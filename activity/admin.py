from django.contrib import admin
from .models import LoginActivity


@admin.register(LoginActivity)
class LoginActivityAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'ip_address', 'browser', 'operating_system', 'device_type', 'login_time']
    list_filter = ['device_type', 'login_time', 'operating_system']
    search_fields = ['user__email', 'user__username', 'ip_address', 'browser']
    readonly_fields = ['login_time']
    ordering = ['-login_time']
    
    fieldsets = (
        ('User Information', {
            'fields': ('user',)
        }),
        ('Login Details', {
            'fields': ('ip_address', 'browser', 'operating_system', 'device_type', 'login_time')
        }),
    )
