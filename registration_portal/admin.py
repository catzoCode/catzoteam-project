# registration_portal/admin.py
# Admin interface for registration portal

from django.contrib import admin
from .models import RegistrationSession


@admin.register(RegistrationSession)
class RegistrationSessionAdmin(admin.ModelAdmin):
    list_display = ['user', 'login_time', 'logout_time', 'is_active', 'customers_registered', 'cats_registered', 'service_requests_created']
    list_filter = ['is_active', 'login_time']
    search_fields = ['user__username', 'user__employee_id']
    readonly_fields = ['login_time', 'logout_time']
    
    fieldsets = (
        ('Session Information', {
            'fields': ('user', 'login_time', 'logout_time', 'is_active')
        }),
        ('Statistics', {
            'fields': ('customers_registered', 'cats_registered', 'service_requests_created')
        }),
    )