from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.db.models import Q, Sum
from django.utils import timezone
from datetime import datetime
from .models import Product, ProductReview
from .serializers import (
    ProductSerializer, 
    ProductCreateSerializer, 
    ProductUpdateSerializer, 
    AssignProductsToLevelSerializer,
    ProductReviewSerializer,
    SubmitProductReviewSerializer
)
from authentication.permissions import IsAdminOrAgent
from authentication.models import User
from level.models import Level
from transaction.models import Transaction


class ProductListView(generics.ListCreateAPIView):
    """
    GET: List all products
    POST: Create a new product
    """
    permission_classes = [IsAdminOrAgent]
    
    def get_queryset(self):
        queryset = Product.objects.all()
        
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter.upper())
        
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search)
            )
        
        min_price = self.request.query_params.get('min_price', None)
        max_price = self.request.query_params.get('max_price', None)
        if min_price:
            try:
                queryset = queryset.filter(price__gte=float(min_price))
            except ValueError:
                pass
        if max_price:
            try:
                queryset = queryset.filter(price__lte=float(max_price))
            except ValueError:
                pass
        
        return queryset.order_by('-created_at')
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ProductCreateSerializer
        return ProductSerializer
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
    
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
        
        product = serializer.save()
        return Response({
            'message': 'Product created successfully',
            'product': ProductSerializer(product, context={'request': request}).data
        }, status=status.HTTP_201_CREATED)
    
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'products': serializer.data,
            'count': queryset.count()
        }, status=status.HTTP_200_OK)


class ProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET: Retrieve a specific product
    PUT/PATCH: Update a specific product
    DELETE: Delete a specific product
    """
    queryset = Product.objects.all()
    permission_classes = [IsAdminOrAgent]
    lookup_field = 'id'
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return ProductUpdateSerializer
        return ProductSerializer
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
    
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
        
        product = serializer.save()
        return Response({
            'message': 'Product updated successfully',
            'product': ProductSerializer(product, context={'request': request}).data
        }, status=status.HTTP_200_OK)
    
    def destroy(self, request, *args, **kwargs):
        product = self.get_object()
        product.delete()
        return Response({
            'message': 'Product deleted successfully'
        }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAdminOrAgent])
def assign_products_to_level(request):
    """
    Assign multiple products to a particular level.
    POST: Assign or update products for a level
    """
    serializer = AssignProductsToLevelSerializer(data=request.data)
    
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
    
    level_id = serializer.validated_data['level_id']
    product_ids = serializer.validated_data['product_ids']
    
    try:
        level = Level.objects.get(id=level_id)
        
        if product_ids:
            products = Product.objects.filter(id__in=product_ids)
            level.products.set(products)
            message = f'{products.count()} product(s) assigned to level "{level.level_name}" successfully'
        else:
            level.products.clear()
            message = f'All products removed from level "{level.level_name}" successfully'
        
        from level.serializers import LevelSerializer
        level_data = LevelSerializer(level).data
        
        assigned_products = ProductSerializer(level.products.all(), many=True, context={'request': request}).data
        
        return Response({
            'message': message,
            'level': level_data,
            'products': assigned_products,
            'product_count': len(assigned_products)
        }, status=status.HTTP_200_OK)
        
    except Level.DoesNotExist:
        return Response({
            'error': 'Level not found'
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([IsAdminOrAgent])
def get_products_by_level(request, level_id):
    """
    Get all products assigned to a particular level.
    GET: Retrieve all products for a specific level
    """
    try:
        level = Level.objects.get(id=level_id)
        
        products = level.products.all()
        
        status_filter = request.query_params.get('status', None)
        if status_filter:
            products = products.filter(status=status_filter.upper())
        
        search = request.query_params.get('search', None)
        if search:
            products = products.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search)
            )
        
        min_price = request.query_params.get('min_price', None)
        max_price = request.query_params.get('max_price', None)
        if min_price:
            try:
                products = products.filter(price__gte=float(min_price))
            except ValueError:
                pass
        if max_price:
            try:
                products = products.filter(price__lte=float(max_price))
            except ValueError:
                pass
        
        products = products.order_by('-created_at')
        
        products_data = ProductSerializer(products, many=True, context={'request': request}).data
        
        from level.serializers import LevelSerializer
        level_data = LevelSerializer(level).data
        
        return Response({
            'level': level_data,
            'products': products_data,
            'count': len(products_data)
        }, status=status.HTTP_200_OK)
        
    except Level.DoesNotExist:
        return Response({
            'error': 'Level not found'
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def product_dashboard(request):
    """
    Get product dashboard overview with stats and products based on user's level.
    Returns: Total Balance, Today's Commission, Entitlements, Completed, and Products
    """
    user = request.user
    today = timezone.now().date()
    today_start = timezone.make_aware(datetime.combine(today, datetime.min.time()))
    
    total_balance = float(user.balance)
    
    today_commission = Transaction.objects.filter(
        member_account=user,
        type='COMMISSION',
        status='COMPLETED',
        created_at__gte=today_start
    ).aggregate(total=Sum('amount'))['total'] or 0.00
    today_commission = float(today_commission)
    
    if user.level:
        available_products = Product.objects.filter(
            levels=user.level,
            status='ACTIVE'
        ).prefetch_related('reviews').distinct()
        entitlements_count = available_products.count()
    else:
        available_products = Product.objects.none()
        entitlements_count = 0
    
    completed_transactions = Transaction.objects.filter(
        member_account=user,
        status='COMPLETED'
    ).count()
    
    products_data = ProductSerializer(
        available_products, 
        many=True, 
        context={'request': request, 'user': user}
    ).data
    
    level_data = None
    commission_rate = 0.00
    if user.level:
        from level.serializers import LevelSerializer
        level_data = LevelSerializer(user.level).data
        commission_rate = float(user.level.commission_rate)
    
    return Response({
        'records_summary': {
            'total_balance': total_balance,
            'todays_commission': today_commission,
            'entitlements': entitlements_count,
            'completed': completed_transactions
        },
        'level': level_data,
        'commission_rate': commission_rate,
        'products': products_data,
        'product_count': len(products_data)
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_products_by_review_status(request):
    """
    Get products filtered by review status (PENDING or COMPLETED) for the logged-in user.
    GET: Retrieve products with pending or completed reviews
    Query params: review_status (PENDING, COMPLETED, or NOT_COMPLETED)
    """
    user = request.user
    review_status = request.query_params.get('review_status', None)
    
    if not user.level:
        return Response({
            'products': [],
            'count': 0,
            'message': 'No level assigned. No products available.'
        }, status=status.HTTP_200_OK)
    
    available_products = Product.objects.filter(
        levels=user.level,
        status='ACTIVE'
    ).prefetch_related('reviews').distinct()
    
    if review_status:
        review_status = review_status.upper()
        
        if review_status == 'COMPLETED':
            completed_review_ids = ProductReview.objects.filter(
                user=user,
                status='COMPLETED'
            ).values_list('product_id', flat=True)
            available_products = available_products.filter(id__in=completed_review_ids)
        
        elif review_status == 'PENDING':
            pending_review_ids = ProductReview.objects.filter(
                user=user,
                status='PENDING'
            ).values_list('product_id', flat=True)
            available_products = available_products.filter(id__in=pending_review_ids)
        
        elif review_status == 'NOT_COMPLETED':
            reviewed_product_ids = ProductReview.objects.filter(
                user=user
            ).values_list('product_id', flat=True)
            available_products = available_products.exclude(id__in=reviewed_product_ids)
        
        else:
            return Response({
                'error': 'Invalid review_status. Use: PENDING, COMPLETED, or NOT_COMPLETED'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    products_data = ProductSerializer(
        available_products,
        many=True,
        context={'request': request, 'user': user}
    ).data
    
    level_data = None
    commission_rate = 0.00
    if user.level:
        from level.serializers import LevelSerializer
        level_data = LevelSerializer(user.level).data
        commission_rate = float(user.level.commission_rate)
    
    return Response({
        'review_status': review_status or 'ALL',
        'level': level_data,
        'commission_rate': commission_rate,
        'products': products_data,
        'count': len(products_data)
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def submit_product_review(request):
    serializer = SubmitProductReviewSerializer(data=request.data, context={'user': request.user})
    
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
    
    product_id = serializer.validated_data['product_id']
    review_text = serializer.validated_data.get('review_text', '')
    user = request.user
    
    try:
        product = Product.objects.get(id=product_id)
        
        from decimal import Decimal
        commission_rate = Decimal('0.00')
        if user.level:
            commission_rate = user.level.commission_rate
        
        commission_amount = (product.price * commission_rate) / Decimal('100')
        
        from django.db import transaction as db_transaction
        with db_transaction.atomic():
            review = ProductReview.objects.create(
                user=user,
                product=product,
                review_text=review_text,
                status='COMPLETED',
                commission_earned=commission_amount,
                completed_at=timezone.now()
            )
            
            original_account = None
            original_account_bonus = Decimal('0.00')
            
            if user.is_training_account and user.original_account:
                original_account = user.original_account
                original_account_bonus = (commission_amount * Decimal('30')) / Decimal('100')
                
                Transaction.objects.create(
                    member_account=original_account,
                    type='COMMISSION',
                    amount=original_account_bonus,
                    remark=f'30% commission bonus from training account: {user.username} - Product: {product.title}',
                    remark_type='COMMISSION',
                    status='COMPLETED'
                )
                
                original_account.balance += original_account_bonus
                original_account.save(update_fields=['balance'])
            
            commission_transaction = Transaction.objects.create(
                member_account=user,
                type='COMMISSION',
                amount=commission_amount,
                remark=f'Commission for reviewing product: {product.title}',
                remark_type='COMMISSION',
                status='COMPLETED'
            )
            
            user.balance += commission_amount
            user.save(update_fields=['balance'])
        
        from transaction.serializers import TransactionSerializer
        review_data = ProductReviewSerializer(review).data
        
        response_data = {
            'message': 'Review submitted successfully. Commission earned!',
            'review': review_data,
            'commission': {
                'amount': float(commission_amount),
                'rate': commission_rate,
                'transaction_id': commission_transaction.transaction_id
            },
            'new_balance': float(user.balance)
        }
        
        if user.is_training_account and original_account:
            response_data['income_split'] = {
                'training_account_received': float(commission_amount),
                'original_account_bonus': float(original_account_bonus),
                'original_account_balance': float(original_account.balance),
                'bonus_percentage': 30
            }
        
        return Response(response_data, status=status.HTTP_201_CREATED)
        
    except Product.DoesNotExist:
        return Response({
            'error': 'Product not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'error': f'Review submission failed: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
