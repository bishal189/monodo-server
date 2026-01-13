from django.contrib import admin
from .models import Level


@admin.register(Level)
class LevelAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'level',
        'level_name',
        'required_points',
        'commission_rate',
        'min_orders',
        'status',
        'created_at'
    ]
    list_filter = ['status', 'created_at']
    search_fields = ['level_name', 'level']
    ordering = ['level']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('level', 'level_name', 'status')
        }),
        ('Requirements', {
            'fields': ('required_points', 'min_orders', 'commission_rate')
        }),
        ('Additional Information', {
            'fields': ('benefits', 'created_at')
        }),
    )
