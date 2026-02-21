from django.contrib import admin
from .models import Product, ProductReview


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'position',
        'title',
        'price',
        'status',
        'created_at'
    ]
    list_editable = ['position']
    list_filter = ['status', 'created_at']
    search_fields = ['title', 'description']
    ordering = ['position', '-created_at']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'image', 'status')
        }),
        ('Pricing', {
            'fields': ('price',)
        }),
        ('Ordering', {
            'fields': ('position', 'use_actual_price')
        }),
        ('Additional Information', {
            'fields': ('created_at',)
        }),
    )


@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'user',
        'product',
        'status',
        'position',
        'use_actual_price',
        'use_frozen_commission',
        'agreed_price',
        'commission_earned',
        'created_at',
        'completed_at'
    ]
    list_filter = ['status', 'created_at', 'completed_at']
    search_fields = ['user__username', 'user__email', 'product__title', 'review_text']
    ordering = ['user', 'position', '-created_at']
    readonly_fields = ['created_at']
    raw_id_fields = ['user', 'product']
    
    fieldsets = (
        ('Review Information', {
            'fields': ('user', 'product', 'review_text', 'status')
        }),
        ('Commission', {
            'fields': ('position', 'use_actual_price', 'use_frozen_commission', 'agreed_price', 'commission_earned')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'completed_at')
        }),
    )
