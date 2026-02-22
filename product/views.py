import random
from decimal import Decimal

from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.db.models import Q, Sum, Count, F
from django.utils import timezone
from datetime import datetime, timedelta
from .models import Product, ProductReview
from .serializers import (
    ProductSerializer,
    ProductDashboardSerializer,
    ProductCreateSerializer,
    ProductUpdateSerializer,
    AssignProductsToLevelSerializer,
    ProductReviewSerializer,
    SubmitProductReviewSerializer
)
from authentication.permissions import IsAdminOrAgent, IsNormalUser
from authentication.models import User
from level.models import Level
from transaction.models import Transaction, WithdrawalAccount


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
        
        order_by = self.request.query_params.get('order_by', 'price')
        if order_by == 'id':
            queryset = queryset.order_by('id')
        elif order_by == 'price_desc':
            queryset = queryset.order_by('-price')
        elif order_by == 'price' or order_by == 'price_asc':
            queryset = queryset.order_by('price')
        else:
            queryset = queryset.order_by('price')
        return queryset

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ProductCreateSerializer
        return ProductSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        user_id = self.request.query_params.get('user_id')
        if user_id and self.request.method == 'GET':
            try:
                target = User.objects.get(id=int(user_id), role='USER')
                if self.request.user.is_admin or target.created_by == self.request.user:
                    context['user'] = target
                    return context
            except (ValueError, TypeError, User.DoesNotExist):
                pass
        context['user'] = getattr(self.request, 'user', None)
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
        total_count = queryset.count()
        try:
            limit = int(request.query_params.get('limit', 10))
            limit = max(1, min(limit, 100))
        except (ValueError, TypeError):
            limit = 10
        try:
            offset = int(request.query_params.get('offset', 0))
            offset = max(0, offset)
        except (ValueError, TypeError):
            offset = 0
        page = queryset[offset:offset + limit]
        serializer = self.get_serializer(page, many=True)
        return Response({
            'products': serializer.data,
            'count': total_count,
            'limit': limit,
            'offset': offset,
            'has_more': (offset + limit) < total_count,
            'next_offset': offset + limit if (offset + limit) < total_count else None
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


def _get_dashboard_pool(user):
    """Build product pool and next_to_do for user's level. Returns (all_products_ordered, next_to_do, pool_products, entitlements_count, completed_in_pool, product_positions). product_positions is {product_id: position}."""
    pool_products = []
    all_products_ordered = []
    next_to_do = []
    entitlements_count = 0
    completed_in_pool = 0
    product_positions = {}

    if not user.level:
        return all_products_ordered, next_to_do, pool_products, entitlements_count, completed_in_pool, product_positions

    level = user.level
    min_orders = int(level.min_orders or 0)
    level_products = list(
        Product.objects.filter(levels=level, status='ACTIVE')
        .prefetch_related('reviews').order_by('price')[:min_orders]
    )
    if len(level_products) < min_orders:
        used_ids = {p.id for p in level_products}
        extra = list(
            Product.objects.filter(status='ACTIVE')
            .exclude(id__in=used_ids)
            .prefetch_related('reviews')
            .order_by('price')[:min_orders - len(level_products)]
        )
        pool_products = level_products + extra
    else:
        pool_products = level_products
    entitlements_count = min_orders

    start_continuous = _get_start_continuous_orders_after(user) + 1
    assigned_reviews = list(ProductReview.objects.filter(
        user=user,
        position__isnull=False
    ).select_related('product').order_by('position'))
    assigned_by_pos = {r.position: r.product for r in assigned_reviews if r.product and r.product.status == 'ACTIVE'}
    used_product_ids = {p.id for p in assigned_by_pos.values()}

    pool_candidates = [p for p in pool_products if p.id not in used_product_ids]
    seed = user.id * 100000 + (level.id or 0)
    rng = random.Random(seed)
    rng.shuffle(pool_candidates)

    combined = []
    pool_consumed = 0
    for pos in range(1, min_orders + 1):
        if pos in assigned_by_pos:
            combined.append((pos, assigned_by_pos[pos]))
        else:
            if pool_consumed < len(pool_candidates):
                p = pool_candidates[pool_consumed]
                pool_consumed += 1
                combined.append((pos, p))
                used_product_ids.add(p.id)
    for pos, prod in sorted(assigned_by_pos.items()):
        if pos > min_orders:
            combined.append((pos, prod))
    combined.sort(key=lambda x: x[0])
    all_products_ordered = [p for _, p in combined]
    product_positions = {p.id: pos for pos, p in combined}
    pool_product_ids = [p.id for p in all_products_ordered]
    completed_reviews = set(ProductReview.objects.filter(
        user=user,
        product_id__in=pool_product_ids,
        status='COMPLETED'
    ).values_list('product_id', flat=True))
    completed_in_pool = len(completed_reviews)
    next_to_do = [p for p in all_products_ordered if p.id not in completed_reviews]

    return all_products_ordered, next_to_do, pool_products, entitlements_count, completed_in_pool, product_positions


@api_view(['GET'])
@permission_classes([IsNormalUser])
def product_dashboard(request):
    """Dashboard: summary stats only (balance, commission, entitlements, completed, level, etc.). Use /dashboard-products/ for products."""
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

    all_products_ordered, next_to_do, pool_products, entitlements_count, completed_in_pool, _ = _get_dashboard_pool(user)

    completed_count = getattr(user, 'completed_products_count', 0) or 0

    commission_rate = 0.00
    if user.level:
        if getattr(user, 'balance_frozen', False):
            fr = getattr(user.level, 'frozen_commission_rate', None)
            commission_rate = float(fr) if fr is not None else 6.00
        else:
            commission_rate = float(user.level.commission_rate)

    minimum_balance = int(user.level.required_points) if user.level and user.level.required_points is not None else None

    return Response({
        'total_balance': total_balance,
        'minimum_balance': minimum_balance,
        'commission_rate': commission_rate,
        'todays_commission': today_commission,
        'entitlements': entitlements_count,
        'completed': completed_count,
        'balance_frozen': user.balance_frozen,
        'balance_frozen_amount': float(user.balance_frozen_amount) if user.balance_frozen_amount is not None else None,
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsNormalUser])
def product_dashboard_products(request):
    """Dashboard products: paginated list of next products to do (min/max % agreed price applied)."""
    user = request.user
    try:
        limit = max(1, min(int(request.query_params.get('limit', 50)), 50))
    except (TypeError, ValueError):
        limit = 50
    try:
        offset = max(0, int(request.query_params.get('offset', 0)))
    except (TypeError, ValueError):
        offset = 0

    all_products_ordered, next_to_do, pool_products, entitlements_count, completed_in_pool, product_positions = _get_dashboard_pool(user)
    completed_reviews = set(ProductReview.objects.filter(
        user=user,
        product_id__in=[p.id for p in all_products_ordered],
        status='COMPLETED'
    ).values_list('product_id', flat=True))
    slots = [
        None if p.id in completed_reviews else p
        for p in all_products_ordered
    ]
    if limit == 1:
        next_index = next((i for i in range(offset, len(slots)) if slots[i] is not None), None)
        if next_index is None:
            slot_slice = []
            actual_offset = offset
        else:
            slot_slice = [slots[next_index]]
            actual_offset = next_index
    else:
        slot_slice = slots[offset:offset + limit]
        actual_offset = offset

    for slot_product in slot_slice:
        if slot_product is None:
            continue
        review, _ = ProductReview.objects.get_or_create(
            user=user,
            product=slot_product,
            defaults={'status': 'PENDING'}
        )
        if review.agreed_price is None and not slot_product.use_actual_price and not getattr(review, 'use_actual_price', False):
            balance_val = float(user.balance)
            min_pct = 30.0
            max_pct = 70.0
            if getattr(user, 'matching_min_percent', None) is not None and getattr(user, 'matching_max_percent', None) is not None:
                min_pct = float(user.matching_min_percent)
                max_pct = float(user.matching_max_percent)
            if balance_val > 0:
                low = (min_pct / 100) * balance_val
                high = (max_pct / 100) * balance_val
                agreed_val = round(random.uniform(low, high), 2)
                agreed_val = max(0.01, agreed_val)
            else:
                agreed_val = 0.01
            review.agreed_price = Decimal(str(agreed_val))
            review.save(update_fields=['agreed_price'])

    products_data = []
    for slot_product in slot_slice:
        if slot_product is None:
            products_data.append(None)
        else:
            products_data.append(
                ProductDashboardSerializer(
                    slot_product,
                    context={'request': request, 'user': user, 'product_positions': product_positions}
                ).data
            )

    return Response({
        'products': products_data,
        'offset': actual_offset,
        'total_slots': len(all_products_ordered),
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsNormalUser])
def get_products_by_review_status(request):
    """
    Get reviews for the logged-in user.
    Default: completed + only pending that are frozen (use_frozen_commission=True).
    Pending in this system = frozen (insufficient balance); other in-progress items are not returned.
    Query params: review_status = COMPLETED | PENDING_FROZEN | ALL
    """
    from django.db.models import Q
    user = request.user
    review_status = request.query_params.get('review_status', None)
    
    reviews = ProductReview.objects.filter(user=user).select_related('product', 'user')
    
    if review_status:
        review_status = review_status.upper()
        if review_status == 'COMPLETED':
            reviews = reviews.filter(status='COMPLETED')
        elif review_status == 'PENDING_FROZEN':
            reviews = reviews.filter(status='PENDING', use_frozen_commission=True)
        elif review_status == 'ALL':
            reviews = reviews.filter(Q(status='COMPLETED') | Q(status='PENDING', use_frozen_commission=True))
            review_status = 'ALL'
        else:
            return Response({
                'message': 'Invalid review_status. Use: COMPLETED, PENDING_FROZEN or ALL'
            }, status=status.HTTP_400_BAD_REQUEST)
    else:
        reviews = reviews.filter(Q(status='COMPLETED') | Q(status='PENDING', use_frozen_commission=True))
        review_status = 'ALL'
    
    reviews = reviews.order_by('-completed_at', '-created_at')
    reviews_data = ProductReviewSerializer(reviews, many=True, context={'request': request}).data
    
    return Response({
        'reviews': reviews_data,
        'count': len(reviews_data),
        'review_status': review_status
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
        if existing_review and getattr(existing_review, 'use_actual_price', False):
            product_price = Decimal(str(product.price))
        elif product.use_actual_price:
            product_price = Decimal(str(product.price))
        elif existing_review and existing_review.agreed_price is not None:
            product_price = existing_review.agreed_price
        else:
            product_price = Decimal(str(product.price))
        
        was_previously_completed = existing_review and existing_review.status == 'COMPLETED'
        
        is_frozen_pending = (
            existing_review and getattr(existing_review, 'use_frozen_commission', False) and
            getattr(user, 'balance_frozen', False) and user.balance_frozen_amount is not None
        )
        if is_frozen_pending:
            effective_balance = Decimal(str(user.balance_frozen_amount))
            review_status = 'COMPLETED' if effective_balance >= product_price else 'PENDING'
        elif user_balance < product_price:
            review_status = 'PENDING'
        else:
            review_status = 'COMPLETED'

        if user.level:
            use_frozen = existing_review and getattr(existing_review, 'use_frozen_commission', False)
            if use_frozen:
                fr = getattr(user.level, 'frozen_commission_rate', None)
                commission_rate = user.level.frozen_commission_rate if fr is not None else Decimal('6.00')
            else:
                commission_rate = user.level.commission_rate
        else:
            commission_rate = Decimal('0.00')

        commission_amount = (product_price * commission_rate) / Decimal('100')
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
                update_fields = ['review_text', 'status', 'commission_earned', 'completed_at']
                if review_status == 'PENDING':
                    existing_review.use_frozen_commission = True
                    update_fields.append('use_frozen_commission')
                existing_review.save(update_fields=update_fields)
                review = existing_review
            else:
                review = ProductReview.objects.create(
                    user=user,
                    product=product,
                    review_text=review_text,
                    status=review_status,
                    commission_earned=commission_amount if review_status == 'COMPLETED' else Decimal('0.00'),
                    completed_at=timezone.now() if review_status == 'COMPLETED' else None,
                    use_frozen_commission=(review_status == 'PENDING'),
                )
            
            if should_process_commission:
                if user.is_training_account and user.original_account:
                    original_account = user.original_account
                    original_account_bonus = (commission_amount * Decimal('30')) / Decimal('100')
                    
                    original_account.balance += original_account_bonus
                    original_account.save(update_fields=['balance'])
                
                if is_frozen_pending and getattr(user, 'balance_frozen', False):
                    frozen_amount = Decimal(str(user.balance_frozen_amount or 0))
                    user.balance = frozen_amount + commission_amount
                    user.balance_frozen = False
                    user.balance_frozen_amount = None
                else:
                    user.balance += commission_amount
                    user.balance_frozen = False
                    user.balance_frozen_amount = None
                user.save(update_fields=['balance', 'balance_frozen', 'balance_frozen_amount'])
                User.objects.filter(pk=user.pk).update(completed_products_count=F('completed_products_count') + 1)
            elif review_status == 'PENDING' and not getattr(user, 'balance_frozen', False):
                user.balance = user_balance - product_price
                user.balance_frozen = True
                user.balance_frozen_amount = user_balance
                user.save(update_fields=['balance', 'balance_frozen', 'balance_frozen_amount'])
        
        today = timezone.now().date()
        today_start = timezone.make_aware(datetime.combine(today, datetime.min.time()))
        
        today_commission = ProductReview.objects.filter(
            user=user,
            status='COMPLETED',
            completed_at__gte=today_start
        ).aggregate(total=Sum('commission_earned'))['total'] or Decimal('0.00')
        today_commission = float(today_commission)
        
        user.refresh_from_db()
        completed_count = getattr(user, 'completed_products_count', 0) or 0
        
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


def reset_user_level_progress_impl(user, level):
    """
    Reset user's progress for a level: completed_products_count=0, delete today's
    completed reviews (commission), level completed reviews, completed transactions.
    Balance unchanged. Caller must ensure permissions.
    """
    level_products = Product.objects.filter(levels=level)
    product_ids = list(level_products.values_list('id', flat=True))
    user_reviews = ProductReview.objects.filter(
        user=user,
        product_id__in=product_ids,
        status='COMPLETED'
    )
    today = timezone.now().date()
    today_start = timezone.make_aware(datetime.combine(today, datetime.min.time()))
    today_completed_reviews = ProductReview.objects.filter(
        user=user,
        status='COMPLETED',
        completed_at__gte=today_start
    )
    completed_transactions = Transaction.objects.filter(
        member_account=user,
        status='COMPLETED'
    )
    from django.db import transaction as db_transaction
    with db_transaction.atomic():
        user_reviews.delete()
        today_completed_reviews.delete()
        completed_transactions.delete()
        user.completed_products_count = 0
        user.save(update_fields=['completed_products_count'])


@api_view(['POST'])
@permission_classes([IsAdminOrAgent])
def reset_user_level_progress(request, user_id, level_id):
    """
    Reset a user's product progress for a specific level. Balance is never changed.
    - Deletes all ProductReview records for products in that level
    - Deletes all of user's reviews completed today (so Today's Commission becomes 0)
    - Deletes completed transactions for the user (log only; balance not touched)
    - Sets completed_products_count to 0
    - User's balance is left unchanged (no deduction, all earned commission kept)
    - User can then play/review products in that level again (fresh game)
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

        today = timezone.now().date()
        today_start = timezone.make_aware(datetime.combine(today, datetime.min.time()))
        today_completed_reviews = ProductReview.objects.filter(
            user=user,
            status='COMPLETED',
            completed_at__gte=today_start
        )
        today_reviews_count = today_completed_reviews.count()

        reset_user_level_progress_impl(user, level)

        return Response({
            'message': f'User progress reset successfully for level "{level.level_name}". Balance unchanged. Fresh start - completed count and today\'s commission reset to 0.',
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
                'today_reviews_deleted': today_reviews_count,
                'completed_transactions_deleted': completed_transaction_count,
                'total_commission_earned': float(total_commission_earned),
                'balance_unchanged': True,
                'current_balance': float(user.balance),
                'total_completed_reset': True,
                'new_completed_count': 0,
                'today_commission_reset': True,
                'message': 'User can now play products in this level again. Fresh game - completed count and today\'s commission reset to 0, balance unchanged.'
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
    ).prefetch_related('reviews').distinct().order_by('price')
    
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


@api_view(['GET', 'PATCH'])
@permission_classes([IsAdminOrAgent])
def admin_user_order_overview(request, user_id):
    """
    GET: Order overview for a user.
    PATCH: Save order settings (start_continuous_orders_after) to the user's level.
    """
    try:
        target_user = User.objects.get(id=user_id, role='USER')
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    if not request.user.is_admin and target_user.created_by != request.user:
        return Response({'error': 'You can only view users created by you'}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'PATCH':
        if not target_user.level:
            return Response({'error': 'User has no level assigned'}, status=status.HTTP_400_BAD_REQUEST)
        level = target_user.level
        val = request.data.get('start_continuous_orders_after')
        if val is not None:
            try:
                val = int(val)
                if val < 0:
                    return Response({'error': 'start_continuous_orders_after must be >= 0'}, status=status.HTTP_400_BAD_REQUEST)
            except (TypeError, ValueError):
                return Response({'error': 'start_continuous_orders_after must be a non-negative integer'}, status=status.HTTP_400_BAD_REQUEST)
            level.start_continuous_orders_after = val
            level.save(update_fields=['start_continuous_orders_after'])

        assigned = request.data.get('assigned_products', [])
        if assigned:
            start_continuous = _get_start_continuous_orders_after(target_user) + 1
            ProductReview.objects.filter(
                user=target_user,
                position__gte=start_continuous
            ).update(position=None, use_actual_price=False)
            for item in assigned:
                pid = item.get('product_id')
                pos = item.get('position')
                if pid is None or pos is None:
                    continue
                try:
                    pos = int(pos)
                    if pos < start_continuous:
                        continue
                except (TypeError, ValueError):
                    continue
                try:
                    product = Product.objects.get(id=pid, status='ACTIVE')
                except Product.DoesNotExist:
                    continue
                ProductReview.objects.filter(
                    user=target_user,
                    product=product,
                    status='COMPLETED'
                ).update(
                    status='PENDING',
                    completed_at=None,
                    commission_earned=Decimal('0.00'),
                    agreed_price=None,
                )
                review, _ = ProductReview.objects.get_or_create(
                    user=target_user,
                    product=product,
                    defaults={'status': 'PENDING'}
                )
                review.position = pos
                review.use_actual_price = True
                review.save(update_fields=['position', 'use_actual_price'])

        return Response({
            'message': 'Order settings saved successfully',
            'user_id': target_user.id,
            'start_continuous_orders_after': level.start_continuous_orders_after
        }, status=status.HTTP_200_OK)

    today = timezone.now().date()
    today_start = timezone.make_aware(datetime.combine(today, datetime.min.time()))

    if not target_user.level:
        return Response({
            'user_id': target_user.id,
            'username': target_user.username,
            'current_orders_made': 0,
            'orders_received_today': 0,
            'max_orders_by_level': 0,
            'start_continuous_orders_after': 0,
            'daily_available_orders': 0,
            'assigned_products': []
        }, status=status.HTTP_200_OK)

    min_orders = int(target_user.level.min_orders or 0)

    current_orders_made = getattr(target_user, 'completed_products_count', 0) or 0

    orders_received_today = ProductReview.objects.filter(
        user=target_user,
        status='COMPLETED',
        completed_at__gte=today_start
    ).count()

    start_continuous_orders_after = _get_start_continuous_orders_after(target_user)
    daily_available_orders = min_orders

    inserted_reviews = ProductReview.objects.filter(
        user=target_user,
        position__isnull=False,
        status='PENDING'
    ).select_related('product').order_by('position')

    assigned = []
    for review in inserted_reviews:
        if review.product and review.product.status == 'ACTIVE':
            assigned.append({
                'id': review.product.id,
                'title': review.product.title,
                'position': review.position,
                'price': str(review.product.price)
            })

    return Response({
        'user_id': target_user.id,
        'username': target_user.username,
        'current_orders_made': current_orders_made,
        'orders_received_today': orders_received_today,
        'max_orders_by_level': min_orders,
        'start_continuous_orders_after': start_continuous_orders_after,
        'daily_available_orders': daily_available_orders,
        'assigned_products': assigned
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


@api_view(['GET'])
@permission_classes([IsAdminOrAgent])
def admin_user_account_details(request, user_id):
    try:
        target_user = User.objects.select_related('level', 'created_by').get(id=user_id, role='USER')
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
    if not request.user.is_admin and getattr(target_user, 'created_by', None) != request.user:
        return Response({'error': 'You can only view account details for users created by you'}, status=status.HTTP_403_FORBIDDEN)

    total_commission = ProductReview.objects.filter(
        user=target_user,
        status='COMPLETED'
    ).aggregate(total=Sum('commission_earned'))['total'] or Decimal('0.00')
    total_commission = float(total_commission)

    primary_wallet = (
        WithdrawalAccount.objects.filter(user=target_user)
        .order_by('-is_primary', '-is_active', '-created_at')
        .first()
    )
    if primary_wallet:
        raw_net = (primary_wallet.crypto_network or '').upper()
        wallet_currency = 'USDT' if raw_net == 'TRC20' else (raw_net if raw_net in ('USDT', 'USDC', 'ETH', 'BTC') else 'USDT')
        wallet_network = 'TRC 20' if raw_net == 'TRC20' else raw_net
        wallet_name = primary_wallet.crypto_wallet_name or None
        wallet_phone = getattr(primary_wallet.user, 'phone_number', None) or None
        wallet_address = primary_wallet.crypto_wallet_address or None
    else:
        wallet_name = None
        wallet_phone = None
        wallet_address = None
        wallet_network = None
        wallet_currency = None

    current_stage = 0
    available_for_daily_order = 0
    product_range = None
    membership = None
    if target_user.level:
        level = target_user.level
        membership = level.level_name
        min_orders = int(level.min_orders or 0)
        available_for_daily_order = min_orders
        pool_products = list(
            Product.objects.filter(status='ACTIVE').order_by('price')[:min_orders]
        )
        pool_ids = [p.id for p in pool_products]
        current_stage = ProductReview.objects.filter(
            user=target_user,
            product_id__in=pool_ids,
            status='COMPLETED'
        ).count()
        if getattr(target_user, 'matching_min_percent', None) is not None and getattr(target_user, 'matching_max_percent', None) is not None:
            min_pct = float(target_user.matching_min_percent)
            max_pct = float(target_user.matching_max_percent)
        else:
            min_pct = 30.0
            max_pct = 70.0
        product_range = f"{int(min_pct)}% - {int(max_pct)}%"
    progress = f"{current_stage}/{available_for_daily_order}" if available_for_daily_order else "0/0"

    def _dt(dt):
        if dt is None:
            return None
        return dt.strftime("%Y-%m-%d, %H:%M:%S")

    return Response({
        'id': target_user.id,
        'username': target_user.username,
        'invitation_code': target_user.invitation_code or None,
        'phone_number': target_user.phone_number or None,
        'superior_id': target_user.created_by_id,
        'superior_username': target_user.created_by.username if target_user.created_by else None,
        'registration_date': _dt(target_user.date_joined),
        'last_login': _dt(target_user.last_login),
        'balance': float(target_user.balance),
        'commission': total_commission,
        'froze_amount': float(target_user.balance_frozen_amount or 0),
        'membership': membership,
        'credibility': '100%',
        'account_status': 'ACTIVE' if target_user.is_active else 'INACTIVE',
        'rob_single': 'ALLOWED',
        'allow_withdrawal': 'ALLOWED',
        'wallet_name': wallet_name if primary_wallet else None,
        'wallet_phone': wallet_phone,
        'wallet_address': wallet_address if primary_wallet else None,
        'network_type': wallet_network if primary_wallet else None,
        'currency': wallet_currency if primary_wallet else None,
        'current_stage': current_stage,
        'available_for_daily_order': available_for_daily_order,
        'progress': progress,
        'product_range': product_range,
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsNormalUser])
def current_user_level_journey_completed(request):
    """
    Check if the logged-in user has completed their journey (first min_orders products by position).
    Not level-based: pool = all ACTIVE products, first min_orders; completed = all in pool done.
    Returns user_id and completed (true/false).
    """
    target_user = request.user
    if not target_user.level:
        return Response({
            'user_id': target_user.id,
            'completed': False
        }, status=status.HTTP_200_OK)

    min_orders = int(target_user.level.min_orders or 0)
    pool_products = list(
        Product.objects.filter(status='ACTIVE').order_by('price')[:min_orders]
    )
    total_items = len(pool_products)
    if total_items == 0:
        return Response({
            'user_id': target_user.id,
            'completed': False
        }, status=status.HTTP_200_OK)

    pool_ids = [p.id for p in pool_products]
    completed_count = ProductReview.objects.filter(
        user=target_user,
        product_id__in=pool_ids,
        status='COMPLETED'
    ).count()
    journey_completed = completed_count >= total_items

    return Response({
        'user_id': target_user.id,
        'completed': journey_completed
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAdminOrAgent])
def user_level_journey_completed(request, user_id):
    """
    Check if a user has completed their journey (first min_orders products by position).
    Not level-based: pool = all ACTIVE products, first min_orders; completed = all in pool done.
    Access: Admin can check any USER; Agent can check only users they created.
    """
    try:
        target_user = User.objects.get(id=user_id, role='USER')
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    if not request.user.is_admin and target_user.created_by != request.user:
        return Response({
            'error': 'You can only check level journey for users created by you'
        }, status=status.HTTP_403_FORBIDDEN)

    if not target_user.level:
        return Response({
            'user_id': target_user.id,
            'username': target_user.username,
            'level_id': None,
            'level_name': None,
            'total_items': 0,
            'completed_count': 0,
            'completed': False,
            'message': 'User has no level assigned.'
        }, status=status.HTTP_200_OK)

    level = target_user.level
    min_orders = int(level.min_orders or 0)
    pool_products = list(
        Product.objects.filter(status='ACTIVE').order_by('price')[:min_orders]
    )
    total_items = len(pool_products)
    if total_items == 0:
        return Response({
            'user_id': target_user.id,
            'username': target_user.username,
            'level_id': level.id,
            'level_name': level.level_name,
            'level_number': level.level,
            'total_items': 0,
            'completed_count': 0,
            'completed': False,
            'message': 'No products in pool (min_orders or ACTIVE products).'
        }, status=status.HTTP_200_OK)

    pool_ids = [p.id for p in pool_products]
    completed_count = ProductReview.objects.filter(
        user=target_user,
        product_id__in=pool_ids,
        status='COMPLETED'
    ).count()
    journey_completed = completed_count >= total_items

    return Response({
        'user_id': target_user.id,
        'username': target_user.username,
        'level_id': level.id,
        'level_name': level.level_name,
        'level_number': level.level,
        'total_items': total_items,
        'completed_count': completed_count,
        'completed': journey_completed,
        'message': 'Level journey completed.' if journey_completed else 'Level journey not yet completed.'
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAdminOrAgent])
def insert_product_at_position(request, product_id):
    """
    Insert a product at a specific position. Optionally for a specific user (user_id in body).
    - Updates the product's global position.
    - Per user: if user_id is provided, that user's ProductReview gets use_actual_price=True
      and position set; if that user had already completed this product, the review is reset to
      PENDING so the product shows again at the new position (re-insert after completion).
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

    target_user = None
    user_id = request.data.get('user_id')
    if user_id is not None:
        try:
            target_user = User.objects.get(id=user_id, role='USER')
        except User.DoesNotExist:
            return Response({
                'error': 'User not found or not a USER'
            }, status=status.HTTP_404_NOT_FOUND)
        if not request.user.is_admin and target_user.created_by != request.user:
            return Response({
                'error': 'You can only insert for users created by you'
            },             status=status.HTTP_403_FORBIDDEN)
    from django.db import transaction as db_transaction

    with db_transaction.atomic():
        current_position = product.position
        is_insert = current_position is None or current_position == 0

        if position == current_position:
            pass
        elif is_insert:
            Product.objects.exclude(id=product_id).filter(
                position__gte=position
            ).update(position=F('position') + 1)
            product.position = position
            product.save(update_fields=['position'])
        else:
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

        if target_user:
            ProductReview.objects.filter(
                user=target_user,
                product=product,
                status='COMPLETED'
            ).update(
                status='PENDING',
                completed_at=None,
                commission_earned=Decimal('0.00'),
                agreed_price=None,
                use_frozen_commission=False,
            )
            review, _ = ProductReview.objects.get_or_create(
                user=target_user,
                product=product,
                defaults={'status': 'PENDING'}
            )
            review.use_actual_price = True
            review.position = position
            review.save(update_fields=['use_actual_price', 'position'])

    product_data = ProductSerializer(product, context={'request': request, 'user': target_user or request.user}).data

    return Response({
        'message': f'Product moved to position {position} successfully' + (f' for user {target_user.id}' if target_user else ''),
        'product': product_data
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAdminOrAgent])
def admin_remove_product_for_user(request, user_id, product_id):
    """
    Remove a product from a user's list by deleting their ProductReview.
    Admin/Agent can remove for users they created.
    """
    try:
        target_user = User.objects.get(id=user_id, role='USER')
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)

    if not request.user.is_admin and target_user.created_by != request.user:
        return Response({'error': 'You can only remove products for users created by you'}, status=status.HTTP_403_FORBIDDEN)

    deleted_count, _ = ProductReview.objects.filter(user=target_user, product=product).delete()

    if deleted_count == 0:
        return Response({
            'message': 'No review found for this user and product',
            'user_id': target_user.id,
            'product_id': product.id
        }, status=status.HTTP_200_OK)

    return Response({
        'message': 'Product removed successfully',
        'user_id': target_user.id,
        'product_id': product.id
    }, status=status.HTTP_200_OK)


def _get_start_continuous_orders_after(user):
    """Get start_continuous_orders_after from user's level, or fallback to max(0, min_orders - 10)."""
    if not user or not user.level:
        return 0
    level = user.level
    val = getattr(level, 'start_continuous_orders_after', None)
    if val is not None:
        return max(0, int(val))
    min_orders = int(level.min_orders or 0)
    return max(0, min_orders - 10)


def _get_next_continuous_position(user):
    """Next position for Add/Replace = start_continuous_orders_after + 1 + count of products with position >= that."""
    start = _get_start_continuous_orders_after(user)
    continuous_start = start + 1
    count = ProductReview.objects.filter(
        user=user,
        position__gte=continuous_start
    ).count()
    return continuous_start + count


def reset_continuous_orders_for_user(target_user):
    """
    Clear continuous order assignments for a user (position and use_actual_price).
    If user has no level, clears all ProductReviews with position set; otherwise
    clears only position >= start_continuous_orders_after + 1.
    Returns number of ProductReviews updated.
    """
    if not target_user.level:
        return ProductReview.objects.filter(
            user=target_user, position__isnull=False
        ).update(position=None, use_actual_price=False)
    continuous_start = _get_start_continuous_orders_after(target_user) + 1
    return ProductReview.objects.filter(
        user=target_user,
        position__gte=continuous_start
    ).update(position=None, use_actual_price=False)


@api_view(['POST'])
@permission_classes([IsAdminOrAgent])
def admin_reset_continuous_orders(request, user_id):
    """
    Reset continuous orders for a user: clear position and use_actual_price for all
    ProductReviews with position >= start_continuous_orders_after + 1.
    """
    try:
        target_user = User.objects.get(id=user_id, role='USER')
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    if not request.user.is_admin and target_user.created_by != request.user:
        return Response({'error': 'You can only reset continuous orders for users created by you'}, status=status.HTTP_403_FORBIDDEN)

    if not target_user.level:
        return Response({'message': 'User has no level; no continuous orders to reset', 'user_id': target_user.id}, status=status.HTTP_200_OK)

    updated = reset_continuous_orders_for_user(target_user)

    return Response({
        'message': 'Continuous orders reset successfully',
        'user_id': target_user.id,
        'cleared_count': updated
    }, status=status.HTTP_200_OK)


@api_view(['POST', 'PATCH'])
@permission_classes([IsAdminOrAgent])
def admin_add_product_to_continuous_order(request, user_id, product_id):
    """
    Add product to continuous order. Position = start_continuous_orders_after + 1 + count.
    E.g. if start=8, first add -> position 9, second add -> position 10.
    """
    try:
        target_user = User.objects.get(id=user_id, role='USER')
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)

    if not request.user.is_admin and target_user.created_by != request.user:
        return Response({'error': 'You can only add products for users created by you'}, status=status.HTTP_403_FORBIDDEN)

    if not target_user.level:
        return Response({'error': 'User has no level assigned'}, status=status.HTTP_400_BAD_REQUEST)

    next_position = _get_next_continuous_position(target_user)
    review, _ = ProductReview.objects.get_or_create(
        user=target_user,
        product=product,
        defaults={'status': 'PENDING'}
    )
    review.use_actual_price = True
    review.position = next_position
    review.save(update_fields=['use_actual_price', 'position'])

    return Response({
        'message': f'Product added to continuous order at position {next_position}',
        'user_id': target_user.id,
        'product_id': product.id,
        'position': next_position
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAdminOrAgent])
def admin_replace_next_order(request, user_id, product_id):
    """
    Replace the product at the next continuous order slot.
    Same position logic as Add; overwrites if a product already occupies that slot.
    """
    try:
        target_user = User.objects.get(id=user_id, role='USER')
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)

    if not request.user.is_admin and target_user.created_by != request.user:
        return Response({'error': 'You can only replace orders for users created by you'}, status=status.HTTP_403_FORBIDDEN)

    if not target_user.level:
        return Response({'error': 'User has no level assigned'}, status=status.HTTP_400_BAD_REQUEST)

    next_position = _get_next_continuous_position(target_user)
    ProductReview.objects.filter(user=target_user, position=next_position).exclude(product=product).update(position=None, use_actual_price=False)
    review, _ = ProductReview.objects.get_or_create(
        user=target_user,
        product=product,
        defaults={'status': 'PENDING'}
    )
    review.use_actual_price = True
    review.position = next_position
    review.save(update_fields=['use_actual_price', 'position'])

    return Response({
        'message': f'Product set at next order position {next_position}',
        'user_id': target_user.id,
        'product_id': product.id,
        'position': next_position
    }, status=status.HTTP_200_OK)
