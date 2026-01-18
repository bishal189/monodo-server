from django.contrib import admin
from .models import Transaction, WithdrawalAccount


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


@admin.register(WithdrawalAccount)
class WithdrawalAccountAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'user',
        'account_holder_name',
        'bank_name',
        'account_number',
        'account_type',
        'is_active',
        'is_primary',
        'created_at'
    ]
    list_filter = ['account_type', 'is_active', 'is_primary', 'created_at']
    search_fields = ['user__email', 'user__username', 'account_holder_name', 'bank_name', 'account_number']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Account Information', {
            'fields': ('user', 'account_holder_name', 'bank_name', 'account_number', 'routing_number', 'account_type')
        }),
        ('Status', {
            'fields': ('is_active', 'is_primary')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
