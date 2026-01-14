from django.contrib import admin
from .models import Transaction


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'transaction_id',
        'member_account',
        'type',
        'amount',
        'status',
        'created_at'
    ]
    list_filter = ['type', 'status', 'remark_type', 'created_at']
    search_fields = ['transaction_id', 'member_account__email', 'member_account__username']
    readonly_fields = ['transaction_id', 'created_at']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Transaction Information', {
            'fields': ('transaction_id', 'member_account', 'type', 'amount', 'status')
        }),
        ('Remarks', {
            'fields': ('remark_type', 'remark')
        }),
        ('Additional Information', {
            'fields': ('created_at',)
        }),
    )
    
    def get_readonly_fields(self, request, obj=None):
        if obj:  # editing an existing object
            return self.readonly_fields + ['transaction_id']
        return self.readonly_fields
