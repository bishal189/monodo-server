from rest_framework import serializers
from .models import Product, ProductReview
from authentication.models import User


class ProductSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    review_status = serializers.SerializerMethodField()
    potential_commission = serializers.SerializerMethodField()
    commission_amount = serializers.SerializerMethodField()
    commission_rate = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = [
            'id',
            'image',
            'image_url',
            'title',
            'description',
            'price',
            'status',
            'position',
            'review_status',
            'potential_commission',
            'commission_amount',
            'commission_rate',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'image_url', 'review_status', 'potential_commission', 'commission_amount', 'commission_rate']
    
    def get_image_url(self, obj):
        """Return full URL for the image"""
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None
    
    def get_review_status(self, obj):
        """Return review status for the current user"""
        user = self.context.get('user')
        if not user or not user.is_authenticated:
            return None
        
        review = obj.reviews.filter(user=user).first()
        if review:
            return review.status
        return 'NOT_COMPLETED'
    
    def get_potential_commission(self, obj):
        """Calculate potential commission for the current user based on their level"""
        from decimal import Decimal
        user = self.context.get('user')
        if not user or not user.is_authenticated or not user.level:
            return None
        
        commission_rate = user.level.commission_rate
        commission_amount = (obj.price * commission_rate) / Decimal('100')
        return float(commission_amount)
    
    def get_commission_amount(self, obj):
        """Calculate commission amount for the current user based on their level"""
        from decimal import Decimal
        user = self.context.get('user')
        if not user or not user.is_authenticated or not user.level:
            return None
        
        commission_rate = user.level.commission_rate
        commission_amount = (obj.price * commission_rate) / Decimal('100')
        return float(commission_amount)
    
    def get_commission_rate(self, obj):
        """Return commission rate percentage for the current user's level"""
        user = self.context.get('user')
        if not user or not user.is_authenticated or not user.level:
            return None
        
        return float(user.level.commission_rate)
    
    def validate_price(self, value):
        """Ensure price is positive"""
        if value < 0:
            raise serializers.ValidationError("Price must be non-negative.")
        return value
    
    def validate_title(self, value):
        """Ensure title is not empty"""
        if not value or not value.strip():
            raise serializers.ValidationError("Title cannot be empty.")
        return value.strip()


class ProductCreateSerializer(ProductSerializer):
    """Serializer for creating products"""
    image = serializers.ImageField(required=False, allow_null=True)
    title = serializers.CharField(required=True, max_length=200)
    description = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    price = serializers.DecimalField(max_digits=10, decimal_places=2, required=True)
    status = serializers.ChoiceField(choices=Product.STATUS_CHOICES, required=False, default='ACTIVE')


class ProductUpdateSerializer(ProductSerializer):
    """Serializer for updating products"""
    image = serializers.ImageField(required=False, allow_null=True)
    title = serializers.CharField(required=False, max_length=200)
    description = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    status = serializers.ChoiceField(choices=Product.STATUS_CHOICES, required=False)


class AssignProductsToLevelSerializer(serializers.Serializer):
    """Serializer for assigning multiple products to a level"""
    level_id = serializers.IntegerField(required=True)
    product_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=True,
        allow_empty=True,
        help_text="List of product IDs to assign. Empty list removes all products from the level."
    )
    
    def validate_level_id(self, value):
        """Validate that the level exists and is active"""
        try:
            from level.models import Level
            level = Level.objects.get(id=value)
            if level.status != 'ACTIVE':
                raise serializers.ValidationError("Cannot assign products to an inactive level.")
        except Level.DoesNotExist:
            raise serializers.ValidationError("Level with this ID does not exist.")
        return value
    
    def validate_product_ids(self, value):
        """Validate that all products exist"""
        if not value:
            return value  # Empty list is allowed (to remove all assignments)
        
        existing_products = Product.objects.filter(id__in=value)
        existing_ids = set(existing_products.values_list('id', flat=True))
        invalid_ids = set(value) - existing_ids
        
        if invalid_ids:
            raise serializers.ValidationError(f"Products with IDs {list(invalid_ids)} do not exist.")
        
        return value


class ProductReviewSerializer(serializers.ModelSerializer):
    product_title = serializers.CharField(source='product.title', read_only=True)
    product_price = serializers.DecimalField(source='product.price', max_digits=10, decimal_places=2, read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    
    class Meta:
        model = ProductReview
        fields = [
            'id',
            'user',
            'username',
            'user_email',
            'product',
            'product_title',
            'product_price',
            'review_text',
            'status',
            'commission_earned',
            'created_at',
            'completed_at'
        ]
        read_only_fields = ['id', 'status', 'commission_earned', 'created_at', 'completed_at']


class SubmitProductReviewSerializer(serializers.Serializer):
    """Serializer for submitting a product review"""
    product_id = serializers.IntegerField(required=True)
    review_text = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    
    def validate_product_id(self, value):
        """Validate that the product exists and is available to user"""
        try:
            product = Product.objects.get(id=value)
        except Product.DoesNotExist:
            raise serializers.ValidationError("Product with this ID does not exist.")
        return value
    
    def validate(self, attrs):
        """Validate that user can review this product"""
        user = self.context['user']
        product_id = attrs.get('product_id')
        
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            raise serializers.ValidationError("Product not found.")
        
        if product.status != 'ACTIVE':
            raise serializers.ValidationError("Cannot review inactive products.")
        
        if not user.level:
            raise serializers.ValidationError("You must have a level assigned to review products.")
        
        if not product.levels.filter(id=user.level.id).exists():
            raise serializers.ValidationError("This product is not available for your level.")
        
        return attrs

