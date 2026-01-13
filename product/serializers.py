from rest_framework import serializers
from .models import Product


class ProductSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    
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
            'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'image_url']
    
    def get_image_url(self, obj):
        """Return full URL for the image"""
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None
    
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

