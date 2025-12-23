from django.urls import path
from . import views

urlpatterns = [
    path('calculator/', views.projection_calculator, name='projection_calculator'),
    path('my-points/', views.my_points_view, name='my_points'),
    path('my-incentives/', views.my_incentives_view, name='my_incentives'),   
    # Record points
    path('record/', views.record_points, name='record_points'),
    path('history/', views.points_history, name='points_history'),
]