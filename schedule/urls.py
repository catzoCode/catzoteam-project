# schedule/urls.py
# URL patterns for schedule management system

from django.urls import path
from . import views

app_name = 'schedule'

urlpatterns = [
    
    # ============================================
    # ADMIN ROUTES
    # ============================================
    
    # Calendar views
    path('admin/calendar/', views.admin_schedule_calendar, name='admin_calendar'),
    
    # Schedule management
    path('admin/create/', views.admin_create_schedule, name='admin_create_schedule'),
    path('admin/bulk-create/', views.admin_bulk_create, name='admin_bulk_create'),
    path('admin/edit/<int:schedule_id>/', views.admin_edit_schedule, name='admin_edit_schedule'),
    path('admin/delete/<int:schedule_id>/', views.admin_delete_schedule, name='admin_delete_schedule'),
    
    # Leave requests
    path('admin/leave-requests/', views.manager_leave_requests, name='admin_leave_requests'),
    path('admin/leave/<int:leave_id>/approve/', views.manager_approve_leave, name='admin_approve_leave'),
    
    # Shift swaps
    path('admin/swap-requests/', views.manager_swap_requests, name='admin_swap_requests'),
    path('admin/swap/<int:swap_id>/approve/', views.manager_approve_swap, name='admin_approve_swap'),
    
    # PDF Export
    path('admin/export-pdf/', views.export_admin_schedule_pdf, name='admin_export_pdf'),
    
    # ============================================
    # MANAGER ROUTES
    # ============================================
    
    # Calendar views
    path('manager/calendar/', views.manager_schedule_calendar, name='manager_calendar'),
    
    # Schedule management
    path('manager/create/', views.manager_create_schedule, name='manager_create_schedule'),  # ✅ FIXED
    path('manager/edit/<int:schedule_id>/', views.manager_edit_schedule, name='manager_edit_schedule'),  # ✅ NEW
    path('manager/delete/<int:schedule_id>/', views.manager_delete_schedule, name='manager_delete_schedule'),  # ✅ NEW
    
    # Leave requests
    path('manager/leave-requests/', views.manager_leave_requests, name='manager_leave_requests'),
    path('manager/leave/<int:leave_id>/approve/', views.manager_approve_leave, name='manager_approve_leave'),
    path('manager/my-leaves/', views.manager_my_leaves, name='manager_my_leaves'),  # ✅ ADDED
    
    # Shift swaps
    path('manager/swap-requests/', views.manager_swap_requests, name='manager_swap_requests'),
    path('manager/swap/<int:swap_id>/approve/', views.manager_approve_swap, name='manager_approve_swap'),
    
    # PDF Export
    path('manager/export-pdf/', views.export_manager_schedule_pdf, name='manager_export_pdf'),
    path('manager/my-schedule/',views.manager_my_schedule,name='manager_my_schedule'),
    
    # ============================================
    # STAFF ROUTES
    # ============================================
    
    # View schedule
    path('my-schedule/', views.staff_my_schedule, name='staff_my_schedule'),
    
    # Leave requests
    path('request-leave/', views.staff_request_leave, name='staff_request_leave'),
    path('my-leaves/', views.staff_my_leaves, name='staff_my_leaves'),
    
    # Shift swaps
    path('request-swap/', views.staff_request_swap, name='staff_request_swap'),
    path('my-swaps/', views.staff_my_swaps, name='staff_my_swaps'),
    path('swap/<int:swap_id>/respond/', views.staff_respond_swap, name='staff_respond_swap'),
    
    # PDF Export
    path('export-my-schedule-pdf/', views.export_staff_schedule_pdf, name='staff_export_pdf'),
    path('export/staff/pdf/', views.export_staff_pdf, name='export_staff_pdf'),

]