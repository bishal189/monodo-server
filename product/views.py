from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.db.models import Q, Sum, Count, F
from django.utils import timezone
from datetime import datetime, timedelta
from .models import Product, ProductReview
from .serializers import (
    ProductSerializer, 
    ProductCreateSerializer, 
    ProductUpdateSerializer, 
    AssignProductsToLevelSerializer,
    ProductReviewSerializer,
    SubmitProductReviewSerializer
)
from authentication.permissions import IsAdminOrAgent, IsNormalUser
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
        
        return queryset.order_by('position', '-created_at')
    
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
@permission_classes([IsNormalUser])
def product_dashboard(request):
    """
    Get product dashboard overview with stats and products based on user's level.
    Returns: Total Balance, Today's Commission, Entitlements, Completed, and Products
    """
    user = request.user
    today = timezone.now().date()
    today_start = timezone.make_aware(datetime.combine(today, datetime.min.time()))
    
    total_balance = float(user.balance)
    
    today_commission = ProductReview.objects.filter(
        user=user,
        status='COMPLETED',
        completed_at__gte=today_start
    ).aggregate(total=Sum('commission_earned'))['total'] or 0.00
    today_commission = float(today_commission)
    
    if user.level:
        all_level_products = Product.objects.filter(
            levels=user.level,
            status='ACTIVE'
        ).prefetch_related('reviews').distinct().order_by('position', '-created_at')
        
        entitlements_count = user.level.min_orders
        
        completed_reviews = ProductReview.objects.filter(
            user=user,
            product__in=all_level_products,
            status='COMPLETED'
        ).values_list('product_id', flat=True)
        
        remaining_orders = max(0, entitlements_count - len(completed_reviews))
        
        available_products_queryset = all_level_products.exclude(id__in=completed_reviews).order_by('position', '-created_at')
        available_products = list(available_products_queryset[:remaining_orders])
    else:
        available_products = Product.objects.none()
        entitlements_count = 0
    
    completed_count = ProductReview.objects.filter(
        user=user,
        status='COMPLETED'
    ).count()
    
    products_data = ProductSerializer(
        available_products, 
        many=True, 
        context={'request': request, 'user': user}
    ).data
    
    level_data = None
    commission_rate = 0.00
    required_amount = 0
    if user.level:
        from level.serializers import LevelSerializer
        level_data = LevelSerializer(user.level).data
        commission_rate = float(user.level.commission_rate)
        required_amount = user.level.required_points
    
    return Response({
        'records_summary': {
            'total_balance': total_balance,
            'todays_commission': today_commission,
            'entitlements': entitlements_count,
            'completed': completed_count,
            'required_amount': required_amount
        },
        'level': level_data,
        'commission_rate': commission_rate,
        'products': products_data,
        'product_count': len(products_data)
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsNormalUser])
def get_products_by_review_status(request):
    """
    Get reviews (PENDING or COMPLETED) for the logged-in user.
    GET: Retrieve user's reviews filtered by status
    Query params: review_status (PENDING or COMPLETED)
    """
    user = request.user
    review_status = request.query_params.get('review_status', None)
    
    reviews = ProductReview.objects.filter(user=user).select_related('product', 'user')
    
    if review_status:
        review_status = review_status.upper()
        
        if review_status == 'COMPLETED':
            reviews = reviews.filter(status='COMPLETED')
        elif review_status == 'PENDING':
            reviews = reviews.filter(status='PENDING')
        else:
            return Response({
                'message': 'Invalid review_status. Use: PENDING or COMPLETED'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    reviews = reviews.order_by('-created_at')
    reviews_data = ProductReviewSerializer(reviews, many=True, context={'request': request}).data
    
    return Response({
        'reviews': reviews_data,
        'count': len(reviews_data),
        'review_status': review_status or 'ALL'
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsNormalUser])
def submit_product_review(request):
    serializer = SubmitProductReviewSerializer(data=request.data, context={'user': request.user})
    
    if not serializer.is_valid():
        error_messages = []
        for field, error_list in serializer.errors.items():
            if isinstance(error_list, list):
                error_messages.append(error_list[0] if error_list else 'Invalid value')
            else:
                error_messages.append(str(error_list))
        
        message = ' '.join(error_messages) if error_messages else 'Validation failed'
        return Response({
            'message': message
        }, status=status.HTTP_400_BAD_REQUEST)
    
    product_id = serializer.validated_data['product_id']
    review_text = serializer.validated_data.get('review_text', '')
    user = request.user
    
    try:
        product = Product.objects.get(id=product_id)
        
        from decimal import Decimal
        from django.db import transaction as db_transaction
        
        existing_review = ProductReview.objects.filter(user=user, product=product).first()
        user_balance = Decimal(str(user.balance))
        product_price = Decimal(str(product.price))
        
        was_previously_completed = existing_review and existing_review.status == 'COMPLETED'
        
        if user_balance < product_price:
            review_status = 'PENDING'
        else:
            review_status = 'COMPLETED'
        
        commission_rate = Decimal('0.00')
        if user.level:
            commission_rate = user.level.commission_rate
        
        commission_amount = (product.price * commission_rate) / Decimal('100')
        original_account = None
        original_account_bonus = Decimal('0.00')
        
        with db_transaction.atomic():
            is_new_review = not existing_review
            should_process_commission = review_status == 'COMPLETED' and (is_new_review or not was_previously_completed)
            
            if existing_review:
                existing_review.review_text = review_text
                existing_review.status = review_status
                if review_status == 'COMPLETED':
                    existing_review.commission_earned = commission_amount
                    existing_review.completed_at = timezone.now()
                else:
                    existing_review.commission_earned = Decimal('0.00')
                    existing_review.completed_at = None
                existing_review.save()
                review = existing_review
            else:
                review = ProductReview.objects.create(
                    user=user,
                    product=product,
                    review_text=review_text,
                    status=review_status,
                    commission_earned=commission_amount if review_status == 'COMPLETED' else Decimal('0.00'),
                    completed_at=timezone.now() if review_status == 'COMPLETED' else None
                )
            
            if should_process_commission:
                if user.is_training_account and user.original_account:
                    original_account = user.original_account
                    original_account_bonus = (commission_amount * Decimal('30')) / Decimal('100')
                    
                    original_account.balance += original_account_bonus
                    original_account.save(update_fields=['balance'])
                
                user.balance += commission_amount
                user.save(update_fields=['balance'])
        
        today = timezone.now().date()
        today_start = timezone.make_aware(datetime.combine(today, datetime.min.time()))
        
        today_commission = ProductReview.objects.filter(
            user=user,
            status='COMPLETED',
            completed_at__gte=today_start
        ).aggregate(total=Sum('commission_earned'))['total'] or Decimal('0.00')
        today_commission = float(today_commission)
        
        completed_count = ProductReview.objects.filter(
            user=user,
            status='COMPLETED'
        ).count()
        
        if review_status == 'COMPLETED':
            if existing_review and was_previously_completed:
                message = 'Review updated successfully.'
            else:
                message = 'Review submitted successfully. Commission earned!'
        else:
            message = 'Review submitted and set to PENDING. Insufficient balance to complete review.'
        
        response_data = {
            'message': message,
            'todays_commission': today_commission,
            'completed': completed_count
        }
        
        return Response(response_data, status=status.HTTP_201_CREATED if not existing_review else status.HTTP_200_OK)
        
    except Product.DoesNotExist:
        return Response({
            'message': 'Product not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'message': f'Review submission failed: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAdminOrAgent])
def reset_user_level_progress(request, user_id, level_id):
    """
    Reset a user's product progress for a specific level.
    - Deletes all ProductReview records for products in that level
    - User's balance remains the same (no commission deduction)
    - User can then play/review products in that level again
    - Like a game - replay levels without losing earnings
    """
    try:
        user = User.objects.get(id=user_id)
        level = Level.objects.get(id=level_id)
        
        if not request.user.is_admin:
            if user.created_by != request.user:
                return Response({
                    'error': 'You can only reset progress for users created by you'
                }, status=status.HTTP_403_FORBIDDEN)
        
        level_products = Product.objects.filter(levels=level)
        product_ids = level_products.values_list('id', flat=True)
        
        user_reviews = ProductReview.objects.filter(
            user=user,
            product_id__in=product_ids,
            status='COMPLETED'
        )
        
        total_commission_earned = user_reviews.aggregate(
            total=Sum('commission_earned')
        )['total'] or 0.00
        
        review_count = user_reviews.count()
        
        completed_transactions = Transaction.objects.filter(
            member_account=user,
            status='COMPLETED'
        )
        completed_transaction_count = completed_transactions.count()
        
        from django.db import transaction as db_transaction
        
        with db_transaction.atomic():
            user_reviews.delete()
            completed_transactions.delete()
        
        return Response({
            'message': f'User progress reset successfully for level "{level.level_name}". Balance remains unchanged. Fresh start - completed count reset to 0.',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'balance': float(user.balance)
            },
            'level': {
                'id': level.id,
                'level_name': level.level_name
            },
            'reset_details': {
                'reviews_deleted': review_count,
                'completed_transactions_deleted': completed_transaction_count,
                'total_commission_earned': float(total_commission_earned),
                'balance_unchanged': True,
                'current_balance': float(user.balance),
                'total_completed_reset': True,
                'new_completed_count': 0,
                'message': 'User can now play products in this level again. Fresh game - all completed counts reset to 0 while keeping all earned commissions'
            }
        }, status=status.HTTP_200_OK)
        
    except User.DoesNotExist:
        return Response({
            'error': 'User not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Level.DoesNotExist:
        return Response({
            'error': 'Level not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'error': f'Reset failed: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAdminOrAgent])
def user_product_completion_stats(request):
    """
    Get product completion statistics for users.
    Admin can see all users, Agent can only see their created users.
    Returns: User stats with completed products count, total commission, and product details
    """
    if request.user.is_admin:
        users_queryset = User.objects.filter(role='USER').select_related('level', 'created_by')
    else:
        users_queryset = User.objects.filter(
            role='USER',
            created_by=request.user
        ).select_related('level', 'created_by')
    
    search = request.query_params.get('search', None)
    if search:
        users_queryset = users_queryset.filter(
            Q(email__icontains=search) |
            Q(username__icontains=search) |
            Q(phone_number__icontains=search) |
            Q(invitation_code__icontains=search)
        )
    
    is_active = request.query_params.get('is_active', None)
    if is_active is not None:
        users_queryset = users_queryset.filter(is_active=is_active.lower() == 'true')
    
    user_id = request.query_params.get('user_id', None)
    if user_id:
        users_queryset = users_queryset.filter(id=user_id)
    
    users_stats = []
    
    for user in users_queryset:
        completed_reviews = ProductReview.objects.filter(
            user=user,
            status='COMPLETED'
        )
        
        total_completed = completed_reviews.count()
        total_commission = completed_reviews.aggregate(
            total=Sum('commission_earned')
        )['total'] or 0.00
        
        today = timezone.now().date()
        today_start = timezone.make_aware(datetime.combine(today, datetime.min.time()))
        today_completed = completed_reviews.filter(completed_at__gte=today_start).count()
        
        this_week_start = timezone.now() - timedelta(days=7)
        week_completed = completed_reviews.filter(completed_at__gte=this_week_start).count()
        
        products_breakdown = completed_reviews.values(
            'product__id',
            'product__title',
            'product__price'
        ).annotate(
            completed_count=Count('id'),
            commission_earned=Sum('commission_earned')
        ).order_by('-completed_at')
        
        products_data = []
        for item in products_breakdown[:10]:
            products_data.append({
                'product_id': item['product__id'],
                'product_title': item['product__title'],
                'product_price': float(item['product__price']),
                'completed_count': item['completed_count'],
                'commission_earned': float(item['commission_earned'])
            })
        
        recent_reviews = completed_reviews.order_by('-completed_at')[:5]
        recent_activity = []
        for review in recent_reviews:
            recent_activity.append({
                'product_id': review.product.id,
                'product_title': review.product.title,
                'commission_earned': float(review.commission_earned),
                'completed_at': review.completed_at.isoformat() if review.completed_at else None
            })
        
        users_stats.append({
            'user_id': user.id,
            'username': user.username,
            'email': user.email,
            'phone_number': user.phone_number,
            'invitation_code': user.invitation_code,
            'level': {
                'id': user.level.id if user.level else None,
                'level_name': user.level.level_name if user.level else None,
                'level_number': user.level.level if user.level else None
            } if user.level else None,
            'created_by': {
                'id': user.created_by.id if user.created_by else None,
                'username': user.created_by.username if user.created_by else None,
                'email': user.created_by.email if user.created_by else None
            } if user.created_by else None,
            'is_training_account': user.is_training_account,
            'balance': float(user.balance),
            'is_active': user.is_active,
            'statistics': {
                'total_completed_products': total_completed,
                'total_commission_earned': float(total_commission),
                'today_completed': today_completed,
                'week_completed': week_completed,
                'products_breakdown': products_data,
                'recent_activity': recent_activity
            }
        })
    
    return Response({
        'users': users_stats,
        'total_users': len(users_stats),
        'summary': {
            'total_completed_products': sum(user['statistics']['total_completed_products'] for user in users_stats),
            'total_commission_paid': sum(user['statistics']['total_commission_earned'] for user in users_stats),
            'users_with_completions': sum(1 for user in users_stats if user['statistics']['total_completed_products'] > 0)
        }
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsNormalUser])
def get_user_products_by_min_orders(request):
    """
    Get products for the logged-in user based on their level's min_orders.
    Returns products up to min_orders count (excluding already completed ones).
    If user has completed some products, shows remaining products up to min_orders.
    """
    user = request.user
    
    if not user.level:
        return Response({
            'message': 'No level assigned. Please contact support.',
            'min_orders': 0,
            'total_products_available': 0,
            'remaining_products': 0,
            'completed_products': 0,
            'products': []
        }, status=status.HTTP_200_OK)
    
    min_orders = user.level.min_orders
    
    all_level_products = Product.objects.filter(
        levels=user.level,
        status='ACTIVE'
    ).prefetch_related('reviews').distinct().order_by('position', '-created_at')
    
    completed_reviews = ProductReview.objects.filter(
        user=user,
        product__in=all_level_products,
        status='COMPLETED'
    ).values_list('product_id', flat=True)
    
    completed_count = len(completed_reviews)
    remaining_orders = max(0, min_orders - completed_count)
    
    available_products = list(all_level_products.exclude(id__in=completed_reviews))[:remaining_orders]
    
    products_data = ProductSerializer(
        available_products,
        many=True,
        context={'request': request, 'user': user}
    ).data
    
    return Response({
        'min_orders': min_orders,
        'total_products_available': len(all_level_products),
        'remaining_products': remaining_orders,
        'completed_products': completed_count,
        'products': products_data,
        'product_count': len(products_data),
        'level': {
            'id': user.level.id,
            'level_name': user.level.level_name,
            'level_number': user.level.level,
            'min_orders': user.level.min_orders,
            'commission_rate': float(user.level.commission_rate)
        },
        'message': f'You can review {remaining_orders} more products out of {min_orders} required for your level.'
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAdminOrAgent])
def get_user_products_for_admin(request, user_id):
    """
    Get min_orders for a specific user from their level.
    Admin/Agent can use this to see the min_orders requirement for a user.
    """
    try:
        target_user = User.objects.get(id=user_id, role='USER')
    except User.DoesNotExist:
        return Response({
            'error': 'User not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    if not request.user.is_admin:
        if target_user.created_by != request.user:
            return Response({
                'error': 'You can only view min_orders for users created by you'
            }, status=status.HTTP_403_FORBIDDEN)
    
    if not target_user.level:
        return Response({
            'user_id': target_user.id,
            'username': target_user.username,
            'min_orders': 0
        }, status=status.HTTP_200_OK)
    
    min_orders = target_user.level.min_orders
    
    return Response({
        'user_id': target_user.id,
        'username': target_user.username,
        'min_orders': min_orders
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAdminOrAgent])
def get_user_completed_products_count(request, user_id):
    """
    Get the count of products a user has completed/reviewed.
    Admin/Agent can use this to track user's product completion progress.
    """
    try:
        target_user = User.objects.get(id=user_id, role='USER')
    except User.DoesNotExist:
        return Response({
            'error': 'User not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    if not request.user.is_admin:
        if target_user.created_by != request.user:
            return Response({
                'error': 'You can only view completion count for users created by you'
            }, status=status.HTTP_403_FORBIDDEN)
    
    if not target_user.level:
        return Response({
            'user_id': target_user.id,
            'username': target_user.username,
            'completed': 0,
            'min_orders': 0
        }, status=status.HTTP_200_OK)
    
    min_orders = target_user.level.min_orders
    
    all_level_products = Product.objects.filter(
        levels=target_user.level,
        status='ACTIVE'
    ).distinct()
    
    completed_count = ProductReview.objects.filter(
        user=target_user,
        product__in=all_level_products,
        status='COMPLETED'
    ).count()
    
    return Response({
        'user_id': target_user.id,
        'username': target_user.username,
        'completed': completed_count,
        'min_orders': min_orders
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAdminOrAgent])
def insert_product_at_position(request, product_id):
    """
    Insert a product at a specific position (for freeze concept).
    Updates the product's position and adjusts other products' positions accordingly.
    """
    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        return Response({
            'error': 'Product not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    position = request.data.get('position', None)
    if position is None:
        return Response({
            'error': 'Position is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        position = int(position)
        if position < 0:
            return Response({
                'error': 'Position must be a non-negative integer'
            }, status=status.HTTP_400_BAD_REQUEST)
    except (ValueError, TypeError):
        return Response({
            'error': 'Position must be a valid integer'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    from django.db import transaction as db_transaction
    
    with db_transaction.atomic():
        current_position = product.position
        
        if position == current_position:
            return Response({
                'message': 'Product is already at this position',
                'product_id': product.id,
                'product_title': product.title,
                'position': position
            }, status=status.HTTP_200_OK)
        
        if position < current_position:
            Product.objects.exclude(id=product_id).filter(
                position__gte=position,
                position__lt=current_position
            ).update(position=F('position') + 1)
        else:
            Product.objects.exclude(id=product_id).filter(
                position__gt=current_position,
                position__lte=position
            ).update(position=F('position') - 1)
        
        product.position = position
        product.save(update_fields=['position'])
    
    product_data = ProductSerializer(product, context={'request': request}).data
    
    return Response({
        'message': f'Product moved to position {position} successfully',
        'product': product_data
    }, status=status.HTTP_200_OK)
