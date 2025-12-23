from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from datetime import date, timedelta
from decimal import Decimal
from calendar import monthrange



class DailyPoints(models.Model):
    """
    Daily points tracking - Target: 50 points per day
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='daily_points')
    date = models.DateField(default=date.today)
    points = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    grooming_count = models.IntegerField(default=0)
    cat_service_count = models.IntegerField(default=0)
    booking_count = models.IntegerField(default=0)
    notes = models.TextField(blank=True)
    
    # Breakdown
    grooming_points = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    service_points = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    booking_points = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    bonus_points = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date']
        unique_together = ['user', 'date']
        verbose_name_plural = "Daily points"
    
    def __str__(self):
        return f"{self.user.username} - {self.date} - {self.points} pts"
    
    @property
    def target_points(self):
        """Daily target is 50 points"""
        return Decimal('50.00')
    
    @property
    def progress_percentage(self):
        """Calculate percentage of target achieved"""
        if self.target_points > 0:
            return min((self.points / self.target_points) * 100, 100)
        return 0
    
    @property
    def status(self):
        """Return status based on points"""
        if self.points >= self.target_points:
            return 'achieved'
        elif self.points >= self.target_points * Decimal('0.7'):
            return 'progress'
        else:
            return 'below_target'
    
    @property
    def points_needed(self):
        """Points needed to reach target"""
        return max(self.target_points - self.points, 0)


class MonthlyIncentive(models.Model):
    """
    Monthly incentive tracking - Target: 1200 points, Warning: 850 points
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='monthly_incentives')
    month = models.DateField()  # First day of month
    total_points = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    incentive_earned = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    bonus_earned = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    milestone_reached = models.IntegerField(null=True, blank=True)
    
    # Warning system
    is_below_warning_threshold = models.BooleanField(default=False)
    warning_issued = models.BooleanField(default=False)
    warning_issued_date = models.DateField(null=True, blank=True)
    
    paid = models.BooleanField(default=False)
    paid_date = models.DateField(null=True, blank=True)
    
    class Meta:
        ordering = ['-month']
        unique_together = ['user', 'month']
        verbose_name_plural = "Monthly incentives"
    
    def __str__(self):
        return f"{self.user.username} - {self.month.strftime('%B %Y')} - {self.total_points} pts"
    
    @property
    def monthly_target(self):
        return Decimal('1200.00')
    
    @property
    def warning_threshold(self):
        return Decimal('850.00')
    
    @property
    def progress_percentage(self):
        return (self.total_points / self.monthly_target) * 100 if self.monthly_target > 0 else 0
    
    def calculate_incentive(self):
        """Calculate incentive based on points"""
        if self.total_points >= 1200:
            self.incentive_earned = Decimal('1000.00')
            self.milestone_reached = 1000
            # Bonus for exceeding
            if self.total_points > 1200:
                excess = self.total_points - 1200
                self.bonus_earned = excess * Decimal('0.50')
        elif self.total_points >= 900:
            self.incentive_earned = Decimal('600.00')
            self.milestone_reached = 600
        elif self.total_points >= 600:
            self.incentive_earned = Decimal('400.00')
            self.milestone_reached = 400
        elif self.total_points >= 300:
            self.incentive_earned = Decimal('200.00')
            self.milestone_reached = 200
        else:
            self.incentive_earned = 0
            self.milestone_reached = None
        
        # Check warning threshold
        if self.total_points < self.warning_threshold:
            self.is_below_warning_threshold = True
        
        self.save()


class PointsProjection(models.Model):
    """
    Points projection with predictions
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='projections')
    date = models.DateField()
    
    # Current data
    current_total = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    daily_average = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # Projections
    projected_monthly_total = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    projected_end_date_total = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    
    # Targets
    days_remaining = models.IntegerField(default=0)
    points_needed_for_target = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    daily_points_required = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # Status
    on_track = models.BooleanField(default=False)
    will_reach_warning = models.BooleanField(default=False)
    will_exceed_target = models.BooleanField(default=False)
    
    # Suggestions
    suggestion = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-date']
    
    def __str__(self):
        return f"{self.user.username} - {self.date} - Projected: {self.projected_monthly_total}"


class WarningLetter(models.Model):
    """
    Track warning letters issued to staff
    """
    REASON_CHOICES = [
        ('low_performance', 'Low Performance (Below 850 points)'),
        ('absence', 'Unauthorized Absence'),
        ('conduct', 'Misconduct'),
        ('quality', 'Quality Issues'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='warning_letters')
    month = models.DateField()
    reason = models.CharField(max_length=50, choices=REASON_CHOICES)
    points_achieved = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    description = models.TextField()
    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='issued_warnings'
    )
    issued_date = models.DateField(auto_now_add=True)
    acknowledged = models.BooleanField(default=False)
    acknowledged_date = models.DateField(null=True, blank=True)
    
    class Meta:
        ordering = ['-issued_date']
    
    def __str__(self):
        return f"Warning: {self.user.username} - {self.get_reason_display()} - {self.month.strftime('%B %Y')}"