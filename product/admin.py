from django.contrib import admin

from .models import Product, ProductReview


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'price', 'status', 'position', 'use_actual_price', 'created_at')
    list_filter = ('status', 'use_actual_price')
    search_fields = ('title', 'description')
    ordering = ('position', '-created_at')


@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    """User order slots / continuous orders (table: product_reviews)."""

    list_display = (
        'id',
        'user',
        'product',
        'status',
        'position',
        'use_actual_price',
        'commission_earned',
        'created_at',
        'completed_at',
    )
    list_filter = ('status', 'use_actual_price', 'use_frozen_commission')
    search_fields = ('user__username', 'user__email', 'product__title')
    raw_id_fields = ('user', 'product')
    ordering = ('-created_at',)
    list_select_related = ('user', 'product')
