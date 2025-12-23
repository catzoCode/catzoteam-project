# registration_portal/urls.py
# URL configuration for registration portal

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
    path('customer/<str:customer_id>/service/create/', views.create_service_request, name='create_service_request'),
]