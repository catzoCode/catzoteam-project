# dashboard/urls.py
# COMPLETE URLs including AJAX endpoints

from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    # Home - auto redirects based on role
    path('', views.dashboard_home, name='home'),
    
    # Staff Dashboard
    path('staff/', views.staff_dashboard, name='staff_dashboard'),
    
    # Manager Dashboard
    path('manager/', views.manager_dashboard, name='manager_dashboard'),
    
    # Task Assignment
    path('packages/<str:package_id>/assign/', views.assign_task_package, name='assign_tasks'),
    
    # Task Approval
    path('tasks/<str:task_id>/approve/', views.approve_task, name='approve_task'),
    
    # Admin Dashboard
    path('admin/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/manage-staff/', views.admin_manage_staff_page, name='admin_manage_staff'),
    
    # ============================================
    # AJAX ENDPOINTS (These were missing!)
    # ============================================
    
    # Staff Management AJAX
    path('ajax/staff/create/', views.ajax_create_staff, name='ajax_create_staff'),
    path('ajax/staff/<int:user_id>/update/', views.ajax_update_staff, name='ajax_update_staff'),
    path('ajax/staff/<int:user_id>/soft-delete/', views.ajax_soft_delete_staff, name='ajax_soft_delete_staff'),
    path('ajax/staff/<int:user_id>/activate/', views.ajax_activate_staff, name='ajax_activate_staff'),
    path('ajax/staff/<int:user_id>/reset-password/', views.ajax_reset_staff_password, name='ajax_reset_password'),
    path('ajax/staff/<int:user_id>/performance/', views.ajax_staff_performance, name='ajax_staff_performance'),
    path('ajax/staff/<int:user_id>/reassign-tasks/', views.ajax_reassign_tasks, name='ajax_reassign_tasks'),
]