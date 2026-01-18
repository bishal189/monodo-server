from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.db.models import Q
from django.db import transaction as db_transaction
from .models import Transaction, WithdrawalAccount
from .serializers import (
    TransactionSerializer, 
    TransactionCreateSerializer, 
    TransactionUpdateSerializer,
    DepositSerializer,
    WithdrawSerializer,
    BalanceAdjustmentSerializer,
    WithdrawalAccountSerializer,
    WithdrawalAccountCreateSerializer,
    WithdrawalAccountUpdateSerializer
)
from authentication.permissions import IsAdmin, IsNormalUser, IsAdminOrAgent


class TransactionListView(generics.ListCreateAPIView):
    permission_classes = [IsAdmin]
    
    def get_queryset(self):
        queryset = Transaction.objects.select_related('member_account').all()
        
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter.upper())
        
        type_filter = self.request.query_params.get('type', None)
        if type_filter:
            queryset = queryset.filter(type=type_filter.upper())
        
        member_id = self.request.query_params.get('member_account', None)
        if member_id:
            queryset = queryset.filter(member_account_id=member_id)
        
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(transaction_id__icontains=search) |
                Q(member_account__email__icontains=search) |
                Q(member_account__username__icontains=search)
            )
        
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
@permission_classes([IsNormalUser])
def my_deposit(request):
    user = request.user
    
    if request.method == 'GET':
        queryset = Transaction.objects.filter(
            member_account=user,
            type='DEPOSIT'
        )
        
        status_filter = request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter.upper())
        
        date_from = request.query_params.get('date_from', None)
        date_to = request.query_params.get('date_to', None)
        if date_from:
            queryset = queryset.filter(created_at__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__lte=date_to)
        
        queryset = queryset.order_by('-created_at')
        
        serializer = TransactionSerializer(queryset, many=True)
        
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
@permission_classes([IsNormalUser])
def withdraw_amount(request):
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
    withdrawal_account_id = serializer.validated_data.get('withdrawal_account_id')
    user = request.user
    
    try:
        withdrawal_account = None
        if withdrawal_account_id:
            withdrawal_account = WithdrawalAccount.objects.get(id=withdrawal_account_id, user=user)
        
        transaction = Transaction.objects.create(
            member_account=user,
            type='WITHDRAWAL',
            amount=amount,
            remark=remark,
            remark_type='PAYMENT',
            status='PENDING',
            withdrawal_account=withdrawal_account
        )
        
        return Response({
            'message': 'Withdrawal request submitted successfully. Waiting for approval.',
            'transaction': TransactionSerializer(transaction).data,
            'current_balance': float(user.balance)
        }, status=status.HTTP_201_CREATED)
        
    except WithdrawalAccount.DoesNotExist:
        return Response({
            'error': 'Withdrawal account not found or does not belong to you.'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'error': f'Withdrawal failed: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAdminOrAgent])
def approve_transaction(request, transaction_id):
    try:
        transaction = Transaction.objects.select_related('member_account', 'member_account__created_by').get(id=transaction_id)
        
        if not request.user.is_admin:
            if transaction.member_account.created_by != request.user:
                return Response({
                    'error': 'You can only approve transactions for users created by you'
                }, status=status.HTTP_403_FORBIDDEN)
        
        if transaction.status not in ['PENDING', 'FAILED', 'COMPLETED']:
            return Response({
                'error': f'Transaction is {transaction.status.lower()}. Cannot approve this transaction.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        user = transaction.member_account
        is_already_completed = transaction.status == 'COMPLETED'
        
        with db_transaction.atomic():
            transaction.status = 'COMPLETED'
            transaction.save(update_fields=['status'])
            
            if not is_already_completed:
                if transaction.type == 'DEPOSIT':
                    user.balance += transaction.amount
                elif transaction.type == 'WITHDRAWAL':
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
@permission_classes([IsAdminOrAgent])
def reject_transaction(request, transaction_id):
    try:
        transaction = Transaction.objects.select_related('member_account', 'member_account__created_by').get(id=transaction_id)
        
        if not request.user.is_admin:
            if transaction.member_account.created_by != request.user:
                return Response({
                    'error': 'You can only reject transactions for users created by you'
                }, status=status.HTTP_403_FORBIDDEN)
        
        if transaction.status not in ['PENDING', 'FAILED', 'COMPLETED']:
            return Response({
                'error': f'Transaction is {transaction.status.lower()}. Cannot reject this transaction.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        user = transaction.member_account
        is_completed = transaction.status == 'COMPLETED'
        
        with db_transaction.atomic():
            if is_completed:
                if transaction.type == 'DEPOSIT':
                    user.balance -= transaction.amount
                elif transaction.type == 'WITHDRAWAL':
                    user.balance += transaction.amount
                user.save(update_fields=['balance'])
            
            transaction.status = 'FAILED'
            transaction.save(update_fields=['status'])
        
        return Response({
            'message': 'Transaction rejected successfully',
            'transaction': TransactionSerializer(transaction).data,
            'new_balance': float(user.balance) if is_completed else None
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
@permission_classes([IsNormalUser])
def get_my_transactions(request):
    user = request.user
    queryset = Transaction.objects.filter(member_account=user)
    
    status_filter = request.query_params.get('status', None)
    if status_filter:
        queryset = queryset.filter(status=status_filter.upper())
    
    type_filter = request.query_params.get('type', None)
    if type_filter:
        queryset = queryset.filter(type=type_filter.upper())
    
    date_from = request.query_params.get('date_from', None)
    date_to = request.query_params.get('date_to', None)
    if date_from:
        queryset = queryset.filter(created_at__gte=date_from)
    if date_to:
        queryset = queryset.filter(created_at__lte=date_to)
    
    queryset = queryset.order_by('-created_at')
    
    serializer = TransactionSerializer(queryset, many=True)
    
    return Response({
        'transactions': serializer.data,
        'count': queryset.count(),
        'current_balance': float(user.balance)
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsNormalUser])
def get_my_balance(request):
    user = request.user
    
    return Response({
        'balance': float(user.balance),
        'username': user.username,
        'email': user.email,
        'user_id': user.id
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAdminOrAgent])
def add_balance(request):
    serializer = BalanceAdjustmentSerializer(data=request.data)
    
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
    
    member_account = serializer.validated_data['member_account']
    balance_type = serializer.validated_data['type']
    amount = serializer.validated_data['amount']
    
    if not request.user.is_admin:
        if member_account.created_by != request.user:
            return Response({
                'error': 'You can only adjust balance for users created by you'
            }, status=status.HTTP_403_FORBIDDEN)
    
    if balance_type == 'CREDIT':
        balance_change = amount
    else:
        balance_change = -amount
    
    try:
        with db_transaction.atomic():
            old_balance = member_account.balance
            member_account.balance += balance_change
            member_account.save(update_fields=['balance'])
        
        return Response({
            'message': f'Balance {balance_type.lower()}ed successfully',
            'balance': {
                'old_balance': float(old_balance),
                'new_balance': float(member_account.balance),
                'change': float(balance_change),
                'type': balance_type
            },
            'user': {
                'id': member_account.id,
                'username': member_account.username,
                'email': member_account.email
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'error': f'Balance adjustment failed: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAdminOrAgent])
def admin_agent_transactions(request):
    if request.user.is_admin:
        queryset = Transaction.objects.select_related('member_account', 'member_account__created_by').all()
    else:
        queryset = Transaction.objects.select_related('member_account', 'member_account__created_by').filter(
            member_account__created_by=request.user
        )
    
    status_filter = request.query_params.get('status', None)
    if status_filter:
        queryset = queryset.filter(status=status_filter.upper())
    
    type_filter = request.query_params.get('type', None)
    if type_filter:
        queryset = queryset.filter(type=type_filter.upper())
    
    member_id = request.query_params.get('member_account', None)
    if member_id:
        queryset = queryset.filter(member_account_id=member_id)
    
    search = request.query_params.get('search', None)
    if search:
        queryset = queryset.filter(
            Q(transaction_id__icontains=search) |
            Q(member_account__email__icontains=search) |
            Q(member_account__username__icontains=search)
        )
    
    date_from = request.query_params.get('date_from', None)
    date_to = request.query_params.get('date_to', None)
    if date_from:
        queryset = queryset.filter(created_at__gte=date_from)
    if date_to:
        queryset = queryset.filter(created_at__lte=date_to)
    
    queryset = queryset.order_by('-created_at')
    
    serializer = TransactionSerializer(queryset, many=True)
    
    return Response({
        'transactions': serializer.data,
        'count': queryset.count(),
        'user_role': 'admin' if request.user.is_admin else 'agent'
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsNormalUser])
def check_withdrawal_account(request):
    try:
        user = request.user
        account_count = WithdrawalAccount.objects.filter(user=user).count()
        has_account = account_count > 0
        active_account_count = WithdrawalAccount.objects.filter(user=user, is_active=True).count()
        primary_account = WithdrawalAccount.objects.filter(user=user, is_primary=True).first()
        
        response_data = {
            'has_account': has_account,
            'total_accounts': account_count,
            'active_accounts': active_account_count,
            'has_primary_account': primary_account is not None
        }
        
        if primary_account:
            serializer = WithdrawalAccountSerializer(primary_account)
            response_data['primary_account'] = serializer.data
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'error': f'Check failed: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET', 'POST'])
@permission_classes([IsNormalUser])
def withdrawal_accounts(request):
    try:
        if request.method == 'GET':
            queryset = WithdrawalAccount.objects.filter(user=request.user)
            
            is_active_filter = request.query_params.get('is_active', None)
            if is_active_filter is not None:
                is_active = is_active_filter.lower() in ['true', '1', 'yes']
                queryset = queryset.filter(is_active=is_active)
            
            queryset = queryset.order_by('-is_primary', '-created_at')
            
            serializer = WithdrawalAccountSerializer(queryset, many=True)
            
            return Response({
                'accounts': serializer.data,
                'count': queryset.count()
            }, status=status.HTTP_200_OK)
        
        serializer = WithdrawalAccountCreateSerializer(data=request.data, context={'request': request})
        
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
        
        withdrawal_account = serializer.save()
        
        return Response({
            'message': 'Withdrawal account added successfully',
            'account': WithdrawalAccountSerializer(withdrawal_account).data
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response({
            'error': f'Operation failed: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
@permission_classes([IsNormalUser])
def withdrawal_account_detail(request, account_id):
    try:
        withdrawal_account = WithdrawalAccount.objects.get(id=account_id, user=request.user)
        
        if request.method == 'GET':
            serializer = WithdrawalAccountSerializer(withdrawal_account)
            return Response({
                'account': serializer.data
            }, status=status.HTTP_200_OK)
        
        if request.method == 'DELETE':
            withdrawal_account.delete()
            return Response({
                'message': 'Withdrawal account deleted successfully'
            }, status=status.HTTP_200_OK)
        
        partial = request.method == 'PATCH'
        serializer = WithdrawalAccountUpdateSerializer(
            withdrawal_account,
            data=request.data,
            partial=partial,
            context={'request': request}
        )
        
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
        
        updated_account = serializer.save()
        
        return Response({
            'message': 'Withdrawal account updated successfully',
            'account': WithdrawalAccountSerializer(updated_account).data
        }, status=status.HTTP_200_OK)
        
    except WithdrawalAccount.DoesNotExist:
        return Response({
            'error': 'Withdrawal account not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'error': f'Operation failed: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
