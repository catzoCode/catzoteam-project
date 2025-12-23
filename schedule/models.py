# schedule/models.py
# Complete Schedule System Models

from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import datetime, time

class Schedule(models.Model):
    """Staff work schedule"""
    
    SHIFT_TYPE_CHOICES = [
        ('morning', 'Morning'),
        ('afternoon', 'Afternoon'),
        ('evening', 'Evening'),
        ('night', 'Night'),
        ('full_day', 'Full Day'),
        ('off', 'OFF/Rest Day'),
    ]
    
    # Core fields
    staff = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='work_schedules',
        help_text="Staff member assigned to this schedule"
    )
    date = models.DateField(help_text="Schedule date")
    shift_type = models.CharField(
        max_length=20,
        choices=SHIFT_TYPE_CHOICES,
        help_text="Type of shift"
    )
    start_time = models.TimeField(
        null=True,
        blank=True,
        help_text="Shift start time (null for OFF days)"
    )
    end_time = models.TimeField(
        null=True,
        blank=True,
        help_text="Shift end time (null for OFF days)"
    )
    
    # Additional info
    branch = models.CharField(
        max_length=50,
        help_text="Branch where staff works this shift"
    )
    notes = models.TextField(
        blank=True,
        help_text="Additional notes (optional)"
    )
    
    # Metadata
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='schedules_created',
        help_text="Admin/Manager who created this schedule"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['date', 'start_time', 'staff']
        unique_together = ['staff', 'date']  # One schedule per staff per day
        indexes = [
            models.Index(fields=['date', 'staff']),
            models.Index(fields=['staff', 'date']),
            models.Index(fields=['branch', 'date']),
        ]
    
    def __str__(self):
        if self.shift_type == 'off':
            return f"{self.staff.username} - {self.date} - OFF"
        return f"{self.staff.username} - {self.date} - {self.start_time} to {self.end_time}"
    
    def clean(self):
        """Validate schedule"""
        # OFF days don't need times
        if self.shift_type == 'off':
            self.start_time = None
            self.end_time = None
            return
        
        # Working days must have times
        if not self.start_time or not self.end_time:
            raise ValidationError("Start time and end time are required for working days.")
        
        # End time must be after start time (handle overnight shifts)
        if self.start_time >= self.end_time:
            # Allow overnight shifts (e.g., 10 PM to 6 AM next day)
            pass
        
        # Check for double booking (same staff, same date, overlapping times)
        overlapping = Schedule.objects.filter(
            staff=self.staff,
            date=self.date
        ).exclude(pk=self.pk)
        
        if overlapping.exists():
            raise ValidationError(
                f"{self.staff.username} is already scheduled on {self.date}. "
                "Please delete the existing schedule first or choose a different date."
            )
        
        # Check if staff has approved leave on this date
        from schedule.models import LeaveRequest
        has_leave = LeaveRequest.objects.filter(
            staff=self.staff,
            start_date__lte=self.date,
            end_date__gte=self.date,
            status='approved'
        ).exists()
        
        if has_leave:
            raise ValidationError(
                f"{self.staff.username} has approved leave on {self.date}. "
                "Cannot create schedule."
            )
    
    def save(self, *args, **kwargs):
        """Override save to run validations"""
        self.clean()
        
        # Auto-set branch from staff if not provided
        if not self.branch and self.staff:
            self.branch = self.staff.branch
        
        super().save(*args, **kwargs)
    
    def get_duration_hours(self):
        """Calculate shift duration in hours"""
        if not self.start_time or not self.end_time:
            return 0
        
        # Create datetime objects for today
        today = datetime.today().date()
        start_dt = datetime.combine(today, self.start_time)
        end_dt = datetime.combine(today, self.end_time)
        
        # Handle overnight shifts
        if end_dt < start_dt:
            end_dt = datetime.combine(today + timedelta(days=1), self.end_time)
        
        duration = end_dt - start_dt
        return duration.total_seconds() / 3600  # Convert to hours
    
    @property
    def shift_color(self):
        """Return color code for UI"""
        colors = {
            'morning': '#3788d8',      # Blue
            'afternoon': '#f59e0b',    # Orange
            'evening': '#8b5cf6',      # Purple
            'night': '#1f2937',        # Dark gray
            'full_day': '#10b981',     # Green
            'off': '#9ca3af',          # Light gray
        }
        return colors.get(self.shift_type, '#6b7280')
    
    @property
    def display_time(self):
        """Return formatted time string"""
        if self.shift_type == 'off':
            return 'OFF'
        if self.start_time and self.end_time:
            return f"{self.start_time.strftime('%I:%M %p')} - {self.end_time.strftime('%I:%M %p')}"
        return 'No time set'


class LeaveRequest(models.Model):
    """Staff leave/holiday requests"""
    
    LEAVE_TYPE_CHOICES = [
        ('annual', 'Annual Leave'),
        ('medical', 'Medical Leave'),
        ('emergency', 'Emergency Leave'),
        ('unpaid', 'Unpaid Leave'),
        ('other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('pending_manager', 'Pending Manager Approval'),
        ('manager_approved', 'Manager Approved - Pending Admin'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ]
    
    # Request details
    staff = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='schedule_leave_requests',
        help_text="Staff requesting leave"
    )
    leave_type = models.CharField(max_length=20, choices=LEAVE_TYPE_CHOICES)
    start_date = models.DateField(help_text="Leave start date")
    end_date = models.DateField(help_text="Leave end date")
    reason = models.TextField(help_text="Reason for leave")
    
    # Medical leave proof (required for medical leave)
    medical_proof = models.FileField(
        upload_to='leave_proofs/%Y/%m/',
        null=True,
        blank=True,
        help_text="Medical certificate (required for medical leave)"
    )
    
    # Approval workflow
    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default='pending_manager'
    )
    manager_approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='leave_requests_manager_approved',
        help_text="Manager who approved"
    )
    manager_approved_at = models.DateTimeField(null=True, blank=True)
    manager_notes = models.TextField(blank=True)
    
    admin_approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='leave_requests_admin_approved',
        help_text="Admin who gave final approval"
    )
    admin_approved_at = models.DateTimeField(null=True, blank=True)
    admin_notes = models.TextField(blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['staff', 'status']),
            models.Index(fields=['start_date', 'end_date']),
            models.Index(fields=['status', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.staff.username} - {self.leave_type} - {self.start_date} to {self.end_date}"
    
    def clean(self):
        """Validate leave request"""
        # End date must be >= start date
        if self.end_date < self.start_date:
            raise ValidationError("End date cannot be before start date.")
        
        # Medical leave requires proof
        if self.leave_type == 'medical' and not self.medical_proof:
            raise ValidationError("Medical certificate is required for medical leave.")
        
        # Check for overlapping leave requests
        overlapping = LeaveRequest.objects.filter(
            staff=self.staff,
            status__in=['pending_manager', 'manager_approved', 'approved'],
            start_date__lte=self.end_date,
            end_date__gte=self.start_date
        ).exclude(pk=self.pk)
        
        if overlapping.exists():
            raise ValidationError(
                "You already have a leave request for overlapping dates."
            )
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
    
    @property
    def total_days(self):
        """Calculate total days of leave"""
        return (self.end_date - self.start_date).days + 1
    
    @property
    def is_pending(self):
        return self.status in ['pending_manager', 'manager_approved']
    
    @property
    def is_approved(self):
        return self.status == 'approved'


class ShiftSwapRequest(models.Model):
    """Staff request to swap shifts with another staff member"""
    
    STATUS_CHOICES = [
        ('pending_counterpart', 'Pending Other Staff Agreement'),
        ('pending_manager', 'Pending Manager Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ]
    
    # Requester details
    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='swap_requests_sent',
        help_text="Staff requesting the swap"
    )
    requester_schedule = models.ForeignKey(
        Schedule,
        on_delete=models.CASCADE,
        related_name='swap_requests_as_requester',
        help_text="Requester's shift to swap"
    )
    
    # Counterpart details
    counterpart = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='swap_requests_received',
        help_text="Staff to swap with"
    )
    counterpart_schedule = models.ForeignKey(
        Schedule,
        on_delete=models.CASCADE,
        related_name='swap_requests_as_counterpart',
        help_text="Counterpart's shift to swap"
    )
    
    # Request details
    reason = models.TextField(help_text="Reason for swap request")
    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default='pending_counterpart'
    )
    
    # Approvals
    counterpart_agreed = models.BooleanField(default=False)
    counterpart_agreed_at = models.DateTimeField(null=True, blank=True)
    
    manager_approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='swap_requests_approved',
        help_text="Manager who approved the swap"
    )
    manager_approved_at = models.DateTimeField(null=True, blank=True)
    manager_notes = models.TextField(blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['requester', 'status']),
            models.Index(fields=['counterpart', 'status']),
            models.Index(fields=['status', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.requester.username} ↔ {self.counterpart.username} - {self.status}"
    
    def clean(self):
        """Validate swap request"""
        # Can't swap with yourself
        if self.requester == self.counterpart:
            raise ValidationError("Cannot swap shift with yourself.")
        
        # Both schedules must be from same branch
        if self.requester_schedule.branch != self.counterpart_schedule.branch:
            raise ValidationError("Can only swap shifts within the same branch.")
        
        # Can't swap OFF days
        if self.requester_schedule.shift_type == 'off' or self.counterpart_schedule.shift_type == 'off':
            raise ValidationError("Cannot swap OFF/Rest days.")
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
    
    def execute_swap(self):
        """Execute the approved swap - swap the staff assignments"""
        if self.status != 'approved':
            raise ValidationError("Can only execute approved swaps.")
        
        # Swap the staff assignments
        req_schedule = self.requester_schedule
        counter_schedule = self.counterpart_schedule
        
        # Temporarily store
        temp_staff = req_schedule.staff
        
        # Swap
        req_schedule.staff = counter_schedule.staff
        counter_schedule.staff = temp_staff
        
        # Save
        req_schedule.save()
        counter_schedule.save()
        
        return True
    
    @property
    def is_pending(self):
        return self.status in ['pending_counterpart', 'pending_manager']