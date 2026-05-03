from django.contrib import admin

from .models import Contact


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ('phone_number', 'updated_at')
    fields = ('phone_number', 'updated_at')
    readonly_fields = ('updated_at',)
