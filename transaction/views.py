from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.db.models import Q
from django.db import transaction as db_transaction
from .models import Transaction
from .serializers import (
    TransactionSerializer, 
    TransactionCreateSerializer, 
    TransactionUpdateSerializer,
    DepositSerializer,
    WithdrawSerializer
)
from authentication.permissions import IsAdmin


class TransactionListView(generics.ListCreateAPIView):
    """
    GET: List all transactions
    POST: Create a new transaction
    """
    permission_classes = [IsAdmin]
    
    def get_queryset(self):
        queryset = Transaction.objects.select_related('member_account').all()
        
        # Filter by status
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter.upper())
        
        # Filter by type
        type_filter = self.request.query_params.get('type', None)
        if type_filter:
            queryset = queryset.filter(type=type_filter.upper())
        
        # Filter by member account
        member_id = self.request.query_params.get('member_account', None)
        if member_id:
            queryset = queryset.filter(member_account_id=member_id)
        
        # Search by transaction ID or member email
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(transaction_id__icontains=search) |
                Q(member_account__email__icontains=search) |
                Q(member_account__username__icontains=search)
            )
        
        # Filter by date range
        date_from = self.request.query_params.get('date_from', None)
        date_to = self.request.query_params.get('date_to', None)
        if date_from:
            queryset = queryset.filter(created_at__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__lte=date_to)
        
        return queryset.order_by('-created_at')
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return TransactionCreateSerializer
        return TransactionSerializer
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            errors = {}
            for field, error_list in serializer.errors.items():
                if isinstance(error_list, list):
                    errors[field] = error_list[0] if error_list else 'Invalid value'
                else:
                    errors[field] = str(error_list)
            
            return Response({
                'message': 'Validation failed',
                'errors': errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        transaction = serializer.save()
        return Response({
            'message': 'Transaction created successfully',
            'transaction': TransactionSerializer(transaction).data
        }, status=status.HTTP_201_CREATED)
    
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'transactions': serializer.data,
            'count': queryset.count()
        }, status=status.HTTP_200_OK)


class TransactionDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET: Retrieve a specific transaction
    PUT/PATCH: Update a specific transaction
    DELETE: Delete a specific transaction
    """
    queryset = Transaction.objects.select_related('member_account').all()
    permission_classes = [IsAdmin]
    lookup_field = 'id'
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return TransactionUpdateSerializer
        return TransactionSerializer
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        
        if not serializer.is_valid():
            errors = {}
            for field, error_list in serializer.errors.items():
                if isinstance(error_list, list):
                    errors[field] = error_list[0] if error_list else 'Invalid value'
                else:
                    errors[field] = str(error_list)
            
            return Response({
                'message': 'Validation failed',
                'errors': errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        transaction = serializer.save()
        return Response({
            'message': 'Transaction updated successfully',
            'transaction': TransactionSerializer(transaction).data
        }, status=status.HTTP_200_OK)
    
    def destroy(self, request, *args, **kwargs):
        transaction = self.get_object()
        transaction.delete()
        return Response({
            'message': 'Transaction deleted successfully'
        }, status=status.HTTP_200_OK)


@api_view(['GET', 'POST'])
@permission_classes([permissions.IsAuthenticated])
def my_deposit(request):
    """
    GET: Get all deposit transactions for the currently logged-in user
    POST: Create a deposit transaction request
    """
    user = request.user
    
    if request.method == 'GET':
        # Get all deposit transactions for the user
        queryset = Transaction.objects.filter(
            member_account=user,
            type='DEPOSIT'
        )
        
        # Filter by status
        status_filter = request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter.upper())
        
        # Filter by date range
        date_from = request.query_params.get('date_from', None)
        date_to = request.query_params.get('date_to', None)
        if date_from:
            queryset = queryset.filter(created_at__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__lte=date_to)
        
        # Order by creation date (newest first)
        queryset = queryset.order_by('-created_at')
        
        serializer = TransactionSerializer(queryset, many=True)
        
        # Calculate approved balance breakdown
        from django.db.models import Sum
        approved_deposits = Transaction.objects.filter(
            member_account=user,
            type='DEPOSIT',
            status='COMPLETED'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        approved_withdrawals = Transaction.objects.filter(
            member_account=user,
            type='WITHDRAWAL',
            status='COMPLETED'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        return Response({
            'deposits': serializer.data,
            'count': queryset.count(),
            'balance': {
                'current_balance': float(user.balance),
                'approved_deposits': float(approved_deposits),
                'approved_withdrawals': float(approved_withdrawals),
                'net_balance': float(approved_deposits - approved_withdrawals)
            }
        }, status=status.HTTP_200_OK)
    
    serializer = DepositSerializer(data=request.data)
    
    if not serializer.is_valid():
        errors = {}
        for field, error_list in serializer.errors.items():
            if isinstance(error_list, list):
                errors[field] = error_list[0] if error_list else 'Invalid value'
            else:
                errors[field] = str(error_list)
        
        return Response({
            'message': 'Validation failed',
            'errors': errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    amount = serializer.validated_data['amount']
    remark = serializer.validated_data.get('remark', '')
    user = request.user
    
    try:
        # Create transaction record with PENDING status
        transaction = Transaction.objects.create(
            member_account=user,
            type='DEPOSIT',
            amount=amount,
            remark=remark,
            remark_type='PAYMENT',
            status='PENDING'
        )
        
        return Response({
            'message': 'Deposit request submitted successfully. Waiting for approval.',
            'transaction': TransactionSerializer(transaction).data,
            'current_balance': float(user.balance)
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response({
            'error': f'Deposit failed: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def withdraw_amount(request):
    """
    Withdraw amount from the currently logged-in user's account.
    POST: Create a withdrawal transaction and update user balance
    Requires withdraw password verification.
    """
    serializer = WithdrawSerializer(data=request.data, context={'user': request.user})
    
    if not serializer.is_valid():
        errors = {}
        for field, error_list in serializer.errors.items():
            if isinstance(error_list, list):
                errors[field] = error_list[0] if error_list else 'Invalid value'
            else:
                errors[field] = str(error_list)
        
        return Response({
            'message': 'Validation failed',
            'errors': errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    amount = serializer.validated_data['amount']
    remark = serializer.validated_data.get('remark', '')
    user = request.user
    
    try:
        # Create transaction record with PENDING status
        transaction = Transaction.objects.create(
            member_account=user,
            type='WITHDRAWAL',
            amount=amount,
            remark=remark,
            remark_type='PAYMENT',
            status='PENDING'
        )
        
        return Response({
            'message': 'Withdrawal request submitted successfully. Waiting for approval.',
            'transaction': TransactionSerializer(transaction).data,
            'current_balance': float(user.balance)
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response({
            'error': f'Withdrawal failed: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAdmin])
def approve_transaction(request, transaction_id):
    """
    Approve a pending transaction and update user balance.
    Only accessible by admins.
    POST: Approve transaction and update balance
    """
    try:
        transaction = Transaction.objects.select_related('member_account').get(id=transaction_id)
        
        # Check if transaction is pending
        if transaction.status != 'PENDING':
            return Response({
                'error': f'Transaction is already {transaction.status.lower()}. Only pending transactions can be approved.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        user = transaction.member_account
        
        # Use database transaction to ensure atomicity
        with db_transaction.atomic():
            # Update transaction status
            transaction.status = 'COMPLETED'
            transaction.save(update_fields=['status'])
            
            # Update user balance based on transaction type
            if transaction.type == 'DEPOSIT':
                user.balance += transaction.amount
            elif transaction.type == 'WITHDRAWAL':
                # Double-check balance is sufficient (in case it changed)
                if user.balance < transaction.amount:
                    transaction.status = 'FAILED'
                    transaction.save(update_fields=['status'])
                    return Response({
                        'error': 'Insufficient balance. Transaction marked as failed.'
                    }, status=status.HTTP_400_BAD_REQUEST)
                user.balance -= transaction.amount
            
            user.save(update_fields=['balance'])
        
        return Response({
            'message': 'Transaction approved successfully',
            'transaction': TransactionSerializer(transaction).data,
            'new_balance': float(user.balance)
        }, status=status.HTTP_200_OK)
        
    except Transaction.DoesNotExist:
        return Response({
            'error': 'Transaction not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'error': f'Approval failed: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAdmin])
def reject_transaction(request, transaction_id):
    """
    Reject a pending transaction.
    Only accessible by admins.
    POST: Reject transaction (status changed to FAILED or CANCELLED)
    """
    try:
        transaction = Transaction.objects.get(id=transaction_id)
        
        # Check if transaction is pending
        if transaction.status != 'PENDING':
            return Response({
                'error': f'Transaction is already {transaction.status.lower()}. Only pending transactions can be rejected.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Update transaction status to FAILED
        transaction.status = 'FAILED'
        transaction.save(update_fields=['status'])
        
        return Response({
            'message': 'Transaction rejected successfully',
            'transaction': TransactionSerializer(transaction).data
        }, status=status.HTTP_200_OK)
        
    except Transaction.DoesNotExist:
        return Response({
            'error': 'Transaction not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'error': f'Rejection failed: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_my_transactions(request):
    """
    Get all transactions for the currently logged-in user.
    GET: Retrieve user's own transactions
    """
    user = request.user
    queryset = Transaction.objects.filter(member_account=user)
    
    # Filter by status
    status_filter = request.query_params.get('status', None)
    if status_filter:
        queryset = queryset.filter(status=status_filter.upper())
    
    # Filter by type
    type_filter = request.query_params.get('type', None)
    if type_filter:
        queryset = queryset.filter(type=type_filter.upper())
    
    # Filter by date range
    date_from = request.query_params.get('date_from', None)
    date_to = request.query_params.get('date_to', None)
    if date_from:
        queryset = queryset.filter(created_at__gte=date_from)
    if date_to:
        queryset = queryset.filter(created_at__lte=date_to)
    
    # Order by creation date (newest first)
    queryset = queryset.order_by('-created_at')
    
    serializer = TransactionSerializer(queryset, many=True)
    
    return Response({
        'transactions': serializer.data,
        'count': queryset.count(),
        'current_balance': float(user.balance)
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_my_balance(request):
    """
    Get the current balance for the currently logged-in user.
    GET: Retrieve user's account balance
    """
    user = request.user
    
    return Response({
        'balance': float(user.balance),
        'username': user.username,
        'email': user.email,
        'user_id': user.id
    }, status=status.HTTP_200_OK)
