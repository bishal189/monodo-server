from django.contrib import admin
from .models import Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'title',
        'price',
        'status',
        'created_at'
    ]
    list_filter = ['status', 'created_at']
    search_fields = ['title', 'description']
    ordering = ['-created_at']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'image', 'status')
        }),
        ('Pricing', {
            'fields': ('price',)
        }),
        ('Additional Information', {
            'fields': ('created_at',)
        }),
    )
