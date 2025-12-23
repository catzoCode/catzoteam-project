from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect

urlpatterns = [
    path('admin/', admin.site.urls),
    path("accounts/", include(("accounts.urls", "accounts"), namespace="accounts")),
    path("dashboard/", include("dashboard.urls", namespace="dashboard")),  
    path('performance/', include('performance.urls')),
    path('schedule/', include('schedule.urls')),
    path('task-management/', include('task_management.urls')),
    path('registration/', include('registration_portal.urls')),
    
    # Root URL - redirect to dashboard home which will route based on role
    path('', lambda request: redirect('/accounts/login/')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)