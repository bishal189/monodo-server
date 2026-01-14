from rest_framework import status, generics
from rest_framework.response import Response
from django.db.models import Q
from .models import Transaction
from .serializers import TransactionSerializer, TransactionCreateSerializer, TransactionUpdateSerializer
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
