# task_management/models.py

from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import date
from decimal import Decimal
import uuid
import random
from django.db import models
from django.conf import settings
import json
from django.db import transaction
# ============================================
# CUSTOMER & CAT MODELS
# ============================================

class Customer(models.Model):
    """Customer information for cat owners"""
    customer_id = models.CharField(max_length=20, unique=True, blank=True)
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15, unique=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    ic_number = models.CharField(max_length=20, blank=True, unique=True)
    emergency_contact = models.CharField(max_length=15, blank=True)
    registered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='registered_customers'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return f"{self.customer_id} - {self.name}"
    
    def save(self, *args, **kwargs):
        if not self.customer_id:
            last = Customer.objects.all().order_by('id').last()
            if last and last.customer_id:
                self.customer_id = f"CUST{int(last.customer_id[4:]) + 1:04d}"
            else:
                self.customer_id = "CUST0001"
        super().save(*args, **kwargs)


class Cat(models.Model):
    """Cat registration and information"""
    
    CAT_BREED_CHOICES = [
        ('persian', 'Persian'),
        ('siamese', 'Siamese'),
        ('maine_coon', 'Maine Coon'),
        ('british_shorthair', 'British Shorthair'),
        ('ragdoll', 'Ragdoll'),
        ('bengal', 'Bengal'),
        ('mixed', 'Mixed Breed'),
        ('other', 'Other'),
    ]
    
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
    ]
    
    VACCINATION_STATUS_CHOICES = [
        ('unknown', 'Unknown'),
        ('up_to_date', 'Up to Date'),
        ('overdue', 'Overdue'),
        ('not_vaccinated', 'Not Vaccinated'),
    ]
    
    # FIXED: Changed max_length to 12 for new format
    cat_id = models.CharField(
        max_length=12,  # Changed from 20 to 12
        unique=True,
        blank=True,
        editable=False,
        help_text="Format: CAT133001239 (CAT + 3random + 3count + 3random)"
    )
    
    name = models.CharField(max_length=100)
    owner = models.ForeignKey(
        'Customer',  # Changed to string reference if Customer is in same file
        on_delete=models.CASCADE,
        related_name='cats'
    )
    breed = models.CharField(
        max_length=50,
        choices=CAT_BREED_CHOICES,
        default='mixed'
    )
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    age = models.IntegerField(help_text="Age in years")
    weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Weight in kg"
    )
    color = models.CharField(max_length=50, blank=True)
    medical_notes = models.TextField(
        blank=True,
        help_text="Allergies, medications, etc."
    )
    special_requirements = models.TextField(blank=True)
    vaccination_status = models.CharField(
        max_length=20,
        choices=VACCINATION_STATUS_CHOICES,
        default='unknown'
    )
    is_active = models.BooleanField(default=True)
    registration_date = models.DateField(auto_now_add=True)
    registered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='registered_cats'
    )
    photo = models.ImageField(
        upload_to='cat_photos/%Y/%m/',  # Organized by year/month
        blank=True,
        null=True
    )
    
    class Meta:
        ordering = ['-registration_date']
        indexes = [
            models.Index(fields=['cat_id']),
            models.Index(fields=['owner', 'name']),
        ]
    
    def __str__(self):
        return f"{self.cat_id} - {self.name} ({self.owner.name})"
    
    def generate_cat_id(self):
        """
        Generate Cat ID in format: CAT133001239
        
        Format:
        - CAT = Prefix (3 chars)
        - 133 = Random (3 digits: 100-999)
        - 001 = Sequential count (3 digits with leading zeros)
        - 239 = Random (3 digits: 100-999)
        
        Total: 12 characters
        Example: CAT133001239
        """
        from django.db.models import Max
        
        # Get sequential count based on database ID
        last_cat = Cat.objects.aggregate(Max('id'))
        count = (last_cat['id__max'] or 0) + 1
        
        # Format count with 3 digits (leading zeros)
        count_str = str(count).zfill(3)
        
        # Generate random parts (3 digits each: 100-999)
        random_part1 = str(random.randint(100, 999))
        random_part2 = str(random.randint(100, 999))
        
        # Combine: CAT + random1 + count + random2
        cat_id = f"CAT{random_part1}{count_str}{random_part2}"
        
        # Ensure uniqueness (retry if duplicate - very rare)
        max_attempts = 10
        attempts = 0
        
        while Cat.objects.filter(cat_id=cat_id).exists() and attempts < max_attempts:
            random_part1 = str(random.randint(100, 999))
            random_part2 = str(random.randint(100, 999))
            cat_id = f"CAT{random_part1}{count_str}{random_part2}"
            attempts += 1
        
        return cat_id
    
    def save(self, *args, **kwargs):
        """Override save to auto-generate cat_id"""
        if not self.cat_id:
            self.cat_id = self.generate_cat_id()
        super().save(*args, **kwargs)


# ============================================
# SERVICE REQUEST
# ============================================

class ServiceRequest(models.Model):
    """Service request created by front desk staff"""
    STATUS_CHOICES = [
        ('pending', 'Pending Assignment'),
        ('assigned', 'Assigned to Manager'),
        ('converted', 'Converted to Task Package'),
        ('cancelled', 'Cancelled'),
    ]
    
    request_id = models.CharField(max_length=20, unique=True, blank=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='service_requests')
    cat = models.ForeignKey(Cat, on_delete=models.CASCADE, related_name='service_requests')
    
    services_wanted = models.TextField(help_text="List of services customer wants")
    preferred_date = models.DateField(null=True, blank=True)
    preferred_time = models.TimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_service_requests'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    converted_to_package = models.OneToOneField(
        'TaskPackage',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='source_request'
    )
    converted_at = models.DateTimeField(null=True, blank=True)
    converted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='converted_service_requests'
    )
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.request_id} - {self.cat.name} ({self.customer.name})"
    
    def save(self, *args, **kwargs):
        if not self.request_id:
            today = date.today()
            date_str = today.strftime('%y%m%d')
            today_count = ServiceRequest.objects.filter(
                created_at__date=today
            ).count()
            seq_num = str(today_count + 1).zfill(4)
            self.request_id = f"SR-{date_str}-{seq_num}"
        super().save(*args, **kwargs)


# ============================================
# TASK GROUPS AND TYPES
# ============================================

class TaskGroup(models.Model):
    """Task groups like Grooming, House Keeping, etc."""
    group_id = models.CharField(max_length=20, unique=True, blank=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['order', 'name']
    
    def __str__(self):
        return f"{self.group_id} - {self.name}"
    
    def save(self, *args, **kwargs):
        if not self.group_id:
            last = TaskGroup.objects.all().order_by('id').last()
            if last and last.group_id:
                self.group_id = f"GRP{int(last.group_id[3:]) + 1:03d}"
            else:
                self.group_id = "GRP001"
        super().save(*args, **kwargs)


class TaskType(models.Model):
    """Enhanced task types with full rule engine support"""
    task_type_id = models.CharField(max_length=20, unique=True, blank=True)
    group = models.ForeignKey('TaskGroup', on_delete=models.PROTECT, related_name='task_types')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    
    points = models.IntegerField(default=0, help_text="Base points for this task")
    price = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True, help_text="Price if applicable")
    
    rule_type = models.CharField(max_length=50, blank=True, help_text="Type of rule to apply")
    price_min = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    price_max = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    count_min = models.IntegerField(null=True, blank=True)
    count_max = models.IntegerField(null=True, blank=True)
    view_min = models.IntegerField(null=True, blank=True)
    view_max = models.IntegerField(null=True, blank=True)
    time_limit_hours = models.IntegerField(null=True, blank=True)
    time_limit_days = models.IntegerField(null=True, blank=True)
    max_per_day = models.IntegerField(null=True, blank=True)
    max_per_month = models.IntegerField(null=True, blank=True)
    requires_evidence = models.BooleanField(default=False)
    requires_approval = models.BooleanField(default=False)
    auto_complete = models.BooleanField(default=True)
    rule_config = models.JSONField(null=True, blank=True)
    category = models.CharField(max_length=50, blank=True)
    
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['group', 'order', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.points} pts)"
    
    def save(self, *args, **kwargs):
        if not self.task_type_id:
            last = TaskType.objects.all().order_by('id').last()
            if last and last.task_type_id:
                num = int(last.task_type_id.replace('TT', ''))
                self.task_type_id = f"TT{num + 1:03d}"
            else:
                self.task_type_id = "TT001"
        super().save(*args, **kwargs)


# ============================================
# TASK PACKAGES AND TASKS
# ============================================
class TaskPackage(models.Model):
    """Task package contains multiple tasks for one cat - ENHANCED with Next Booking System"""
    STATUS_CHOICES = [
        ('pending', 'Pending Assignment'),
        ('assigned', 'Assigned'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    BOOKING_TYPE_CHOICES = [
        ('type_a', 'Type A - Got Proof (Award Now)'),
        ('type_c', 'Type C - No Proof (Hold Points)'),
        ('type_b', 'Type B - Combo Package (No Points)'),
    ]
    
    ARRIVAL_STATUS_CHOICES = [
        ('pending', 'Pending Arrival'),
        ('arrived', 'Customer Arrived'),
        ('no_show', 'Customer No-Show'),
    ]
    
    # ============ EXISTING FIELDS ============
    package_id = models.CharField(max_length=20, unique=True, blank=True)
    cat = models.ForeignKey(Cat, on_delete=models.CASCADE, related_name='task_packages')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_packages'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    branch = models.CharField(
        max_length=50,
        choices=[
            ('hq', 'HQ'),
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
        ],
        default='seri_kembangan',
        help_text='Branch where this package will be serviced'
    )
    
    total_points = models.IntegerField(default=0)
    notes = models.TextField(blank=True)
    
    email_sent = models.BooleanField(default=False)
    email_sent_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # ============ NEXT BOOKING SYSTEM FIELDS ============
    
    # Booking Type Selection
    booking_type = models.CharField(
        max_length=20,
        choices=BOOKING_TYPE_CHOICES,
        default='type_c',
        help_text='Type of booking determines point awarding logic'
    )
    
    # Type A: Payment Proof
    payment_proof = models.ImageField(
        upload_to='payment_proofs/%Y/%m/',
        blank=True,
        null=True,
        help_text='Upload screenshot of payment/deposit/booking confirmation'
    )
    
    # Type B: Combo Package Flag
    is_combo_package = models.BooleanField(
        default=False,
        help_text='Mark if this is a combo package session (no additional points)'
    )
    combo_session_number = models.IntegerField(
        null=True,
        blank=True,
        help_text='Which session of the combo? (e.g., 2 of 4)'
    )
    combo_total_sessions = models.IntegerField(
        null=True,
        blank=True,
        help_text='Total sessions in combo (e.g., 4)'
    )
    
    # Type C: Arrival Tracking
    scheduled_date = models.DateField(
        null=True,
        blank=True,
        help_text='When customer is scheduled to arrive for service'
    )
    
    arrival_status = models.CharField(
        max_length=20,
        choices=ARRIVAL_STATUS_CHOICES,
        default='pending',
        help_text='Customer arrival confirmation status'
    )
    
    arrival_confirmed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When manager confirmed customer arrival'
    )
    
    confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='confirmed_arrivals',
        help_text='Manager who confirmed the arrival'
    )
    
    # Points Tracking
    points_awarded = models.BooleanField(
        default=False,
        help_text='Have points been awarded to staff?'
    )
    
    points_awarded_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When points were awarded to staff'
    )
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['booking_type', 'arrival_status', 'scheduled_date']),
            models.Index(fields=['scheduled_date', 'arrival_status']),
            models.Index(fields=['points_awarded', 'booking_type']),
        ]
    
    def __str__(self):
        return f"{self.package_id} - {self.cat.name}"
    
    def save(self, *args, **kwargs):
        if not self.package_id:
            today = date.today()
            date_str = today.strftime('%y%m%d')
            today_count = TaskPackage.objects.filter(created_at__date=today).count()
            seq_num = str(today_count + 1).zfill(4)
            self.package_id = f"PKG-{date_str}-{seq_num}"
        
        # Auto-set scheduled_date from first task if not set
        if not self.scheduled_date and self.pk:
            first_task = self.tasks.first()
            if first_task and first_task.scheduled_date:
                self.scheduled_date = first_task.scheduled_date
        
        super().save(*args, **kwargs)
    
    # ============ NEXT BOOKING METHODS ============
    
    def award_points_immediately(self):
        """
        Type A: Award points immediately when booking created
        Called when payment proof is uploaded
        """
        if self.booking_type != 'type_a':
            return False
        
        if self.points_awarded:
            return False  # Already awarded
        
        # Award points to staff
        from performance.models import DailyPoints, MonthlyIncentive
        from decimal import Decimal
        
        try:
            # Create/update daily points
            daily_points, created = DailyPoints.objects.get_or_create(
                user=self.created_by,
                date=self.created_at.date(),
                defaults={
                    'points': Decimal('0.00'),
                    'booking_points': Decimal('0.00'),
                }
            )
            
            daily_points.booking_points += Decimal(str(self.total_points))
            daily_points.points = (
                daily_points.grooming_points +
                daily_points.service_points +
                daily_points.booking_points +
                daily_points.bonus_points
            )
            daily_points.save()
            
            # Update monthly incentive
            first_day = self.created_at.date().replace(day=1)
            monthly, created = MonthlyIncentive.objects.get_or_create(
                user=self.created_by,
                month=first_day,
                defaults={'total_points': Decimal('0.00')}
            )
            monthly.total_points += Decimal(str(self.total_points))
            if hasattr(monthly, 'calculate_incentive'):
                monthly.calculate_incentive()
            monthly.save()
            
            # Mark as awarded
            self.points_awarded = True
            self.points_awarded_at = timezone.now()
            self.save()
            
            return True
            
        except Exception as e:
            print(f"Error awarding points: {e}")
            return False
    
    def confirm_arrival(self, manager_user):
        """
        Type C: Confirm customer arrived and release held points
        """
        if self.arrival_status == 'arrived':
            return False  # Already confirmed
        
        # Update arrival status
        self.arrival_status = 'arrived'
        self.arrival_confirmed_at = timezone.now()
        self.confirmed_by = manager_user
        self.save()
        
        # Release points if Type C
        if self.booking_type == 'type_c' and not self.points_awarded:
            return self.release_held_points()
        
        return True
    
    def mark_no_show(self, manager_user):
        """
        Mark customer as no-show (points NOT awarded)
        """
        self.arrival_status = 'no_show'
        self.arrival_confirmed_at = timezone.now()
        self.confirmed_by = manager_user
        self.save()
        
        return True
    
    def release_held_points(self):
        """
        Release held points to staff (for Type C arrivals)
        """
        if self.points_awarded:
            return False  # Already awarded
        
        if self.booking_type == 'type_b':
            return False  # Combo packages don't get points
        
        # Award points to staff
        from performance.models import DailyPoints, MonthlyIncentive
        from decimal import Decimal
        
        try:
            # Award points on the scheduled date (when service happens)
            award_date = self.scheduled_date or self.created_at.date()
            
            daily_points, created = DailyPoints.objects.get_or_create(
                user=self.created_by,
                date=award_date,
                defaults={
                    'points': Decimal('0.00'),
                    'booking_points': Decimal('0.00'),
                }
            )
            
            daily_points.booking_points += Decimal(str(self.total_points))
            daily_points.points = (
                daily_points.grooming_points +
                daily_points.service_points +
                daily_points.booking_points +
                daily_points.bonus_points
            )
            daily_points.save()
            
            # Update monthly
            first_day = award_date.replace(day=1)
            monthly, created = MonthlyIncentive.objects.get_or_create(
                user=self.created_by,
                month=first_day,
                defaults={'total_points': Decimal('0.00')}
            )
            monthly.total_points += Decimal(str(self.total_points))
            if hasattr(monthly, 'calculate_incentive'):
                monthly.calculate_incentive()
            monthly.save()
            
            # Mark as awarded
            self.points_awarded = True
            self.points_awarded_at = timezone.now()
            self.save()
            
            # Create notification
            from task_management.models import Notification
            Notification.objects.create(
                user=self.created_by,
                notification_type='points_awarded',
                title='Points Released!',
                message=f'{self.total_points} points released for {self.package_id} - Customer arrived',
                link=f'/registration/dashboard/'
            )
            
            return True
            
        except Exception as e:
            print(f"Error releasing points: {e}")
            return False
    
    def get_booking_type_display_with_icon(self):
        """Get display text with icon for booking type"""
        icons = {
            'type_a': '✅',
            'type_b': '❌',
            'type_c': '⏸️',
        }
        icon = icons.get(self.booking_type, '')
        return f"{icon} {self.get_booking_type_display()}"
    
    def get_arrival_status_badge_class(self):
        """Get Bootstrap badge class for arrival status"""
        classes = {
            'pending': 'warning',
            'arrived': 'success',
            'no_show': 'danger',
        }
        return classes.get(self.arrival_status, 'secondary')
    
    # ============ EXISTING METHODS ============
    
    def calculate_total_points(self):
        """Calculate total points from all tasks"""
        self.total_points = sum(task.points for task in self.tasks.all())
        self.save()
    
    def update_status(self):
        """Update package status based on task statuses"""
        tasks = self.tasks.all()
        if not tasks:
            return
        
        if all(task.status == 'completed' for task in tasks):
            self.status = 'completed'
        elif any(task.status == 'in_progress' for task in tasks):
            self.status = 'in_progress'
        elif any(task.status == 'assigned' for task in tasks):
            self.status = 'assigned'
        else:
            self.status = 'pending'
        
        self.save()
class ComboPackageOwnership(models.Model):
    """Track customer's owned combo packages and session usage"""
    
    ownership_id = models.CharField(max_length=20, unique=True, blank=True)
    
    # Link to customer and cat
    customer = models.ForeignKey(
        'Customer',
        on_delete=models.CASCADE,
        related_name='owned_combo_packages'
    )
    cat = models.ForeignKey(
        'Cat',
        on_delete=models.CASCADE,
        related_name='combo_packages',
        help_text='Which cat this combo package is for'
    )
    
    # Which combo package
    combo_task_type = models.ForeignKey(
        'TaskType',
        on_delete=models.PROTECT,
        related_name='combo_ownerships',
        help_text='The Combo Front task type (e.g., Cute Combo 4)'
    )
    
    # Session tracking
    total_sessions = models.IntegerField(
        help_text='Total sessions in this combo (e.g., 4 for Cute Combo 4)'
    )
    sessions_used = models.IntegerField(
        default=0,
        help_text='How many sessions have been used'
    )
    sessions_remaining = models.IntegerField(
        help_text='How many sessions are left'
    )
    
    # Points tracking (for front desk who sold it)
    points_awarded = models.IntegerField(
        default=0,
        help_text='Points awarded to staff who sold this combo'
    )
    awarded_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='combo_sales',
        help_text='Staff who sold this combo package'
    )
    awarded_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When points were awarded'
    )
    
    # The original sale booking
    purchase_package = models.OneToOneField(
        'TaskPackage',
        on_delete=models.CASCADE,
        related_name='combo_ownership',
        help_text='The TaskPackage created when combo was sold'
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    is_fully_used = models.BooleanField(default=False)
    
    # Dates
    purchased_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateField(
        null=True,
        blank=True,
        help_text='Expiry date (if applicable)'
    )
    
    class Meta:
        ordering = ['-purchased_at']
        indexes = [
            models.Index(fields=['customer', 'is_active']),
            models.Index(fields=['cat', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.ownership_id} - {self.combo_task_type.name} ({self.sessions_remaining}/{self.total_sessions})"
    
    def save(self, *args, **kwargs):
        if not self.ownership_id:
            today = date.today()
            count = ComboPackageOwnership.objects.filter(
                purchased_at__date=today
            ).count() + 1
            self.ownership_id = f"COMBO-{today.strftime('%y%m%d')}-{count:04d}"
        
        # Auto-calculate remaining sessions
        self.sessions_remaining = self.total_sessions - self.sessions_used
        
        # Mark as fully used if no sessions left
        if self.sessions_remaining <= 0:
            self.is_fully_used = True
            self.is_active = False
        
        super().save(*args, **kwargs)
    
    def use_session(self):
        """Use one session from this combo package"""
        if self.sessions_remaining > 0:
            self.sessions_used += 1
            self.save()
            return True
        return False
    
    def get_progress_percentage(self):
        """Get usage progress as percentage"""
        if self.total_sessions == 0:
            return 0
        return int((self.sessions_used / self.total_sessions) * 100)


class Task(models.Model):
    """Individual task assigned to staff"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('assigned', 'Assigned'),
        ('in_progress', 'In Progress'),
        ('submitted', 'Submitted for Approval'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    task_id = models.CharField(max_length=20, unique=True, blank=True)
    package = models.ForeignKey(TaskPackage, on_delete=models.CASCADE, related_name='tasks')
    task_type = models.ForeignKey(TaskType, on_delete=models.PROTECT, related_name='tasks')
    points = models.IntegerField(default=0)
    
    scheduled_date = models.DateField()
    scheduled_time = models.TimeField(default='09:00')
    
    assigned_staff = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tm_assigned_tasks'
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tm_tasks_i_assigned'
    )
    assigned_date = models.DateTimeField(null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    notes = models.TextField(blank=True)
    
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tm_tasks_i_approved'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['scheduled_date', 'scheduled_time']
    
    def __str__(self):
        return f"{self.task_id} - {self.task_type.name}"
    
    def save(self, *args, **kwargs):
        if not self.task_id:
            today = date.today()
            date_str = today.strftime('%y%m%d')
            today_count = Task.objects.filter(created_at__date=today).count()
            seq_num = str(today_count + 1).zfill(4)
            self.task_id = f"TSK-{date_str}-{seq_num}"
        
        if not self.points and self.task_type:
            self.points = self.task_type.points
        
        super().save(*args, **kwargs)


# ============================================
# TASK COMPLETION
# ============================================

class TaskCompletion(models.Model):
    """Record of task completion with automatic point awarding"""
    task = models.OneToOneField(Task, on_delete=models.CASCADE, related_name='completion')
    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='completed_tasks_tm'
    )
    completed_at = models.DateTimeField(auto_now_add=True)
    completion_notes = models.TextField(blank=True)
    photo_proof = models.TextField(blank=True, help_text="Comma-separated image paths")
    
    points_awarded = models.IntegerField(default=0)
    points_awarded_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"Completion: {self.task.task_id}"
    
    def get_proof_images_list(self):
        """Get list of proof image paths"""
        if self.photo_proof:
            return [f.strip() for f in self.photo_proof.split(',') if f.strip()]
        return []
    
    def award_points(self):
        """Award points to staff member"""
        if self.points_awarded > 0:
            return
        
        self.points_awarded = self.task.points
        self.points_awarded_at = timezone.now()
        self.save()
        
        try:
            from performance.models import DailyPoints, MonthlyIncentive
            daily_points, created = DailyPoints.objects.get_or_create(
                user=self.completed_by,
                date=self.completed_at.date(),
                defaults={
                    'points': Decimal('0.00'),
                    'service_points': Decimal('0.00'),
                }
            )
            daily_points.service_points += Decimal(str(self.points_awarded))
            daily_points.points += Decimal(str(self.points_awarded))
            daily_points.save()
            
            first_day = self.completed_at.date().replace(day=1)
            monthly, created = MonthlyIncentive.objects.get_or_create(
                user=self.completed_by,
                month=first_day,
                defaults={'total_points': Decimal('0.00')}
            )
            monthly.total_points += Decimal(str(self.points_awarded))
            if hasattr(monthly, 'calculate_incentive'):
                monthly.calculate_incentive()
            monthly.save()
        except ImportError:
            pass


# ============================================
# POINT REQUEST
# ============================================

class PointRequest(models.Model):
    """Staff requests for points on tasks not in regular workflow"""
    
    APPROVAL_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    REASON_CHOICES = [
        ('not_in_system', 'Task Not in System'),
        ('emergency', 'Emergency Task'),
        ('special_request', 'Special Customer Request'),
        ('additional_work', 'Additional Work Required'),
        ('other', 'Other'),
    ]
    
    request_id = models.CharField(max_length=50, unique=True, editable=False)
    
    staff = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='point_requests'
    )
    
    task_type = models.ForeignKey(
        'TaskType',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Select task type from list, or describe in reason_details"
    )
    points_requested = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        help_text="Points requested for this task"
    )
    
    date_completed = models.DateField(
        help_text="Date when the task was actually completed"
    )
    
    reason = models.CharField(
        max_length=50,
        choices=REASON_CHOICES,
        default='not_in_system'
    )
    reason_details = models.TextField(
        blank=True,
        help_text="Explain why this task deserves points"
    )
    
    proof_photo = models.ImageField(
        upload_to='point_requests/%Y/%m/%d/',
        blank=True,
        null=True,
        help_text="Photo proof of completed task"
    )
    
    approval_status = models.CharField(
        max_length=20,
        choices=APPROVAL_STATUS_CHOICES,
        default='pending'
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_point_requests'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    manager_notes = models.TextField(
        blank=True,
        help_text="Manager's notes on approval/rejection"
    )
    
    points_awarded = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0,
        help_text="Actual points awarded (may differ from requested)"
    )
    points_awarded_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['staff', 'approval_status']),
            models.Index(fields=['approval_status', '-created_at']),
            models.Index(fields=['date_completed']),
        ]
    
    def save(self, *args, **kwargs):
        if not self.request_id:
            today = date.today()
            count = PointRequest.objects.filter(
                created_at__date=today
            ).count() + 1
            self.request_id = f"PR-{today.strftime('%y%m%d')}-{count:04d}"
        super().save(*args, **kwargs)
    
    def __str__(self):
        task_name = self.task_type.name if self.task_type else "Custom Task"
        return f"{self.request_id} - {task_name} by {self.staff.username}"
    
    def approve(self, admin_user, notes='', awarded_points=None):
        """Approve request and award points on the date_completed"""
        from performance.models import DailyPoints, MonthlyIncentive
        
        self.approval_status = 'approved'
        self.approved_by = admin_user
        self.approved_at = timezone.now()
        self.manager_notes = notes
        
        if awarded_points:
            self.points_awarded = Decimal(str(awarded_points))
        else:
            self.points_awarded = self.points_requested
        
        self.points_awarded_at = timezone.now()
        self.save()
        
        daily_points, created = DailyPoints.objects.get_or_create(
            user=self.staff,
            date=self.date_completed,
            defaults={
                'points': Decimal('0.00'),
                'grooming_points': Decimal('0.00'),
                'service_points': Decimal('0.00'),
                'booking_points': Decimal('0.00'),
                'bonus_points': Decimal('0.00'),
            }
        )
        
        daily_points.bonus_points += self.points_awarded
        daily_points.points = (
            daily_points.grooming_points +
            daily_points.service_points +
            daily_points.booking_points +
            daily_points.bonus_points
        )
        daily_points.save()
        
        first_day = self.date_completed.replace(day=1)
        monthly, created = MonthlyIncentive.objects.get_or_create(
            user=self.staff,
            month=first_day,
            defaults={'total_points': Decimal('0.00')}
        )
        monthly.total_points += self.points_awarded
        if hasattr(monthly, 'calculate_incentive'):
            monthly.calculate_incentive()
        monthly.save()
    
    def reject(self, admin_user, notes=''):
        """Reject request"""
        self.approval_status = 'rejected'
        self.approved_by = admin_user
        self.approved_at = timezone.now()
        self.manager_notes = notes
        self.save()


# ============================================
# NOTIFICATION
# ============================================

class Notification(models.Model):
    """System notifications for users"""
    
    NOTIFICATION_TYPES = [
        ('task_assigned', 'Task Assigned'),
        ('task_completed', 'Task Completed'),
        ('point_request', 'Point Request'),
        ('package_created', 'Package Created'),
        ('approval_needed', 'Approval Needed'),
        ('points_awarded', 'Points Awarded'),
        ('general', 'General'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    
    notification_type = models.CharField(
        max_length=50,
        choices=NOTIFICATION_TYPES,
        default='general'
    )
    
    title = models.CharField(max_length=200)
    message = models.TextField()
    link = models.CharField(
        max_length=500,
        blank=True,
        help_text="URL to navigate to when clicked"
    )
    
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.user.username}"
    
    def mark_as_read(self):
        """Mark notification as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save()


# ============================================
# TASK IMAGES
# ============================================

class TaskImage(models.Model):
    """Store multiple images for task completion proof"""
    image_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    task = models.ForeignKey('Task', on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='task_proofs/%Y/%m/%d/')
    caption = models.CharField(max_length=255, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return f"Image for {self.task.task_id}"


# ============================================
# CLOSING REPORT MODEL (DEFINED ONCE HERE!)
# ============================================

class ClosingReport(models.Model):
    """Daily closing report submitted by managers"""
    
    # Auto-generated ID
    report_id = models.CharField(max_length=50, unique=True, editable=False)
    
    # Basic Info
    date = models.DateField(help_text="Date of this closing report")
    branch = models.CharField(
        max_length=50,
        help_text="Branch this report is for"
    )
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='submitted_closing_reports',
        help_text="Manager who submitted this report"
    )
    
    # Count Fields
    grooming_count = models.IntegerField(default=0, help_text="a. Numbers of cat grooming today")
    boarding_count = models.IntegerField(default=0, help_text="b. Numbers of boarded room today")
    total_customers = models.IntegerField(default=0, help_text="c. Numbers of customers today")
    
    # Payment Fields
    payment_record_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0.00'),
        help_text="d. Total payment record (RM)"
    )
    payment_receipt_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0.00'),
        help_text="e. Total payment receipt (RM)"
    )
    
    # Photo Proof (REQUIRED)
    payment_proof_photo = models.ImageField(
        upload_to='closing_reports/%Y/%m/%d/',
        help_text="Photo or screenshot of payment record"
    )
    
    # Compliance Checks
    compliance_all_paid_through_system = models.BooleanField(
        default=True,
        help_text="f.i Do all customers are registered and paid through system?"
    )
    compliance_free_services_today = models.BooleanField(
        default=False,
        help_text="f.ii Is there any service with no payment today?"
    )
    
    # Notes
    notes = models.TextField(blank=True, null=True, help_text="Additional notes")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(default=timezone.now)
    
    # Calculated fields
    revenue_total = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0.00'),
        help_text="Average of payment record and receipt"
    )
    
    class Meta:
        ordering = ['-date', '-submitted_at']
        unique_together = ['date', 'branch']
        verbose_name = 'Closing Report'
        verbose_name_plural = 'Closing Reports'
        indexes = [
            models.Index(fields=['date', 'branch']),
            models.Index(fields=['branch', '-date']),
        ]
    
    def __str__(self):
        return f"{self.report_id} - {self.branch} - {self.date}"
    
    def save(self, *args, **kwargs):
        if not self.report_id:
            self.report_id = self.generate_report_id()
        self.revenue_total = (self.payment_record_amount + self.payment_receipt_amount) / 2
        super().save(*args, **kwargs)
    
    def generate_report_id(self):
        """Generate unique report ID: CR-YYMMDD-XXXX"""
        today = date.today()
        prefix = f"CR-{today.strftime('%y%m%d')}"
        last_report = ClosingReport.objects.filter(
            report_id__startswith=prefix
        ).order_by('report_id').last()
        
        if last_report:
            last_sequence = int(last_report.report_id.split('-')[-1])
            new_sequence = last_sequence + 1
        else:
            new_sequence = 1
        
        return f"{prefix}-{new_sequence:04d}"
    
    @property
    def payment_difference(self):
        """Calculate difference between record and receipt"""
        return abs(self.payment_record_amount - self.payment_receipt_amount)
    
    @property
    def is_balanced(self):
        """Check if payment record matches receipt"""
        return self.payment_difference <= Decimal('1.00')
    
    @property
    def average_transaction_value(self):
        """Calculate average transaction value"""
        if self.total_customers > 0:
            return self.revenue_total / self.total_customers
        return Decimal('0.00')
    
    @property
    def status_color(self):
        """Return color based on compliance"""
        if not self.compliance_all_paid_through_system:
            return 'danger'
        elif not self.is_balanced:
            return 'warning'
        else:
            return 'success'


class AuditLog(models.Model):
    """Track all admin actions for accountability"""
    
    ACTION_CHOICES = [
        ('create', 'Created'),
        ('update', 'Updated'),
        ('delete', 'Deleted'),
        ('activate', 'Activated'),
        ('deactivate', 'Deactivated'),
        ('password_reset', 'Password Reset'),
        ('task_reassign', 'Tasks Reassigned'),
    ]
    
    MODEL_CHOICES = [
        ('tasktype', 'Task Type'),
        ('taskgroup', 'Task Group'),
        ('user', 'User/Staff'),
        ('task', 'Task'),
    ]
    
    # Who did it
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='audit_logs',
        help_text="Admin who performed the action"
    )
    
    # What was done
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    model_type = models.CharField(max_length=20, choices=MODEL_CHOICES)
    object_id = models.CharField(max_length=100, help_text="ID of affected object")
    object_repr = models.CharField(max_length=200, help_text="String representation")
    
    # Details
    changes = models.JSONField(
        null=True,
        blank=True,
        help_text="JSON of what changed (before/after)"
    )
    notes = models.TextField(blank=True, help_text="Additional notes")
    
    # When
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['model_type', 'object_id']),
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.user.username if self.user else 'System'} {self.action} {self.model_type} at {self.timestamp}"


# Helper function to log actions
def log_admin_action(user, action, model_type, object_id, object_repr, changes=None, notes='', request=None):
    """Helper to create audit log entries"""
    ip_address = None
    if request:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(',')[0]
        else:
            ip_address = request.META.get('REMOTE_ADDR')
    
    AuditLog.objects.create(
        user=user,
        action=action,
        model_type=model_type,
        object_id=str(object_id),
        object_repr=object_repr,
        changes=changes,
        notes=notes,
        ip_address=ip_address
    )

class PendingBooking(models.Model):
    """
    Temporary booking created when customer books WITHOUT payment proof.
    Converts to TaskPackage when customer arrives and pays.
    Auto-expires if scheduled_date passes without payment.
    """
    
    BOOKING_STATUS = [
        ('pending_payment', 'Pending Payment'),
        ('confirmed', 'Confirmed & Converted'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
    ]
    
    # Booking ID
    booking_id = models.CharField(max_length=20, unique=True, blank=True)
    
    # Customer & Cat
    customer = models.ForeignKey(
        'Customer',
        on_delete=models.CASCADE,
        related_name='pending_bookings'
    )
    cat = models.ForeignKey(
        'Cat',
        on_delete=models.CASCADE,
        related_name='pending_bookings'
    )
    
    # Selected Services (stored as JSON)
    selected_tasks_json = models.TextField(
        help_text='JSON array of task IDs'
    )
    total_points = models.IntegerField(default=0)
    
    # Schedule
    scheduled_date = models.DateField(
        help_text='The appointment date - booking expires day after if no payment'
    )
    scheduled_time = models.TimeField(default='09:00')
    
    # Notes
    notes = models.TextField(blank=True)
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=BOOKING_STATUS,
        default='pending_payment'
    )
    
    # Created by (Staff who made the booking)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_pending_bookings'
    )
    branch = models.CharField(max_length=50, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Confirmation (when customer arrives)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='confirmed_pending_bookings'
    )
    payment_proof = models.ImageField(
        upload_to='pending_booking_proofs/%Y/%m/',
        null=True,
        blank=True,
        help_text='Payment proof uploaded when customer arrives'
    )
    
    # Expiry
    expired_at = models.DateTimeField(null=True, blank=True)
    
    # Converted TaskPackage (when confirmed)
    converted_to_package = models.OneToOneField(
        'TaskPackage',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='source_pending_booking'
    )
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'scheduled_date']),
            models.Index(fields=['customer', 'status']),
            models.Index(fields=['created_by', 'status']),
        ]
    
    def __str__(self):
        return f"{self.booking_id} - {self.customer.name} ({self.get_status_display()})"
    
    def save(self, *args, **kwargs):
        # Generate booking ID
        if not self.booking_id:
            today = date.today()
            count = PendingBooking.objects.filter(
                created_at__date=today
            ).count() + 1
            self.booking_id = f"PB-{today.strftime('%y%m%d')}-{count:04d}"
        
        # Set branch from user
        if self.created_by and not self.branch:
            self.branch = self.created_by.branch
        
        super().save(*args, **kwargs)
    
    def get_selected_tasks(self):
        """Parse JSON to get list of TaskType objects"""
        try:
            task_ids = json.loads(self.selected_tasks_json)
            return TaskType.objects.filter(id__in=task_ids)
        except:
            return TaskType.objects.none()
    
    def set_selected_tasks(self, task_types):
        """Store TaskType IDs as JSON"""
        task_ids = [task.id for task in task_types]
        self.selected_tasks_json = json.dumps(task_ids)
        
        # Calculate total points
        self.total_points = sum(task.points for task in task_types)
    
    def is_expired(self):
        """Check if booking should be expired (date passed without payment)"""
        if self.status == 'pending_payment':
            today = timezone.now().date()
            return today > self.scheduled_date
        return False
    
    def can_be_confirmed(self):
        """Check if booking can still be confirmed"""
        return self.status == 'pending_payment' and not self.is_expired()
    
    def confirm_and_convert(self, confirmed_by_user, payment_proof_file):
        if not self.can_be_confirmed():
            return False, None, "Booking cannot be confirmed (expired or already confirmed)"
        
        try:
            with transaction.atomic():
                # ✅ Create TaskPackage with payment proof
                task_package = TaskPackage.objects.create(
                    cat=self.cat,
                    created_by=self.created_by,  # Original staff who made booking
                    status='pending',
                    notes=self.notes or f'Converted from {self.booking_id}',
                    branch=self.branch,
                    booking_type='type_a',  # Now has payment proof
                    payment_proof=payment_proof_file,
                    scheduled_date=self.scheduled_date,
                    arrival_status='arrived',  # Customer already arrived
                    points_awarded=False,  # Will be set to True below
                    total_points=self.total_points,
                )
                
                # ✅ Create individual tasks
                tasks = self.get_selected_tasks()
                for task_type in tasks:
                    Task.objects.create(
                        package=task_package,
                        task_type=task_type,
                        points=task_type.points,
                        scheduled_date=self.scheduled_date,
                        scheduled_time=self.scheduled_time,
                        status='pending',
                    )
                
                # ✅✅✅ AWARD POINTS TO ORIGINAL STAFF
                # This is the key fix - points go to whoever created the booking
                success = task_package.award_points_immediately()
                
                if not success:
                    raise Exception("Failed to award points")
                
                # ✅ Update pending booking status
                self.status = 'confirmed'
                self.confirmed_at = timezone.now()
                self.confirmed_by = confirmed_by_user  # Who confirmed (might be manager)
                self.payment_proof = payment_proof_file
                self.converted_to_package = task_package
                self.save()
                
                # ✅ Create notification for original staff
                from task_management.models import Notification
                Notification.objects.create(
                    user=self.created_by,  # Notify the staff who made the booking
                    notification_type='points_awarded',
                    title=f'Booking {self.booking_id} Confirmed!',
                    message=f'Customer arrived and paid. {self.total_points} points awarded to you!',
                    link='/registration/my-bookings/'
                )
                
                return True, task_package, None
    
        except Exception as e:
            import traceback
            print(f"Error in confirm_and_convert: {traceback.format_exc()}")
            return False, None, str(e)
    
    def mark_as_expired(self):
        """Mark booking as expired"""
        if self.status == 'pending_payment':
            self.status = 'expired'
            self.expired_at = timezone.now()
            self.save()
            
            # Notify staff
            from task_management.models import Notification
            Notification.objects.create(
                user=self.created_by,
                title=f'Booking {self.booking_id} Expired',
                message=f'Customer did not arrive on {self.scheduled_date.strftime("%b %d, %Y")}',
                notification_type='warning'
            )
    
    def cancel(self, cancelled_by_user):
        """Manually cancel the booking"""
        if self.status == 'pending_payment':
            self.status = 'cancelled'
            self.confirmed_by = cancelled_by_user
            self.confirmed_at = timezone.now()
            self.save()
            return True
        return False
