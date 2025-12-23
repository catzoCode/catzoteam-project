# schedule/forms.py
# Forms for schedule management

from django import forms
from django.core.exceptions import ValidationError
from .models import Schedule, LeaveRequest, ShiftSwapRequest
from accounts.models import User
from datetime import datetime, timedelta

class ScheduleForm(forms.ModelForm):
    """Form for creating/editing single schedule"""
    
    class Meta:
        model = Schedule
        fields = ['staff', 'date', 'shift_type', 'start_time', 'end_time', 'notes']
        widgets = {
            'staff': forms.Select(attrs={'class': 'form-select'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'shift_type': forms.Select(attrs={'class': 'form-select'}),
            'start_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # IMPORTANT: Set default empty queryset first
        self.fields['staff'].queryset = User.objects.none()
        
        # Filter staff based on user role
        if user:
            if user.role == 'manager':
                # Manager can only schedule staff in their branch
                staff_queryset = User.objects.filter(
                    branch=user.branch,
                    role='staff',
                    is_active=True
                ).order_by('username')
                
                self.fields['staff'].queryset = staff_queryset
                
                # CRITICAL: Add helpful label if no staff available
                if not staff_queryset.exists():
                    self.fields['staff'].empty_label = f"No staff in {user.branch} branch"
                else:
                    self.fields['staff'].empty_label = "Select a staff member"
                
            elif user.role == 'admin':
                # Admin can schedule anyone
                staff_queryset = User.objects.filter(
                    role__in=['staff', 'manager'],
                    is_active=True
                ).order_by('branch', 'username')
                
                self.fields['staff'].queryset = staff_queryset
                self.fields['staff'].empty_label = "Select a staff member"
        
        # Make time fields not required (will be validated based on shift_type)
        self.fields['start_time'].required = False
        self.fields['end_time'].required = False
        
        # Make staff field required
        self.fields['staff'].required = True
    
    def clean(self):
        cleaned_data = super().clean()
        shift_type = cleaned_data.get('shift_type')
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        staff = cleaned_data.get('staff')
        
        # Check if staff was selected
        if not staff:
            raise ValidationError("Please select a staff member.")
        
        # OFF days don't need times
        if shift_type == 'off':
            cleaned_data['start_time'] = None
            cleaned_data['end_time'] = None
        else:
            # Working days must have times
            if not start_time or not end_time:
                raise ValidationError("Start time and end time are required for working shifts.")
        
        return cleaned_data


class BulkScheduleForm(forms.Form):
    """Form for bulk schedule creation"""
    
    MODE_CHOICES = [
        ('same_shift', 'Same Shift for Multiple Staff'),
        ('weekly_pattern', 'Weekly Pattern for One Staff'),
        ('copy_week', 'Copy From Previous Week'),
    ]
    
    # Mode selection
    mode = forms.ChoiceField(
        choices=MODE_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        initial='same_shift'
    )
    
    # Date range
    start_date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        help_text="Start date (Monday recommended)"
    )
    end_date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        help_text="End date (Sunday recommended)"
    )
    
    # For same_shift mode
    staff_members = forms.ModelMultipleChoiceField(
        queryset=User.objects.none(),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'staff-checkbox'}),
        required=False,
        help_text="Select staff to schedule"
    )

    shift_type = forms.ChoiceField(
        choices=Schedule.SHIFT_TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=False
    )
    start_time = forms.TimeField(
        widget=forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
        required=False
    )
    end_time = forms.TimeField(
        widget=forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
        required=False
    )
    
    # For weekly_pattern mode
    single_staff = forms.ModelChoiceField(
        queryset=User.objects.none(),
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=False,
        help_text="Select one staff member"
    )
    
    # Days of week patterns (for weekly_pattern mode)
    monday_shift = forms.ChoiceField(choices=Schedule.SHIFT_TYPE_CHOICES, required=False)
    monday_start = forms.TimeField(widget=forms.TimeInput(attrs={'type': 'time'}), required=False)
    monday_end = forms.TimeField(widget=forms.TimeInput(attrs={'type': 'time'}), required=False)
    
    tuesday_shift = forms.ChoiceField(choices=Schedule.SHIFT_TYPE_CHOICES, required=False)
    tuesday_start = forms.TimeField(widget=forms.TimeInput(attrs={'type': 'time'}), required=False)
    tuesday_end = forms.TimeField(widget=forms.TimeInput(attrs={'type': 'time'}), required=False)
    
    wednesday_shift = forms.ChoiceField(choices=Schedule.SHIFT_TYPE_CHOICES, required=False)
    wednesday_start = forms.TimeField(widget=forms.TimeInput(attrs={'type': 'time'}), required=False)
    wednesday_end = forms.TimeField(widget=forms.TimeInput(attrs={'type': 'time'}), required=False)
    
    thursday_shift = forms.ChoiceField(choices=Schedule.SHIFT_TYPE_CHOICES, required=False)
    thursday_start = forms.TimeField(widget=forms.TimeInput(attrs={'type': 'time'}), required=False)
    thursday_end = forms.TimeField(widget=forms.TimeInput(attrs={'type': 'time'}), required=False)
    
    friday_shift = forms.ChoiceField(choices=Schedule.SHIFT_TYPE_CHOICES, required=False)
    friday_start = forms.TimeField(widget=forms.TimeInput(attrs={'type': 'time'}), required=False)
    friday_end = forms.TimeField(widget=forms.TimeInput(attrs={'type': 'time'}), required=False)
    
    saturday_shift = forms.ChoiceField(choices=Schedule.SHIFT_TYPE_CHOICES, required=False)
    saturday_start = forms.TimeField(widget=forms.TimeInput(attrs={'type': 'time'}), required=False)
    saturday_end = forms.TimeField(widget=forms.TimeInput(attrs={'type': 'time'}), required=False)
    
    sunday_shift = forms.ChoiceField(choices=Schedule.SHIFT_TYPE_CHOICES, required=False)
    sunday_start = forms.TimeField(widget=forms.TimeInput(attrs={'type': 'time'}), required=False)
    sunday_end = forms.TimeField(widget=forms.TimeInput(attrs={'type': 'time'}), required=False)
    
    # For copy_week mode
    copy_from_date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        required=False,
        help_text="Select a Monday from previous week to copy"
    )
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Filter staff based on user role
        if user:
            if user.role == 'manager':
                # Manager can only schedule their branch
                staff_queryset = User.objects.filter(
                    branch=user.branch,
                    role='staff',
                    is_active=True
                ).order_by('username')
            elif user.role == 'admin':
                # Admin can schedule anyone
                staff_queryset = User.objects.filter(
                    role__in=['staff', 'manager'],
                    is_active=True
                ).order_by('branch', 'username')
            else:
                staff_queryset = User.objects.none()
            
            self.fields['staff_members'].queryset = staff_queryset
            self.fields['single_staff'].queryset = staff_queryset
    
    def clean(self):
        cleaned_data = super().clean()
        mode = cleaned_data.get('mode')
        
        # Validate based on mode
        if mode == 'same_shift':
            if not cleaned_data.get('staff_members'):
                raise ValidationError("Please select at least one staff member.")
            if cleaned_data.get('shift_type') != 'off':
                if not cleaned_data.get('start_time') or not cleaned_data.get('end_time'):
                    raise ValidationError("Start time and end time are required.")
        
        elif mode == 'weekly_pattern':
            if not cleaned_data.get('single_staff'):
                raise ValidationError("Please select a staff member.")
        
        elif mode == 'copy_week':
            if not cleaned_data.get('copy_from_date'):
                raise ValidationError("Please select a date to copy from.")
        
        # Validate date range
        start = cleaned_data.get('start_date')
        end = cleaned_data.get('end_date')
        if start and end and end < start:
            raise ValidationError("End date cannot be before start date.")
        
        return cleaned_data


class LeaveRequestForm(forms.ModelForm):
    """Form for staff to request leave"""
    
    class Meta:
        model = LeaveRequest
        exclude = ('staff',) 
        fields = ['leave_type', 'start_date', 'end_date', 'reason', 'medical_proof']
        widgets = {
            'leave_type': forms.Select(attrs={'class': 'form-select'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'medical_proof': forms.FileInput(attrs={'class': 'form-control'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        leave_type = cleaned_data.get('leave_type')
        medical_proof = cleaned_data.get('medical_proof')
        
        # Medical leave requires proof
        if leave_type == 'medical' and not medical_proof:
            raise ValidationError("Medical certificate is required for medical leave.")
        
        return cleaned_data


class ShiftSwapRequestForm(forms.ModelForm):
    """Form for staff to request shift swap"""
    
    class Meta:
        model = ShiftSwapRequest
        fields = ['counterpart', 'counterpart_schedule', 'reason']
        widgets = {
            'counterpart': forms.Select(attrs={'class': 'form-select'}),
            'counterpart_schedule': forms.Select(attrs={'class': 'form-select'}),
            'reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        requester_schedule = kwargs.pop('requester_schedule', None)
        super().__init__(*args, **kwargs)
        
        if user and requester_schedule:
            # Can only swap with staff from same branch
            self.fields['counterpart'].queryset = User.objects.filter(
                branch=user.branch,
                role='staff',
                is_active=True
            ).exclude(id=user.id).order_by('username')
            
            # Can only swap with schedules on the same date
            self.fields['counterpart_schedule'].queryset = Schedule.objects.filter(
                date=requester_schedule.date,
                branch=user.branch
            ).exclude(staff=user).exclude(shift_type='off')