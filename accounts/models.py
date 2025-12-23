# accounts/models.py
# UPDATED VERSION - Replace your current file with this

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import FileExtensionValidator

class User(AbstractUser):
    """
    Custom User model with role-based access
    """
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('manager', 'Manager'),
        ('staff', 'Staff'),
        ('registration', 'Registration Staff'),
    ]
    
    BRANCH_CHOICES = [
        ('hq', 'HQ (Headquarters)'),
        ('damansara_perdana', 'Damansara Perdana'),
        ('wangsa_maju', 'Wangsa Maju'),
        ('shah_alam', 'Shah Alam'),
        ('bangi', 'Bangi'),
        ('cheng_melaka', 'Cheng, Melaka'),
        ('johor_bahru', 'Johor Bahru'),
        ('seremban', 'Seremban 2'),
        ('seri_kembangan', 'Seri Kembangan'),
        ('usj21', 'USJ 21'),
        ('ipoh', 'Ipoh'),
    ]
    
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='staff')
    branch = models.CharField(max_length=50, choices=BRANCH_CHOICES, default='main')
    phone_number = models.CharField(max_length=15, blank=True)
    join_date = models.DateField(auto_now_add=True)
    profile_picture = models.ImageField(
        upload_to='profile_pics/',
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png'])]
    )
    employee_id = models.CharField(max_length=20, unique=True, blank=True)
    
    # Warning system
    warning_count = models.IntegerField(default=0)
    is_on_warning = models.BooleanField(default=False)
    warning_date = models.DateField(null=True, blank=True)
    
    class Meta:
        ordering = ['username']
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
    
    def save(self, *args, **kwargs):
        """Auto-generate CTZ employee ID if not set"""
        if not self.employee_id:
            self.employee_id = self.generate_employee_id()
        super().save(*args, **kwargs)
    
    def generate_employee_id(self):
        """
        Generate employee ID: CTZ001, CTZ002, ..., CTZ999, CTZ1000
        Starts with 3 digits, expands to 4 when reaching 1000
        """
        # Get the last user with employee_id starting with 'CTZ'
        last_user = User.objects.filter(
            employee_id__startswith='CTZ'
        ).order_by('-id').first()
        
        if last_user and last_user.employee_id:
            # Extract number from last employee_id
            try:
                last_number = int(last_user.employee_id[3:])
                new_number = last_number + 1
            except (ValueError, IndexError):
                new_number = 1
        else:
            # Check if there are any EMP IDs to maintain backward compatibility
            last_emp = User.objects.filter(
                employee_id__startswith='EMP'
            ).order_by('-id').first()
            
            if last_emp and last_emp.employee_id:
                try:
                    # Start CTZ numbering after EMP
                    emp_number = int(last_emp.employee_id[3:])
                    new_number = emp_number + 1
                except (ValueError, IndexError):
                    new_number = 1
            else:
                new_number = 1
        
        # Format with appropriate padding
        if new_number < 1000:
            return f"CTZ{new_number:03d}"  # CTZ001, CTZ002, ..., CTZ999
        else:
            return f"CTZ{new_number:04d}"  # CTZ1000, CTZ1001, ...


class UserProfile(models.Model):
    """
    Extended profile information for users
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField(blank=True)
    address = models.TextField(blank=True)
    emergency_contact_name = models.CharField(max_length=100, blank=True)
    emergency_contact_phone = models.CharField(max_length=15, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    
    def __str__(self):
        return f"Profile of {self.user.username}"