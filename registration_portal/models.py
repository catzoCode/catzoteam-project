# registration_portal/models.py
# Simple session tracking for registration portal

from django.db import models
from django.conf import settings
from django.utils import timezone
import json

class RegistrationSession(models.Model):
    """Track registration portal login sessions"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='registration_sessions'
    )
    login_time = models.DateTimeField(auto_now_add=True)
    logout_time = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    # Statistics
    customers_registered = models.IntegerField(default=0)
    cats_registered = models.IntegerField(default=0)
    service_requests_created = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['-login_time']
    
    def __str__(self):
        return f"{self.user.username} - {self.login_time.strftime('%Y-%m-%d %H:%M')}"
    
    def end_session(self):
        """Mark session as ended"""
        self.is_active = False
        self.logout_time = timezone.now()
        self.save()