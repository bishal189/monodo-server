from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = [
        'email', 'username', 'phone_number', 'role', 'created_by', 'level',
        'balance', 'balance_frozen', 'balance_frozen_amount', 'credibility',
        'completed_products_count',
        'withdrawal_min_amount', 'withdrawal_max_amount', 'allow_rob_order', 'allow_withdrawal',
        'number_of_draws', 'winning_amount', 'custom_winning_amount',
        'is_active', 'is_staff', 'date_joined'
    ]
    list_filter = ['role', 'is_active', 'is_staff', 'is_superuser', 'is_training_account', 'date_joined']
    search_fields = ['email', 'username', 'phone_number', 'invitation_code']
    ordering = ['-date_joined']
    raw_id_fields = ['created_by', 'level', 'original_account']

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('username', 'phone_number', 'invitation_code')}),
        ('Hierarchy', {'fields': ('created_by', 'level', 'original_account', 'is_training_account')}),
        ('Account & balance', {
            'fields': (
                'balance', 'balance_frozen', 'balance_frozen_amount',
                'credibility', 'completed_products_count',
            ),
        }),
        ('Withdrawal', {
            'fields': (
                'withdrawal_min_amount', 'withdrawal_max_amount',
                'withdrawal_needed_to_complete_order', 'allow_withdrawal',
            ),
        }),
        ('Matching & orders', {
            'fields': (
                'matching_min_percent', 'matching_max_percent',
                'allow_rob_order', 'number_of_draws',
                'winning_amount', 'custom_winning_amount',
            ),
        }),
        ('Security', {'fields': ('withdraw_password',)}),
        ('Role & Permissions', {'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'phone_number', 'password1', 'password2', 'role', 'is_staff', 'is_superuser'),
        }),
    )

    readonly_fields = ['date_joined', 'last_login']
