# task_management/urls.py
# COMPLETE UPDATED FILE - Replace your existing file with this

from django.urls import path
from . import views

app_name = 'task_management'

urlpatterns = [
    # ============================================
    # REGISTRATION WIZARD (3 steps) - EXISTING
    # ============================================
    path('register/step1/', views.register_service_step1, name='register_step1'),
    path('register/step1/create/', views.register_service_step1_create, name='register_step1_create'),
    path('register/step2/<str:customer_id>/', views.register_service_step2, name='register_step2'),
    path('register/step2/<str:customer_id>/add-cat/', views.register_service_step2_add_cat, name='register_step2_add_cat'),
    path('register/step3/', views.register_service_step3, name='register_step3'),
    
    # ============================================
    # MANAGER: ASSIGN TASKS - EXISTING
    # ============================================
    path('unassigned/', views.unassigned_packages, name='unassigned_packages'),
    path('task/<str:task_id>/assign/', views.assign_task, name='assign_task'),
    
    # ============================================
    # STAFF: MY TASKS - EXISTING (Keep for backward compatibility)
    # ============================================
    path('my-tasks/', views.my_tasks, name='my_tasks'),
    path('complete/<str:task_id>/', views.complete_task, name='complete_task'),
    
    # ============================================
    # STAFF: ENHANCED TASK VIEWS - NEW
    # ============================================
    path('tasks/my-tasks/', views.my_tasks_view, name='my_tasks_new'),
    path('tasks/complete/<str:task_id>/', views.complete_task_with_proof, name='complete_task_with_proof'),
    
    # ============================================
    # STAFF: CUSTOM POINT REQUESTS - NEW
    # ============================================
    path('tasks/request-points/', views.request_custom_points, name='request_custom_points'),
    path('tasks/my-requests/', views.my_point_requests, name='my_point_requests'),
    
    # ============================================
    # MANAGER: STAFF TASKS (BRANCH) - NEW
    # ============================================
    path('manager/staff-tasks/', views.staff_tasks_branch, name='staff_tasks_branch'),
    
    # ============================================
    # ADMIN: MONITOR ALL TASKS - NEW
    # ============================================
    path('admin/all-tasks/', views.admin_all_tasks_monitor, name='admin_all_tasks_monitor'),
    path('admin/point-requests/', views.admin_point_requests, name='admin_point_requests'),
    path('admin/point-request/<int:pk>/review/', views.review_point_request, name='review_point_request'),
    path('closing-report/submit/', 
         views.submit_closing_report, 
         name='submit_closing_report'),
    
    path('closing-report/my-reports/', 
         views.my_closing_reports, 
         name='my_closing_reports'),
    
    path('closing-report/analytics/', 
         views.manager_analytics_dashboard, 
         name='manager_analytics_dashboard'),
    
    # ============================================
    # CLOSING REPORTS - ADMIN
    # ============================================
    path('admin/closing-reports/', 
         views.admin_all_closing_reports, 
         name='admin_all_closing_reports'),
    
    path('admin/closing-reports/analytics/', 
         views.admin_analytics_dashboard, 
         name='admin_analytics_dashboard'),
    
    path('admin/closing-reports/export/', 
         views.export_reports_excel, 
         name='export_reports_excel'),
    # ============================================
    # MANAGE TASKS - Task Types & Groups
    # ============================================

    # Main page
    path('admin/manage-tasks/', views.admin_manage_tasks_page, name='admin_manage_tasks'),

    # Task Group AJAX operations
    path('ajax/task-group/create/', views.ajax_create_task_group, name='ajax_create_task_group'),
    path('ajax/task-group/<str:group_id>/update/', views.ajax_update_task_group, name='ajax_update_task_group'),
    path('ajax/task-group/<str:group_id>/delete/', views.ajax_delete_task_group, name='ajax_delete_task_group'),
    path('ajax/task-group/<str:group_id>/reorder/', views.ajax_reorder_group, name='ajax_reorder_group'),

    # Task Type AJAX operations
    path('ajax/task-type/create/', views.ajax_create_task_type, name='ajax_create_task_type'),
    path('ajax/task-type/<str:type_id>/update/', views.ajax_update_task_type, name='ajax_update_task_type'),
    path('ajax/task-type/<str:type_id>/delete/', views.ajax_delete_task_type, name='ajax_delete_task_type'),
    path('ajax/task-type/<str:type_id>/reorder/', views.ajax_reorder_task_type, name='ajax_reorder_task_type'),

    # ============================================
    # MANAGE STAFF
    # ============================================

    # Main page
    path('admin/manage-staff-page/', views.admin_manage_staff_page, name='admin_manage_staff_page'),

    # Staff AJAX operations
    path('ajax/staff/create/', views.ajax_create_staff, name='ajax_create_staff'),
    path('ajax/staff/<int:user_id>/update/', views.ajax_update_staff, name='ajax_update_staff'),
    path('ajax/staff/<int:user_id>/soft-delete/', views.ajax_soft_delete_staff, name='ajax_soft_delete_staff'),
    path('ajax/staff/<int:user_id>/activate/', views.ajax_activate_staff, name='ajax_activate_staff'),
    path('ajax/staff/<int:user_id>/reset-password/', views.ajax_reset_staff_password, name='ajax_reset_staff_password'),
    path('ajax/staff/<int:user_id>/performance/', views.ajax_staff_performance, name='ajax_staff_performance'),
    path('ajax/staff/<int:user_id>/reassign-tasks/', views.ajax_reassign_tasks, name='ajax_reassign_tasks'),

]