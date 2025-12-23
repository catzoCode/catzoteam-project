# task_management/admin.py
# FIXED VERSION - Compatible with your existing structure

from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Customer, Cat, ServiceRequest,
    TaskGroup, TaskType, TaskPackage, Task,
    TaskCompletion, PointRequest, Notification
)


# ============================================
# CUSTOMER & CAT ADMIN
# ============================================

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['customer_id', 'name', 'phone', 'email', 'ic_number', 'created_at']
    search_fields = ['customer_id', 'name', 'phone', 'email', 'ic_number']
    list_filter = ['created_at', 'registered_by']
    readonly_fields = ['customer_id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Customer Information', {
            'fields': ('customer_id', 'name', 'phone', 'email', 'ic_number')
        }),
        ('Contact Details', {
            'fields': ('address', 'emergency_contact')
        }),
        ('System Information', {
            'fields': ('registered_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Cat)
class CatAdmin(admin.ModelAdmin):
    list_display = ['cat_id', 'name', 'owner', 'breed', 'age', 'gender', 'vaccination_status', 'is_active']
    search_fields = ['cat_id', 'name', 'owner__name', 'owner__phone']
    list_filter = ['breed', 'gender', 'vaccination_status', 'is_active', 'registration_date']
    readonly_fields = ['cat_id', 'registration_date']
    
    fieldsets = (
        ('Cat Information', {
            'fields': ('cat_id', 'name', 'owner', 'breed', 'age', 'gender', 'color', 'weight')
        }),
        ('Health Information', {
            'fields': ('vaccination_status', 'medical_notes', 'special_requirements')
        }),
        ('Photo', {
            'fields': ('photo',)
        }),
        ('System Information', {
            'fields': ('is_active', 'registered_by', 'registration_date'),
            'classes': ('collapse',)
        }),
    )


# ============================================
# SERVICE REQUEST ADMIN (Front Desk)
# ============================================

@admin.register(ServiceRequest)
class ServiceRequestAdmin(admin.ModelAdmin):
    list_display = ['request_id', 'customer', 'cat', 'status_badge', 'preferred_date', 'created_by', 'created_at']
    search_fields = ['request_id', 'customer__name', 'cat__name']
    list_filter = ['status', 'created_at', 'preferred_date']
    readonly_fields = ['request_id', 'created_at', 'converted_to_package', 'converted_at', 'converted_by']
    
    fieldsets = (
        ('Request Information', {
            'fields': ('request_id', 'customer', 'cat', 'status')
        }),
        ('Service Details', {
            'fields': ('services_wanted', 'preferred_date', 'preferred_time', 'notes')
        }),
        ('System Information', {
            'fields': ('created_by', 'created_at'),
            'classes': ('collapse',)
        }),
        ('Conversion Tracking', {
            'fields': ('converted_to_package', 'converted_at', 'converted_by'),
            'classes': ('collapse',)
        }),
    )
    
    def status_badge(self, obj):
        colors = {
            'pending': 'warning',
            'assigned': 'info',
            'converted': 'success',
            'cancelled': 'danger'
        }
        color = colors.get(obj.status, 'secondary')
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'


# ============================================
# TASK GROUP & TYPE ADMIN
# ============================================

@admin.register(TaskGroup)
class TaskGroupAdmin(admin.ModelAdmin):
    list_display = ['group_id', 'name', 'task_count', 'is_active', 'order']
    search_fields = ['group_id', 'name']
    list_filter = ['is_active']
    readonly_fields = ['group_id', 'created_at']
    ordering = ['order', 'name']
    
    fieldsets = (
        ('Group Information', {
            'fields': ('group_id', 'name', 'description', 'is_active', 'order')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def task_count(self, obj):
        return obj.task_types.count()
    task_count.short_description = 'Tasks'


@admin.register(TaskType)
class TaskTypeAdmin(admin.ModelAdmin):
    list_display = ['task_type_id', 'name', 'group', 'points_display', 'price_display', 'is_active', 'order']
    search_fields = ['task_type_id', 'name', 'group__name']
    list_filter = ['group', 'is_active']
    readonly_fields = ['task_type_id', 'created_at']
    ordering = ['group', 'order', 'name']
    
    fieldsets = (
        ('Task Information', {
            'fields': ('task_type_id', 'group', 'name', 'description')
        }),
        ('Points & Pricing', {
            'fields': ('points', 'price', 'is_active', 'order')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def points_display(self, obj):
        return format_html(
            '<span style="background: #28a745; color: white; padding: 3px 8px; border-radius: 3px; font-weight: bold;">{} pts</span>',
            obj.points
        )
    points_display.short_description = 'Points'
    
    def price_display(self, obj):
        if obj.price:
            return format_html(
                '<span style="color: #007bff; font-weight: bold;">RM {}</span>',
                obj.price
            )
        return '-'
    price_display.short_description = 'Price'


# ============================================
# TASK PACKAGE & TASK ADMIN
# ============================================

@admin.register(TaskPackage)
class TaskPackageAdmin(admin.ModelAdmin):
    list_display = ['package_id', 'cat', 'customer_name', 'status_badge', 'task_count', 'total_points', 'email_sent', 'created_at']
    search_fields = ['package_id', 'cat__name', 'cat__owner__name']
    list_filter = ['status', 'email_sent', 'created_at']
    readonly_fields = ['package_id', 'total_points', 'email_sent_at', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Package Information', {
            'fields': ('package_id', 'cat', 'status', 'total_points', 'notes')
        }),
        ('Email Tracking', {
            'fields': ('email_sent', 'email_sent_at')
        }),
        ('System Information', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def customer_name(self, obj):
        return obj.cat.owner.name
    customer_name.short_description = 'Customer'
    
    def task_count(self, obj):
        return obj.tasks.count()
    task_count.short_description = 'Tasks'
    
    def status_badge(self, obj):
        colors = {
            'pending': 'warning',
            'assigned': 'info',
            'in_progress': 'primary',
            'completed': 'success',
            'cancelled': 'danger'
        }
        color = colors.get(obj.status, 'secondary')
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ['task_id', 'package', 'task_type', 'points', 'scheduled_date', 'scheduled_time', 'assigned_staff', 'status_badge']
    search_fields = ['task_id', 'package__package_id', 'package__cat__name', 'task_type__name', 'assigned_staff__username']
    list_filter = ['status', 'scheduled_date', 'task_type__group']
    readonly_fields = ['task_id', 'created_at', 'assigned_date', 'started_at', 'completed_at']
    date_hierarchy = 'scheduled_date'
    
    fieldsets = (
        ('Task Information', {
            'fields': ('task_id', 'package', 'task_type', 'points', 'status')
        }),
        ('Schedule', {
            'fields': ('scheduled_date', 'scheduled_time')
        }),
        ('Assignment', {
            'fields': ('assigned_staff', 'assigned_by', 'assigned_date')
        }),
        ('Progress', {
            'fields': ('notes', 'started_at', 'completed_at'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def status_badge(self, obj):
        colors = {
            'pending': 'warning',
            'assigned': 'info',
            'in_progress': 'primary',
            'completed': 'success',
            'cancelled': 'danger'
        }
        color = colors.get(obj.status, 'secondary')
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'


# ============================================
# TASK COMPLETION ADMIN
# ============================================

@admin.register(TaskCompletion)
class TaskCompletionAdmin(admin.ModelAdmin):
    list_display = ['id', 'task', 'completed_by', 'points_awarded', 'completed_at']
    search_fields = ['task__task_id', 'completed_by__username']
    list_filter = ['completed_at', 'completed_by']
    readonly_fields = ['completed_at', 'points_awarded_at']
    
    fieldsets = (
        ('Completion Information', {
            'fields': ('task', 'completed_by', 'completion_notes', 'photo_proof')
        }),
        ('Points', {
            'fields': ('points_awarded', 'points_awarded_at')
        }),
        ('Timestamps', {
            'fields': ('completed_at',),
            'classes': ('collapse',)
        }),
    )


# ============================================
# POINT REQUEST ADMIN - FIXED
# ============================================

@admin.register(PointRequest)
class PointRequestAdmin(admin.ModelAdmin):
    list_display = ['request_id', 'staff', 'task_type', 'points_requested', 'approval_badge', 'date_completed', 'created_at']
    search_fields = ['request_id', 'staff__username', 'staff__employee_id']
    list_filter = ['approval_status', 'reason', 'created_at', 'date_completed']
    readonly_fields = ['request_id', 'created_at', 'approved_at', 'points_awarded_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Request Information', {
            'fields': ('request_id', 'staff', 'task_type', 'points_requested', 'date_completed')
        }),
        ('Reason', {
            'fields': ('reason', 'reason_details', 'proof_photo')
        }),
        ('Approval', {
            'fields': ('approval_status', 'approved_by', 'approved_at', 'manager_notes')
        }),
        ('Points Award', {
            'fields': ('points_awarded', 'points_awarded_at'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['approve_requests', 'reject_requests']
    list_per_page = 50
    
    def approval_badge(self, obj):
        colors = {
            'pending': '#ffc107',
            'approved': '#28a745',
            'rejected': '#dc3545'
        }
        color = colors.get(obj.approval_status, '#6c757d')
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
            color, obj.get_approval_status_display()
        )
    approval_badge.short_description = 'Status'
    
    def approve_requests(self, request, queryset):
        count = 0
        for point_request in queryset.filter(approval_status='pending'):
            if hasattr(point_request, 'approve'):
                point_request.approve(request.user, 'Bulk approved from admin')
                count += 1
        self.message_user(request, f'{count} requests approved.')
    approve_requests.short_description = 'Approve selected requests'
    
    def reject_requests(self, request, queryset):
        count = 0
        for point_request in queryset.filter(approval_status='pending'):
            if hasattr(point_request, 'reject'):
                point_request.reject(request.user, 'Bulk rejected from admin')
                count += 1
        self.message_user(request, f'{count} requests rejected.')
    reject_requests.short_description = 'Reject selected requests'


# ============================================
# NOTIFICATION ADMIN
# ============================================

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'notification_type', 'title', 'is_read', 'created_at']
    search_fields = ['user__username', 'title', 'message']
    list_filter = ['notification_type', 'is_read', 'created_at']
    readonly_fields = ['created_at', 'read_at']
    date_hierarchy = 'created_at'
    
    actions = ['mark_as_read', 'mark_as_unread']
    
    fieldsets = (
        ('Notification Information', {
            'fields': ('user', 'notification_type', 'title', 'message', 'link')
        }),
        ('Status', {
            'fields': ('is_read', 'read_at')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def mark_as_read(self, request, queryset):
        from django.utils import timezone
        updated = queryset.update(is_read=True, read_at=timezone.now())
        self.message_user(request, f'{updated} notifications marked as read.')
    mark_as_read.short_description = 'Mark selected as read'
    
    def mark_as_unread(self, request, queryset):
        updated = queryset.update(is_read=False, read_at=None)
        self.message_user(request, f'{updated} notifications marked as unread.')
    mark_as_unread.short_description = 'Mark selected as unread'