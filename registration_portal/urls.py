# registration_portal/urls.py
from django.urls import path
from . import views

app_name = 'registration_portal'

urlpatterns = [
    # Authentication
    path('', views.registration_login, name='login'),
    path('login/', views.registration_login, name='login'),
    path('logout/', views.registration_logout, name='logout'),
    
    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Customer Management
    path('customer/search/', views.customer_search, name='customer_search'),
    path('customer/register/', views.register_customer, name='register_customer'),
    path('customer/<str:customer_id>/', views.customer_detail, name='customer_detail'),
    
    # Cat Registration
    path('cat/register/<str:customer_id>/', views.register_cat, name='register_cat'),
    
    # Service Request / Booking
    path('booking/create/', views.create_service_request, name='create_service_request'),
    path('booking/create/<str:customer_id>/', views.create_service_request, name='create_service_request'),
    
    # Pending Bookings (NEW!)
    path('pending-bookings/', views.pending_bookings, name='pending_bookings'),
    path('pending-bookings/confirm/<str:booking_id>/', views.confirm_pending_booking, name='confirm_pending_booking'),
    path('pending-bookings/cancel/<str:booking_id>/', views.cancel_pending_booking, name='cancel_pending_booking'),
    
    # Booking History (NEW!)
    path('my-bookings/', views.my_bookings, name='my_bookings'),
    path('branch-bookings/', views.branch_bookings, name='branch_bookings'),
    
    # OCR Screenshot Upload
    path('upload-screenshot/', views.upload_screenshot, name='upload_screenshot'),
    path('review-ocr/', views.review_ocr_data, name='review_ocr_data'),
    
    # Manager Arrivals
    path('manager/arrivals/', views.manager_arrivals, name='manager_arrivals'),
    path('arrivals/confirm/<str:package_id>/', views.confirm_arrival, name='confirm_arrival'),
    path('arrivals/no-show/<str:package_id>/', views.mark_no_show, name='mark_no_show'),
]