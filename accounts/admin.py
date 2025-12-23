from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, UserProfile

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'employee_id', 'role', 'branch', 'is_staff', 'is_on_warning']
    list_filter = ['role', 'branch', 'is_staff', 'is_active', 'is_on_warning']
    search_fields = ['username', 'email', 'employee_id', 'first_name', 'last_name']
    
    # Simplified fieldsets
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'email', 'phone_number')}),
        ('Employee Info', {'fields': ('role', 'branch')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'role', 'branch'),
        }),
    )

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'date_of_birth', 'emergency_contact_name']
    search_fields = ['user__username', 'emergency_contact_name']