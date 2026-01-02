# registration_portal/urls.py
# UPDATED with Next Booking System routes

from django.urls import path
from . import views

app_name = 'registration_portal'

urlpatterns = [
    # Login/Logout
    path('', views.registration_login, name='login'),
    path('login/', views.registration_login, name='login'),
    path('logout/', views.registration_logout, name='logout'),
    
    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Customer
    path('customer/search/', views.customer_search, name='customer_search'),
    path('customer/register/', views.register_customer, name='register_customer'),
    path('customer/<str:customer_id>/', views.customer_detail, name='customer_detail'),
    
    # Cat
    path('customer/<str:customer_id>/cat/register/', views.register_cat, name='register_cat'),
    
    # Service Request
    path('service/create/', views.create_service_request, name='create_service_request'),
    path('customer/<str:customer_id>/service/create/', views.create_service_request, name='create_service_request'),
    
    # AJAX Endpoints
    path('ajax/search-tasks/', views.ajax_search_tasks, name='ajax_search_tasks'),
    path('ajax/task-details/<int:task_type_id>/', views.get_task_details, name='get_task_details'),
    
    # ========== NEXT BOOKING SYSTEM ROUTES ==========
    
    # Manager Arrivals Page
    path('manager/arrivals/', views.manager_arrivals, name='manager_arrivals'),
    
    # Confirm Arrival (Release Points)
    path('arrivals/confirm/<str:package_id>/', views.confirm_arrival, name='confirm_arrival'),
    
    # Mark No-Show (Don't Award Points)
    path('arrivals/no-show/<str:package_id>/', views.mark_no_show, name='mark_no_show'),
    
    # Auto-Crosscheck Customer
    path('arrivals/auto-check/<str:customer_id>/', views.auto_crosscheck_customer, name='auto_crosscheck_customer'),
]