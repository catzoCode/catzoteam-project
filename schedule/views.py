# schedule/views.py - Part 1: Admin & Manager Views

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Count
from django.utils import timezone
from datetime import datetime, timedelta, date
from calendar import monthrange
import json

from .models import Schedule, LeaveRequest, ShiftSwapRequest
from .forms import ScheduleForm, BulkScheduleForm, LeaveRequestForm, ShiftSwapRequestForm
from accounts.models import User

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.template.loader import render_to_string
from datetime import datetime, timedelta, date
from calendar import monthrange

from .models import Schedule
from accounts.models import User


from datetime import date, datetime, timedelta
import calendar
from collections import defaultdict

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from accounts.models import User
from .models import Schedule

# For PDF generation
try:
    from weasyprint import HTML
    import tempfile
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from datetime import datetime, timedelta, date

from .models import Schedule, LeaveRequest, ShiftSwapRequest
from .forms import LeaveRequestForm, ShiftSwapRequestForm
from datetime import date, timedelta
from calendar import monthrange

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .models import Schedule, LeaveRequest

def _build_days_data(user, start_date, end_date, include_pending=True):
    """
    Returns a list of day dicts:
    [{
        'date': <date>,
        'schedule': <Schedule|None>,
        'is_today': bool,
        'has_leave': bool,
        'leave_info': <LeaveRequest|None>,
    }, ...]
    """

    schedules_qs = Schedule.objects.filter(
        staff=user,
        date__range=[start_date, end_date]
    ).order_by('date')

    # For quick lookup
    schedule_map = {s.date: s for s in schedules_qs}

    # Which leave statuses to show on calendar
    if include_pending:
        leave_statuses = ['pending_manager', 'manager_approved', 'approved']
    else:
        leave_statuses = ['approved']

    leaves_qs = LeaveRequest.objects.filter(
        staff=user,
        status__in=leave_statuses,
        start_date__lte=end_date,
        end_date__gte=start_date
    ).order_by('-created_at')

    # Build a list of days
    days_data = []
    for i in range((end_date - start_date).days + 1):
        current_day = start_date + timedelta(days=i)

        # Find schedule
        day_schedule = schedule_map.get(current_day)

        # Find leave covering this day
        day_leave = None
        for leave in leaves_qs:
            if leave.start_date <= current_day <= leave.end_date:
                day_leave = leave
                break

        days_data.append({
            'date': current_day,
            'schedule': day_schedule,
            'is_today': current_day == date.today(),
            'has_leave': day_leave is not None,
            'leave_info': day_leave,
        })

    return days_data


# ============================================
# ADMIN VIEWS
# ============================================

@login_required
def admin_schedule_calendar(request):
    """Admin calendar view - Week or Month toggle"""
    if request.user.role != 'admin':
        messages.error(request, 'Access denied. Admin only.')
        return redirect('dashboard:staff_dashboard')
    
    # Get view type (week or month)
    view_type = request.GET.get('view', 'week')
    
    # Get date (default to today)
    date_str = request.GET.get('date', date.today().isoformat())
    try:
        current_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except:
        current_date = date.today()
    
    # Get branch filter (admin can see all)
    branch_filter = request.GET.get('branch', 'all')
    branch_filter = branch_filter.strip() if isinstance(branch_filter, str) else branch_filter

    
    if view_type == 'week':
        return admin_week_view(request, current_date, branch_filter)
    else:
        return admin_month_view(request, current_date, branch_filter)


def admin_week_view(request, current_date, branch_filter):
    """Admin week calendar view - FIXED"""
    from datetime import date as date_class
    
    # Get week start (Monday)
    week_start = current_date - timedelta(days=current_date.weekday())
    week_end = week_start + timedelta(days=6)
    
    # Generate week days
    week_days = [week_start + timedelta(days=i) for i in range(7)]
    
    # Get all staff
    if branch_filter == 'all':
        staff_list = User.objects.filter(
            role__in=['staff', 'manager'],
            is_active=True
        ).order_by('branch', 'username')
    else:
        staff_list = User.objects.filter(
            role__in=['staff', 'manager'],
            is_active=True,
            branch=branch_filter
        ).order_by('username')
    
    # Get schedules for the week
    schedules = Schedule.objects.filter(
        date__range=[week_start, week_end]
    ).select_related('staff')
    
    if branch_filter != 'all':
        schedules = schedules.filter(branch=branch_filter)
    
    # Create lookup dictionary: (staff_id, date_string) -> schedule
    schedule_lookup = {(s.staff_id, s.date.isoformat()): s for s in schedules}
    
    # Build rows the template can loop (FIXED)
    schedule_rows = []
    for staff in staff_list:
        cells = []
        for day in week_days:
            day_key = day.isoformat()
            cells.append({
                "day": day,
                "day_key": day_key,
                "schedule": schedule_lookup.get((staff.id, day_key)),
            })
        schedule_rows.append({
            "staff": staff,
            "cells": cells,
        })
    
    # Get branches for filter
    # Get branches for filter (DEDUP + CLEAN)
    branch_codes = (
        User.objects.filter(is_active=True)
        .exclude(branch__isnull=True)
        .exclude(branch__exact="")
        .values_list('branch', flat=True)
    )

    seen = set()
    clean_codes = []
    for code in branch_codes:
        c = str(code).strip()
        if not c:
            continue
        key = c.lower()  # normalize for dedupe
        if key in seen:
            continue
        seen.add(key)
        clean_codes.append(c)

    clean_codes.sort(key=lambda x: x.replace("_", " ").title())

    branches = [{"value": c, "label": c.replace("_", " ").title()} for c in clean_codes]

    
    # Navigation dates
    prev_week = week_start - timedelta(days=7)
    next_week = week_start + timedelta(days=7)
    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    
    context = {
        'view_type': 'week',
        'current_date': current_date,
        'week_start': week_start,
        'week_end': week_end,
        'week_days': week_days,
        'staff_list': staff_list,
        'schedule_rows': schedule_rows,  # This is the FIXED structure
        'branch_filter': branch_filter,
        'branches': branches,
        'prev_week': prev_week,
        'next_week': next_week,
        "day_names": day_names,
        'today': date_class.today(),  # Add today for highlighting
    }
    
    return render(request, 'schedule/admin/calendar_week.html', context)


def admin_month_view(request, current_date, branch_filter):
    """Admin month calendar view - FIXED to match template (no get_item)"""
    from collections import defaultdict
    import calendar
    from datetime import date as date_class

    # Month boundaries (real month)
    first_day = current_date.replace(day=1)
    last_day_num = calendar.monthrange(first_day.year, first_day.month)[1]
    last_day = current_date.replace(day=last_day_num)

    # Calendar grid boundaries (Mon -> Sun)
    calendar_start = first_day - timedelta(days=first_day.weekday())
    calendar_end = last_day + timedelta(days=(6 - last_day.weekday()))

    # Build weeks (list of list of dates)
    weeks = []
    day_ptr = calendar_start
    while day_ptr <= calendar_end:
        week = [day_ptr + timedelta(days=i) for i in range(7)]
        weeks.append(week)
        day_ptr += timedelta(days=7)

    # Pull schedules for visible grid range
    schedules = Schedule.objects.filter(date__range=[calendar_start, calendar_end]).select_related('staff')
    if branch_filter != 'all':
        schedules = schedules.filter(branch=branch_filter)

    # Count schedules per day
    counts = defaultdict(int)
    for s in schedules:
        counts[s.date.isoformat()] += 1

    # Convert weeks -> cell objects for template
    calendar_weeks = []
    for week in weeks:
        row = []
        for d in week:
            key = d.isoformat()
            row.append({
                "day": d,
                "key": key,
                "count": counts.get(key, 0),
            })
        calendar_weeks.append(row)

    # Branch list for dropdown
    # Branch list for dropdown (DEDUP + CLEAN)
    branch_codes = (
        User.objects.filter(is_active=True)
        .exclude(branch__isnull=True)
        .exclude(branch__exact="")
        .values_list('branch', flat=True)
    )

    seen = set()
    clean_codes = []
    for code in branch_codes:
        c = str(code).strip()
        if not c:
            continue
        key = c.lower()
        if key in seen:
            continue
        seen.add(key)
        clean_codes.append(c)

    clean_codes.sort(key=lambda x: x.replace("_", " ").title())

    branches = [{"value": c, "label": c.replace("_", " ").title()} for c in clean_codes]


    # Navigation
    prev_month = (first_day - timedelta(days=1)).replace(day=1)
    next_month = (last_day + timedelta(days=1)).replace(day=1)

    context = {
        'view_type': 'month',
        'current_date': current_date,
        'month_start': first_day,            # template compares day.month with month_start.month
        'today': date_class.today(),         # highlight today
        'day_names': ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        'calendar_weeks': calendar_weeks,    # NEW: cells
        'branch_filter': branch_filter,
        'branches': branches,
        'prev_month': prev_month,
        'next_month': next_month,
    }

    return render(request, 'schedule/admin/calendar_month.html', context)


@login_required
def admin_create_schedule(request):
    """Admin create single schedule"""
    if request.user.role != 'admin':
        messages.error(request, 'Access denied.')
        return redirect('dashboard:staff_dashboard')
    
    if request.method == 'POST':
        form = ScheduleForm(request.POST, user=request.user)
        if form.is_valid():
            schedule = form.save(commit=False)
            schedule.created_by = request.user
            schedule.branch = schedule.staff.branch
            try:
                schedule.save()
                messages.success(request, f'Schedule created for {schedule.staff.username}')
                return redirect('schedule:admin_calendar')
            except Exception as e:
                messages.error(request, f'Error: {str(e)}')
        else:
            for error in form.errors.values():
                messages.error(request, error)
    else:
        form = ScheduleForm(user=request.user)
    
    context = {'form': form}
    return render(request, 'schedule/admin/create_schedule.html', context)


@login_required
def admin_bulk_create(request):
    """Admin bulk schedule creation"""
    if request.user.role != 'admin':
        messages.error(request, 'Access denied.')
        return redirect('dashboard:staff_dashboard')
    
    if request.method == 'POST':
        form = BulkScheduleForm(request.POST, user=request.user)
        if form.is_valid():
            mode = form.cleaned_data['mode']
            created_count = 0
            
            try:
                if mode == 'same_shift':
                    created_count = create_same_shift_bulk(form.cleaned_data, request.user)
                elif mode == 'weekly_pattern':
                    created_count = create_weekly_pattern_bulk(form.cleaned_data, request.user)
                elif mode == 'copy_week':
                    created_count = copy_week_schedules(form.cleaned_data, request.user)
                
                messages.success(request, f'Successfully created {created_count} schedule(s)!')
                return redirect('schedule:admin_calendar')
            
            except Exception as e:
                messages.error(request, f'Error: {str(e)}')
        else:
            for error in form.errors.values():
                messages.error(request, error)
    else:
        form = BulkScheduleForm(user=request.user)
    
    context = {'form': form}
    return render(request, 'schedule/admin/bulk_create.html', context)


def create_same_shift_bulk(data, creator):
    """Create same shift for multiple staff"""
    staff_members = data['staff_members']
    start_date = data['start_date']
    end_date = data['end_date']
    shift_type = data['shift_type']
    start_time = data.get('start_time')
    end_time = data.get('end_time')
    
    created_count = 0
    current_date = start_date
    
    while current_date <= end_date:
        for staff in staff_members:
            # Check if already scheduled
            if Schedule.objects.filter(staff=staff, date=current_date).exists():
                continue
            
            # Check for leave
            has_leave = LeaveRequest.objects.filter(
                staff=staff,
                start_date__lte=current_date,
                end_date__gte=current_date,
                status='approved'
            ).exists()
            
            if has_leave:
                continue
            
            # Create schedule
            Schedule.objects.create(
                staff=staff,
                date=current_date,
                shift_type=shift_type,
                start_time=start_time if shift_type != 'off' else None,
                end_time=end_time if shift_type != 'off' else None,
                branch=staff.branch,
                created_by=creator
            )
            created_count += 1
        
        current_date += timedelta(days=1)
    
    return created_count


def create_weekly_pattern_bulk(data, creator):
    """Create weekly pattern for one staff"""
    staff = data['single_staff']
    start_date = data['start_date']
    end_date = data['end_date']
    
    # Week pattern
    week_pattern = {
        0: {'shift': data.get('monday_shift'), 'start': data.get('monday_start'), 'end': data.get('monday_end')},
        1: {'shift': data.get('tuesday_shift'), 'start': data.get('tuesday_start'), 'end': data.get('tuesday_end')},
        2: {'shift': data.get('wednesday_shift'), 'start': data.get('wednesday_start'), 'end': data.get('wednesday_end')},
        3: {'shift': data.get('thursday_shift'), 'start': data.get('thursday_start'), 'end': data.get('thursday_end')},
        4: {'shift': data.get('friday_shift'), 'start': data.get('friday_start'), 'end': data.get('friday_end')},
        5: {'shift': data.get('saturday_shift'), 'start': data.get('saturday_start'), 'end': data.get('saturday_end')},
        6: {'shift': data.get('sunday_shift'), 'start': data.get('sunday_start'), 'end': data.get('sunday_end')},
    }
    
    created_count = 0
    current_date = start_date
    
    while current_date <= end_date:
        weekday = current_date.weekday()
        pattern = week_pattern[weekday]
        
        if pattern['shift']:
            # Check if already scheduled
            if Schedule.objects.filter(staff=staff, date=current_date).exists():
                current_date += timedelta(days=1)
                continue
            
            # Check for leave
            has_leave = LeaveRequest.objects.filter(
                staff=staff,
                start_date__lte=current_date,
                end_date__gte=current_date,
                status='approved'
            ).exists()
            
            if not has_leave:
                Schedule.objects.create(
                    staff=staff,
                    date=current_date,
                    shift_type=pattern['shift'],
                    start_time=pattern['start'] if pattern['shift'] != 'off' else None,
                    end_time=pattern['end'] if pattern['shift'] != 'off' else None,
                    branch=staff.branch,
                    created_by=creator
                )
                created_count += 1
        
        current_date += timedelta(days=1)
    
    return created_count


def copy_week_schedules(data, creator):
    """Copy schedules from previous week"""
    copy_from = data['copy_from_date']
    start_date = data['start_date']
    
    # Get source week schedules
    source_start = copy_from
    source_end = source_start + timedelta(days=6)
    
    source_schedules = Schedule.objects.filter(
        date__range=[source_start, source_end]
    )
    
    created_count = 0
    
    for source in source_schedules:
        # Calculate new date (same weekday, new week)
        days_diff = (source.date - source_start).days
        new_date = start_date + timedelta(days=days_diff)
        
        # Check if already scheduled
        if Schedule.objects.filter(staff=source.staff, date=new_date).exists():
            continue
        
        # Check for leave
        has_leave = LeaveRequest.objects.filter(
            staff=source.staff,
            start_date__lte=new_date,
            end_date__gte=new_date,
            status='approved'
        ).exists()
        
        if has_leave:
            continue
        
        # Copy schedule
        Schedule.objects.create(
            staff=source.staff,
            date=new_date,
            shift_type=source.shift_type,
            start_time=source.start_time,
            end_time=source.end_time,
            branch=source.branch,
            notes=source.notes,
            created_by=creator
        )
        created_count += 1
    
    return created_count


@login_required
def admin_edit_schedule(request, schedule_id):
    """Admin edit schedule"""
    if request.user.role != 'admin':
        messages.error(request, 'Access denied.')
        return redirect('dashboard:staff_dashboard')
    
    schedule = get_object_or_404(Schedule, id=schedule_id)
    
    if request.method == 'POST':
        form = ScheduleForm(request.POST, instance=schedule, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Schedule updated successfully')
            return redirect('schedule:admin_calendar')
    else:
        form = ScheduleForm(instance=schedule, user=request.user)
    
    context = {'form': form, 'schedule': schedule}
    return render(request, 'schedule/admin/edit_schedule.html', context)


@login_required
def admin_delete_schedule(request, schedule_id):
    """Admin delete schedule"""
    if request.user.role != 'admin':
        messages.error(request, 'Access denied.')
        return redirect('dashboard:staff_dashboard')
    
    schedule = get_object_or_404(Schedule, id=schedule_id)
    
    if request.method == 'POST':
        staff_name = schedule.staff.username
        schedule.delete()
        messages.success(request, f'Schedule deleted for {staff_name}')
        return redirect('schedule:admin_calendar')
    
    context = {'schedule': schedule}
    return render(request, 'schedule/admin/delete_schedule.html', context)


# ============================================
# MANAGER VIEWS (Similar to Admin but filtered)
# ============================================

@login_required
def manager_schedule_calendar(request):
    """Manager calendar view - only their branch"""
    if request.user.role != 'manager':
        messages.error(request, 'Access denied. Manager only.')
        return redirect('dashboard:staff_dashboard')

    view_type = request.GET.get('view', 'week')
    date_str = request.GET.get('date', date.today().isoformat())

    try:
        current_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except Exception:
        current_date = date.today()

    # Manager can only see their branch
    branch_filter = request.user.branch

    if view_type == 'week':
        return manager_week_view(request, current_date, branch_filter)
    else:
        return manager_month_view(request, current_date, branch_filter)


def manager_week_view(request, current_date, branch):
    """Manager week view - same as admin but filtered"""
    week_start = current_date - timedelta(days=current_date.weekday())
    week_end = week_start + timedelta(days=6)
    week_days = [week_start + timedelta(days=i) for i in range(7)]

    # Only staff in manager's branch
    staff_list = User.objects.filter(
        role='staff',
        is_active=True,
        branch=branch
    ).order_by('username')

    schedules = Schedule.objects.filter(
        date__range=[week_start, week_end],
        branch=branch
    ).select_related('staff')

    # Organize schedules (no template dict lookup)
    schedule_lookup = {(s.staff_id, s.date.isoformat()): s for s in schedules}

    schedule_rows = []
    for staff in staff_list:
        cells = []
        for day in week_days:
            day_key = day.isoformat()
            cells.append({
                "day": day,
                "day_key": day_key,
                "schedule": schedule_lookup.get((staff.id, day_key)),
            })
        schedule_rows.append({
            "staff": staff,
            "cells": cells,
        })

    prev_week = week_start - timedelta(days=7)
    next_week = week_start + timedelta(days=7)

    context = {
        'view_type': 'week',
        'current_date': current_date,
        'week_start': week_start,
        'week_end': week_end,
        'week_days': week_days,
        'staff_list': staff_list,
        'schedule_rows': schedule_rows,
        'branch_filter': branch,
        'prev_week': prev_week,
        'next_week': next_week,
    }

    return render(request, 'schedule/manager/calendar_week.html', context)


def manager_month_view(request, current_date, branch):
    """Manager month view - fixed: no get_item filter needed"""
    # Month boundaries
    first_day = current_date.replace(day=1)
    last_day_num = calendar.monthrange(first_day.year, first_day.month)[1]
    last_day = current_date.replace(day=last_day_num)

    # Calendar grid should start on Monday
    month_start = first_day - timedelta(days=first_day.weekday())
    month_end = last_day + timedelta(days=(6 - last_day.weekday()))

    # Build weeks (list of list of dates)
    weeks = []
    day_ptr = month_start
    while day_ptr <= month_end:
        week = [day_ptr + timedelta(days=i) for i in range(7)]
        weeks.append(week)
        day_ptr += timedelta(days=7)

    # Pull schedules in visible range (includes other-month cells for grid)
    schedules = Schedule.objects.filter(
        date__range=[month_start, month_end],
        branch=branch
    )

    # Count schedules per day
    counts = defaultdict(int)
    for s in schedules:
        counts[s.date.isoformat()] += 1

    # Convert weeks to "cell" objects so template doesn't need get_item
    calendar_weeks = []
    for week in weeks:
        row = []
        for d in week:
            key = d.isoformat()
            row.append({
                "day": d,
                "key": key,
                "count": counts.get(key, 0),
            })
        calendar_weeks.append(row)

    # Navigation
    prev_month = (first_day - timedelta(days=1)).replace(day=1)
    next_month = (last_day + timedelta(days=1)).replace(day=1)

    context = {
        'view_type': 'month',
        'current_date': current_date,
        'month_start': first_day,   # used for month label / comparisons
        'today': date.today(),
        'calendar_weeks': calendar_weeks,
        'day_names': ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        'branch_filter': branch,
        'prev_month': prev_month,
        'next_month': next_month,
    }

    return render(request, 'schedule/manager/calendar_month.html', context)

@login_required
def manager_create_schedule(request):
    """Manager create schedule (only for their staff) - WITH DEBUGGING"""
    
    # ===== STEP 1: Check if user is manager =====
    if request.user.role != 'manager':
        messages.error(request, 'Access denied. Manager role required.')
        return redirect('dashboard:staff_dashboard')
    
    # ===== STEP 2: Check if manager has a branch =====
    print(f"DEBUG: Manager username: {request.user.username}")
    print(f"DEBUG: Manager branch: {request.user.branch}")
    print(f"DEBUG: Manager role: {request.user.role}")
    
    if not request.user.branch:
        messages.error(
            request, 
            'Your account does not have a branch assigned. Please contact admin.'
        )
        return redirect('schedule:manager_calendar')
    
    # ===== STEP 3: Check available staff =====
    available_staff = User.objects.filter(
        branch=request.user.branch,
        role='staff',
        is_active=True
    )
    
    print(f"DEBUG: Available staff count: {available_staff.count()}")
    for staff in available_staff:
        print(f"DEBUG: - {staff.username} (branch={staff.branch}, role={staff.role})")
    
    if not available_staff.exists():
        messages.warning(
            request, 
            f'No active staff found in your branch ({request.user.branch}). '
            'Please add staff to your branch first or contact admin.'
        )
        # Don't redirect - still show the form
    
    # ===== STEP 4: Handle form submission =====
    if request.method == 'POST':
        print(f"DEBUG: POST data: {request.POST}")
        
        form = ScheduleForm(request.POST, user=request.user)
        
        print(f"DEBUG: Form is valid: {form.is_valid()}")
        if not form.is_valid():
            print(f"DEBUG: Form errors: {form.errors}")
        
        if form.is_valid():
            schedule = form.save(commit=False)
            
            print(f"DEBUG: Selected staff: {schedule.staff.username}")
            print(f"DEBUG: Selected staff branch: {schedule.staff.branch}")
            print(f"DEBUG: Selected staff role: {schedule.staff.role}")
            
            # Double-check: Ensure staff is from manager's branch
            if schedule.staff.branch != request.user.branch:
                messages.error(
                    request, 
                    f'Error: {schedule.staff.username} is not in your branch. '
                    f'Their branch is {schedule.staff.branch}, yours is {request.user.branch}.'
                )
                return redirect('schedule:manager_calendar')
            
            # Ensure not scheduling managers
            if schedule.staff.role == 'manager':
                messages.error(request, 'You cannot schedule other managers.')
                return redirect('schedule:manager_calendar')
            
            # Set metadata
            schedule.created_by = request.user
            schedule.branch = request.user.branch
            
            try:
                schedule.save()
                messages.success(
                    request, 
                    f'✅ Schedule created successfully for {schedule.staff.username} '
                    f'on {schedule.date}'
                )
                return redirect('schedule:manager_calendar')
            except Exception as e:
                print(f"DEBUG: Save error: {str(e)}")
                messages.error(request, f'Error saving schedule: {str(e)}')
        else:
            # Show all form errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        # GET request - create blank form
        form = ScheduleForm(user=request.user)
    
    # ===== STEP 5: Render template =====
    context = {
        'form': form,
        'available_staff_count': available_staff.count(),
        'debug_info': {
            'manager_branch': request.user.branch,
            'manager_role': request.user.role,
            'staff_count': available_staff.count(),
            'staff_list': list(available_staff.values_list('username', 'branch', 'role')),
        }
    }
    
    return render(request, 'schedule/manager/create_schedule.html', context)

@login_required
def manager_edit_schedule(request, schedule_id):
    """Manager edit schedule (only for their branch staff)"""
    if request.user.role != 'manager':
        messages.error(request, 'Access denied.')
        return redirect('dashboard:staff_dashboard')
    
    schedule = get_object_or_404(Schedule, id=schedule_id)
    
    # Check if schedule is from manager's branch
    if schedule.branch != request.user.branch:
        messages.error(request, 'You can only edit schedules from your branch.')
        return redirect('schedule:manager_calendar')
    
    if request.method == 'POST':
        form = ScheduleForm(request.POST, instance=schedule, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Schedule updated successfully')
            return redirect('schedule:manager_calendar')
    else:
        form = ScheduleForm(instance=schedule, user=request.user)
    
    context = {'form': form, 'schedule': schedule}
    return render(request, 'schedule/manager/edit_schedule.html', context)


@login_required
def manager_delete_schedule(request, schedule_id):
    """Manager delete schedule (only for their branch staff)"""
    if request.user.role != 'manager':
        messages.error(request, 'Access denied.')
        return redirect('dashboard:staff_dashboard')
    
    schedule = get_object_or_404(Schedule, id=schedule_id)
    
    # Check if schedule is from manager's branch
    if schedule.branch != request.user.branch:
        messages.error(request, 'You can only delete schedules from your branch.')
        return redirect('schedule:manager_calendar')
    
    if request.method == 'POST':
        staff_name = schedule.staff.username
        schedule.delete()
        messages.success(request, f'Schedule deleted for {staff_name}')
        return redirect('schedule:manager_calendar')
    
    context = {'schedule': schedule}
    return render(request, 'schedule/manager/delete_schedule.html', context)


@login_required  
def manager_my_leaves(request):
    """Manager view their own leave requests"""
    if request.user.role != 'manager':
        messages.error(request, 'Access denied.')
        return redirect('dashboard:staff_dashboard')
    
    leave_requests = LeaveRequest.objects.filter(
        staff=request.user
    ).order_by('-created_at')
    
    context = {'leave_requests': leave_requests}
    return render(request, 'schedule/manager/my_leaves.html', context)
# ============================================
# STAFF VIEWS
# ============================================

@login_required
def staff_my_schedule(request):
    """Staff view their own schedule - 7 day + month, with leaves shown properly"""

    # Default 7 days
    start_date = date.today()
    end_date = start_date + timedelta(days=6)

    view_type = request.GET.get('view', '7day')

    # Show pending leaves too (recommended so user sees it immediately)
    include_pending = True

    if view_type == 'month':
        month_start = start_date.replace(day=1)
        days_in_month = monthrange(month_start.year, month_start.month)[1]
        month_end = month_start.replace(day=days_in_month)

        # Build month days list (this fixes leave-only days not appearing)
        month_days_data = _build_days_data(
            user=request.user,
            start_date=month_start,
            end_date=month_end,
            include_pending=include_pending
        )

        context = {
            'view_type': 'month',
            'month_start': month_start,
            'month_end': month_end,
            'days_data': month_days_data,   # <-- IMPORTANT
        }
        return render(request, 'schedule/staff/my_schedule.html', context)

    # 7-day view
    week_days_data = _build_days_data(
        user=request.user,
        start_date=start_date,
        end_date=end_date,
        include_pending=include_pending
    )

    context = {
        'view_type': '7day',
        'days_data': week_days_data,
        'start_date': start_date,
        'end_date': end_date,
    }
    return render(request, 'schedule/staff/my_schedule.html', context)

# ============================================
# LEAVE REQUEST VIEWS
# ============================================


@login_required
def staff_request_leave(request):
    """Staff/Manager submit leave request"""

    if request.method == 'POST':
        form = LeaveRequestForm(request.POST, request.FILES)

        # ✅ IMPORTANT: set staff BEFORE validation
        form.instance.staff = request.user

        if form.is_valid():
            leave_request = form.save(commit=False)
            leave_request.staff = request.user  # keep it (double safety)

            # Workflow
            if request.user.role == 'manager':
                leave_request.status = 'manager_approved'
                leave_request.manager_approved_by = None
                leave_request.manager_approved_at = None
                leave_request.manager_notes = 'Manager leave request - sent directly to admin'
            else:
                leave_request.status = 'pending_manager'

            try:
                leave_request.save()

                messages.success(
                    request,
                    f'Leave request submitted for {leave_request.start_date} to {leave_request.end_date}. '
                    + ('Sent to admin for approval.' if request.user.role == 'manager' else 'Awaiting manager approval.')
                )

                return redirect('schedule:manager_my_leaves' if request.user.role == 'manager' else 'schedule:staff_my_leaves')

            except Exception as e:
                messages.error(request, f'Error submitting leave request: {e}')
        else:
            for field, errors in form.errors.items():
                for err in errors:
                    messages.error(request, f"{field}: {err}")

    else:
        form = LeaveRequestForm()

    return render(request, 'schedule/staff/request_leave.html', {
        'form': form,
        'is_manager': request.user.role == 'manager',
    })


@login_required
def staff_my_leaves(request):
    """Staff view their leave requests"""
    
    leave_requests = LeaveRequest.objects.filter(
        staff=request.user
    ).order_by('-created_at')
    
    context = {'leave_requests': leave_requests}
    return render(request, 'schedule/staff/my_leaves.html', context)

@login_required
def manager_my_leaves(request):
    """Manager view their own leave requests"""
    if request.user.role != 'manager':
        messages.error(request, 'Access denied.')
        return redirect('dashboard:staff_dashboard')
    
    leave_requests = LeaveRequest.objects.filter(
        staff=request.user
    ).order_by('-created_at')
    
    context = {'leave_requests': leave_requests}
    return render(request, 'schedule/manager/my_leaves.html', context)

@login_required
def manager_leave_requests(request):
    """Manager/Admin view and approve leave requests"""
    if request.user.role not in ['manager', 'admin']:
        messages.error(request, 'Access denied.')
        return redirect('dashboard:staff_dashboard')
    
    # Get pending requests
    if request.user.role == 'manager':
        # Manager sees their branch staff only (NOT other managers)
        pending_requests = LeaveRequest.objects.filter(
            staff__branch=request.user.branch,
            staff__role='staff',  # Only staff, not other managers
            status__in=['pending_manager']
        ).select_related('staff').order_by('-created_at')
        
        # History
        history = LeaveRequest.objects.filter(
            staff__branch=request.user.branch,
            staff__role='staff',
            status__in=['approved', 'rejected']
        ).select_related('staff').order_by('-updated_at')[:20]
        
    else:  # Admin
        # Admin sees:
        # 1. Manager leave requests (manager_approved status)
        # 2. Staff leave requests that manager approved
        pending_requests = LeaveRequest.objects.filter(
            status__in=['manager_approved']
        ).select_related('staff').order_by('-created_at')
        
        # History
        history = LeaveRequest.objects.filter(
            status__in=['approved', 'rejected']
        ).select_related('staff').order_by('-updated_at')[:20]
    
    context = {
        'pending_requests': pending_requests,
        'history': history,
    }
    
    return render(request, 'schedule/manager/leave_requests.html', context)

@login_required
def manager_my_schedule(request):
    """Manager view their own schedule - SAME as staff (7 day + month) with leaves"""

    if request.user.role != 'manager':
        messages.error(request, 'Access denied.')
        return redirect('dashboard:staff_dashboard')

    start_date = date.today()
    end_date = start_date + timedelta(days=6)

    view_type = request.GET.get('view', '7day')

    include_pending = True

    if view_type == 'month':
        month_start = start_date.replace(day=1)
        days_in_month = monthrange(month_start.year, month_start.month)[1]
        month_end = month_start.replace(day=days_in_month)

        month_days_data = _build_days_data(
            user=request.user,
            start_date=month_start,
            end_date=month_end,
            include_pending=include_pending
        )

        context = {
            'view_type': 'month',
            'month_start': month_start,
            'month_end': month_end,
            'days_data': month_days_data,
        }
        return render(request, 'schedule/manager/my_schedule.html', context)

    week_days_data = _build_days_data(
        user=request.user,
        start_date=start_date,
        end_date=end_date,
        include_pending=include_pending
    )

    context = {
        'view_type': '7day',
        'days_data': week_days_data,
        'start_date': start_date,
        'end_date': end_date,
    }
    return render(request, 'schedule/manager/my_schedule.html', context)


@login_required
def manager_approve_leave(request, leave_id):
    """Manager/Admin approve leave request"""
    if request.user.role not in ['manager', 'admin']:
        messages.error(request, 'Access denied.')
        return redirect('dashboard:staff_dashboard')
    
    leave_request = get_object_or_404(LeaveRequest, id=leave_id)
    
    # Validation: Manager can only approve their branch staff (not other managers)
    if request.user.role == 'manager':
        if leave_request.staff.branch != request.user.branch:
            messages.error(request, 'You can only approve leave for your branch.')
            return redirect('schedule:manager_leave_requests')
        
        if leave_request.staff.role == 'manager':
            messages.error(request, 'You cannot approve leave for other managers.')
            return redirect('schedule:manager_leave_requests')
    
    # Admin can approve anyone (including managers)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        notes = request.POST.get('notes', '')
        
        if action == 'approve':
            if request.user.role == 'manager':
                # Manager approval - goes to admin
                leave_request.status = 'manager_approved'
                leave_request.manager_approved_by = request.user
                leave_request.manager_approved_at = timezone.now()
                leave_request.manager_notes = notes
                leave_request.save()
                
                messages.success(
                    request,
                    f'Leave request approved and sent to admin for final approval.'
                )
                
            else:  # Admin
                # Admin final approval
                leave_request.status = 'approved'
                leave_request.admin_approved_by = request.user
                leave_request.admin_approved_at = timezone.now()
                leave_request.admin_notes = notes
                leave_request.save()
                
                # Special message for manager leave
                if leave_request.staff.role == 'manager':
                    messages.success(
                        request,
                        f'Leave request APPROVED for Manager {leave_request.staff.username}!'
                    )
                else:
                    messages.success(
                        request,
                        f'Leave request APPROVED for {leave_request.staff.username}!'
                    )
        
        elif action == 'reject':
            leave_request.status = 'rejected'
            if request.user.role == 'manager':
                leave_request.manager_notes = notes
            else:
                leave_request.admin_notes = notes
            leave_request.save()
            
            messages.warning(
                request,
                f'Leave request REJECTED for {leave_request.staff.username}.'
            )
        
        return redirect('schedule:manager_leave_requests')
    
    context = {
        'leave_request': leave_request,
        'is_manager_leave': leave_request.staff.role == 'manager',
    }
    return render(request, 'schedule/manager/approve_leave.html', context)

# ============================================
# SHIFT SWAP VIEWS
# ============================================

@login_required
def staff_request_swap(request):
    """Staff request to swap shift"""
    
    # Get staff's upcoming schedules (can only swap future shifts)
    my_schedules = Schedule.objects.filter(
        staff=request.user,
        date__gte=date.today(),
        shift_type__in=['morning', 'afternoon', 'evening', 'night', 'full_day']
    ).order_by('date')[:14]  # Next 2 weeks
    
    if request.method == 'POST':
        my_schedule_id = request.POST.get('my_schedule')
        my_schedule = get_object_or_404(Schedule, id=my_schedule_id, staff=request.user)
        
        form = ShiftSwapRequestForm(
            request.POST,
            user=request.user,
            requester_schedule=my_schedule
        )
        
        if form.is_valid():
            swap_request = form.save(commit=False)
            swap_request.requester = request.user
            swap_request.requester_schedule = my_schedule
            swap_request.status = 'pending_counterpart'
            
            try:
                swap_request.save()
                messages.success(
                    request,
                    f'Swap request sent to {swap_request.counterpart.username}. '
                    'Awaiting their agreement.'
                )
                return redirect('schedule:staff_my_swaps')
            except Exception as e:
                messages.error(request, f'Error: {str(e)}')
        else:
            for error in form.errors.values():
                messages.error(request, error)
    else:
        form = None
    
    context = {
        'my_schedules': my_schedules,
        'form': form,
    }
    return render(request, 'schedule/staff/request_swap.html', context)


@login_required
def staff_my_swaps(request):
    """Staff view their swap requests"""
    
    # Requests I sent
    sent_requests = ShiftSwapRequest.objects.filter(
        requester=request.user
    ).select_related(
        'counterpart',
        'requester_schedule',
        'counterpart_schedule'
    ).order_by('-created_at')
    
    # Requests I received
    received_requests = ShiftSwapRequest.objects.filter(
        counterpart=request.user,
        status='pending_counterpart'
    ).select_related(
        'requester',
        'requester_schedule',
        'counterpart_schedule'
    ).order_by('-created_at')
    
    context = {
        'sent_requests': sent_requests,
        'received_requests': received_requests,
    }
    return render(request, 'schedule/staff/my_swaps.html', context)


@login_required
def staff_respond_swap(request, swap_id):
    """Staff respond to swap request"""
    
    swap_request = get_object_or_404(
        ShiftSwapRequest,
        id=swap_id,
        counterpart=request.user,
        status='pending_counterpart'
    )
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'agree':
            swap_request.counterpart_agreed = True
            swap_request.counterpart_agreed_at = timezone.now()
            swap_request.status = 'pending_manager'
            swap_request.save()
            
            messages.success(
                request,
                f'You agreed to swap with {swap_request.requester.username}. '
                'Awaiting manager approval.'
            )
        
        elif action == 'decline':
            swap_request.status = 'rejected'
            swap_request.save()
            
            messages.info(
                request,
                f'Swap request declined.'
            )
        
        return redirect('schedule:staff_my_swaps')
    
    context = {'swap_request': swap_request}
    return render(request, 'schedule/staff/respond_swap.html', context)


@login_required
def manager_swap_requests(request):
    """Manager view and approve swap requests"""
    if request.user.role not in ['manager', 'admin']:
        messages.error(request, 'Access denied.')
        return redirect('dashboard:staff_dashboard')
    
    # Get pending swaps
    if request.user.role == 'manager':
        pending_swaps = ShiftSwapRequest.objects.filter(
            requester__branch=request.user.branch,
            status='pending_manager'
        ).select_related(
            'requester',
            'counterpart',
            'requester_schedule',
            'counterpart_schedule'
        ).order_by('-created_at')
    else:
        pending_swaps = ShiftSwapRequest.objects.filter(
            status='pending_manager'
        ).select_related(
            'requester',
            'counterpart',
            'requester_schedule',
            'counterpart_schedule'
        ).order_by('-created_at')
    
    context = {'pending_swaps': pending_swaps}
    return render(request, 'schedule/manager/swap_requests.html', context)


@login_required
def manager_approve_swap(request, swap_id):
    """Manager approve swap request"""
    if request.user.role not in ['manager', 'admin']:
        messages.error(request, 'Access denied.')
        return redirect('dashboard:staff_dashboard')
    
    swap_request = get_object_or_404(ShiftSwapRequest, id=swap_id)
    
    # Manager can only approve their branch
    if request.user.role == 'manager' and swap_request.requester.branch != request.user.branch:
        messages.error(request, 'You can only approve swaps for your branch.')
        return redirect('schedule:manager_swap_requests')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        notes = request.POST.get('notes', '')
        
        if action == 'approve':
            swap_request.status = 'approved'
            swap_request.manager_approved_by = request.user
            swap_request.manager_approved_at = timezone.now()
            swap_request.manager_notes = notes
            swap_request.save()
            
            # Execute the swap
            try:
                swap_request.execute_swap()
                messages.success(
                    request,
                    f'Swap approved and executed! '
                    f'{swap_request.requester.username} ↔ {swap_request.counterpart.username}'
                )
            except Exception as e:
                messages.error(request, f'Error executing swap: {str(e)}')
        
        elif action == 'reject':
            swap_request.status = 'rejected'
            swap_request.manager_notes = notes
            swap_request.save()
            
            messages.warning(request, 'Swap request rejected.')
        
        return redirect('schedule:manager_swap_requests')
    
    context = {'swap_request': swap_request}
    return render(request, 'schedule/manager/approve_swap.html', context)


# ============================================
# PDF EXPORT VIEWS
# ============================================

@login_required
def export_staff_schedule_pdf(request):
    """Staff export their own schedule as PDF"""
    
    # Get date range
    export_type = request.GET.get('type', 'week')  # week or month
    date_str = request.GET.get('date', date.today().isoformat())
    
    try:
        current_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except:
        current_date = date.today()
    
    if export_type == 'week':
        week_start = current_date - timedelta(days=current_date.weekday())
        week_end = week_start + timedelta(days=6)
        
        schedules = Schedule.objects.filter(
            staff=request.user,
            date__range=[week_start, week_end]
        ).order_by('date')
        
        context = {
            'staff': request.user,
            'export_type': 'week',
            'start_date': week_start,
            'end_date': week_end,
            'schedules': schedules,
            'generated_at': timezone.now(),
        }
        
        filename = f'schedule_{request.user.username}_{week_start.isoformat()}_to_{week_end.isoformat()}.pdf'
    
    else:  # month
        month_start = current_date.replace(day=1)
        days_in_month = monthrange(current_date.year, current_date.month)[1]
        month_end = month_start.replace(day=days_in_month)
        
        schedules = Schedule.objects.filter(
            staff=request.user,
            date__range=[month_start, month_end]
        ).order_by('date')
        
        context = {
            'staff': request.user,
            'export_type': 'month',
            'start_date': month_start,
            'end_date': month_end,
            'schedules': schedules,
            'generated_at': timezone.now(),
        }
        
        filename = f'schedule_{request.user.username}_{month_start.strftime("%Y-%m")}.pdf'
    
    # Generate PDF
    return generate_pdf_response(
        'schedule/pdf/staff_schedule.html',
        context,
        filename
    )


@login_required
def export_manager_schedule_pdf(request):
    """Manager export branch schedule as PDF"""
    if request.user.role != 'manager':
        messages.error(request, 'Access denied.')
        return redirect('dashboard:staff_dashboard')
    
    # Get date range
    export_type = request.GET.get('type', 'week')
    date_str = request.GET.get('date', date.today().isoformat())
    
    try:
        current_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except:
        current_date = date.today()
    
    # Get branch staff
    branch_staff = User.objects.filter(
        branch=request.user.branch,
        role='staff',
        is_active=True
    ).order_by('username')
    
    if export_type == 'week':
        week_start = current_date - timedelta(days=current_date.weekday())
        week_end = week_start + timedelta(days=6)
        
        schedules = Schedule.objects.filter(
            branch=request.user.branch,
            date__range=[week_start, week_end]
        ).select_related('staff').order_by('date', 'staff__username')
        
        # Organize by staff
        staff_schedules = {}
        for staff in branch_staff:
            staff_schedules[staff] = schedules.filter(staff=staff)
        
        context = {
            'manager': request.user,
            'branch': request.user.get_branch_display(),
            'export_type': 'week',
            'start_date': week_start,
            'end_date': week_end,
            'staff_schedules': staff_schedules,
            'generated_at': timezone.now(),
        }
        
        filename = f'schedule_{request.user.branch}_{week_start.isoformat()}_to_{week_end.isoformat()}.pdf'
    
    else:  # month
        month_start = current_date.replace(day=1)
        days_in_month = monthrange(current_date.year, current_date.month)[1]
        month_end = month_start.replace(day=days_in_month)
        
        schedules = Schedule.objects.filter(
            branch=request.user.branch,
            date__range=[month_start, month_end]
        ).select_related('staff').order_by('date', 'staff__username')
        
        # Organize by staff
        staff_schedules = {}
        for staff in branch_staff:
            staff_schedules[staff] = schedules.filter(staff=staff)
        
        context = {
            'manager': request.user,
            'branch': request.user.get_branch_display(),
            'export_type': 'month',
            'start_date': month_start,
            'end_date': month_end,
            'staff_schedules': staff_schedules,
            'generated_at': timezone.now(),
        }
        
        filename = f'schedule_{request.user.branch}_{month_start.strftime("%Y-%m")}.pdf'
    
    # Generate PDF
    return generate_pdf_response(
        'schedule/pdf/manager_schedule.html',
        context,
        filename
    )


@login_required
def export_admin_schedule_pdf(request):
    """Admin export all schedules as PDF"""
    if request.user.role != 'admin':
        messages.error(request, 'Access denied.')
        return redirect('dashboard:staff_dashboard')
    
    # Get parameters
    export_type = request.GET.get('type', 'week')
    branch_filter = request.GET.get('branch', 'all')
    date_str = request.GET.get('date', date.today().isoformat())
    
    try:
        current_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except:
        current_date = date.today()
    
    if export_type == 'week':
        week_start = current_date - timedelta(days=current_date.weekday())
        week_end = week_start + timedelta(days=6)
        
        # Get schedules
        if branch_filter == 'all':
            schedules = Schedule.objects.filter(
                date__range=[week_start, week_end]
            ).select_related('staff').order_by('branch', 'staff__username', 'date')
            
            branch_codes = (
                User.objects.filter(is_active=True)
                .exclude(branch__isnull=True)
                .exclude(branch__exact="")
                .values_list('branch', flat=True)
                .distinct()
            )

            branches = [
                {"value": code, "label": str(code).replace("_", " ").title()}
                for code in branch_codes
            ]
        else:
            schedules = Schedule.objects.filter(
                branch=branch_filter,
                date__range=[week_start, week_end]
            ).select_related('staff').order_by('staff__username', 'date')
            
            branches = [branch_filter]
        
        # Organize by branch and staff
        branch_data = {}
        for branch_code in branches:
            branch_name = dict(User.BRANCH_CHOICES).get(branch_code, branch_code)
            branch_schedules = schedules.filter(branch=branch_code)
            
            staff_list = User.objects.filter(
                branch=branch_code,
                role__in=['staff', 'manager'],
                is_active=True
            ).order_by('username')
            
            staff_schedules = {}
            for staff in staff_list:
                staff_schedules[staff] = branch_schedules.filter(staff=staff)
            
            branch_data[branch_name] = {
                'code': branch_code,
                'staff_schedules': staff_schedules,
            }
        
        context = {
            'admin': request.user,
            'export_type': 'week',
            'branch_filter': branch_filter,
            'start_date': week_start,
            'end_date': week_end,
            'branch_data': branch_data,
            'generated_at': timezone.now(),
        }
        
        if branch_filter == 'all':
            filename = f'schedule_all_branches_{week_start.isoformat()}_to_{week_end.isoformat()}.pdf'
        else:
            filename = f'schedule_{branch_filter}_{week_start.isoformat()}_to_{week_end.isoformat()}.pdf'
    
    else:  # month
        month_start = current_date.replace(day=1)
        days_in_month = monthrange(current_date.year, current_date.month)[1]
        month_end = month_start.replace(day=days_in_month)
        
        # Get schedules
        if branch_filter == 'all':
            schedules = Schedule.objects.filter(
                date__range=[month_start, month_end]
            ).select_related('staff').order_by('branch', 'staff__username', 'date')
            
            branches = User.objects.filter(
                is_active=True
            ).values_list('branch', flat=True).distinct()
        else:
            schedules = Schedule.objects.filter(
                branch=branch_filter,
                date__range=[month_start, month_end]
            ).select_related('staff').order_by('staff__username', 'date')
            
            branches = [branch_filter]
        
        # Organize by branch and staff
        branch_data = {}
        for branch_code in branches:
            branch_name = dict(User.BRANCH_CHOICES).get(branch_code, branch_code)
            branch_schedules = schedules.filter(branch=branch_code)
            
            staff_list = User.objects.filter(
                branch=branch_code,
                role__in=['staff', 'manager'],
                is_active=True
            ).order_by('username')
            
            staff_schedules = {}
            for staff in staff_list:
                staff_schedules[staff] = branch_schedules.filter(staff=staff)
            
            branch_data[branch_name] = {
                'code': branch_code,
                'staff_schedules': staff_schedules,
            }
        
        context = {
            'admin': request.user,
            'export_type': 'month',
            'branch_filter': branch_filter,
            'start_date': month_start,
            'end_date': month_end,
            'branch_data': branch_data,
            'generated_at': timezone.now(),
        }
        
        if branch_filter == 'all':
            filename = f'schedule_all_branches_{month_start.strftime("%Y-%m")}.pdf'
        else:
            filename = f'schedule_{branch_filter}_{month_start.strftime("%Y-%m")}.pdf'
    
    # Generate PDF
    return generate_pdf_response(
        'schedule/pdf/admin_schedule.html',
        context,
        filename
    )


def generate_pdf_response(template_path, context, filename):
    """
    Generate PDF from HTML template
    Uses WeasyPrint if available, otherwise returns HTML
    """
    
    # Render HTML
    html_string = render_to_string(template_path, context)
    
    if not WEASYPRINT_AVAILABLE:
        # If WeasyPrint not installed, return HTML for now
        # (Admin can install WeasyPrint later: pip install weasyprint)
        response = HttpResponse(html_string, content_type='text/html')
        messages.warning(
            None,
            'WeasyPrint not installed. Showing HTML preview. '
            'To generate PDF, run: pip install weasyprint'
        )
        return response
    
    # Generate PDF
    pdf_file = HTML(string=html_string).write_pdf()
    
    # Return PDF response
    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response


@login_required
def export_staff_pdf(request):
    # later you can generate a real PDF
    # for now: prevent NoReverseMatch and confirm endpoint works
    export_type = request.GET.get("type", "week")
    return HttpResponse(f"Export PDF placeholder (type={export_type})", content_type="text/plain")