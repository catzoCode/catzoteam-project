from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Avg, Count, Q
from django.contrib import messages
from django.utils import timezone
from datetime import date, timedelta
from decimal import Decimal
from calendar import monthrange

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
import json

from performance.models import DailyPoints, MonthlyIncentive
from task_management.models import TaskType, Task, TaskPackage
from accounts.models import User
from django.contrib.auth.hashers import make_password
from django.core.mail import send_mail
from django.conf import settings
import secrets
import string


@login_required
def dashboard_home(request):
    """Auto-redirect based on role"""
    if request.user.role == 'manager':
        return redirect('dashboard:manager_dashboard')
    elif request.user.role == 'admin':
        return redirect('dashboard:admin_dashboard')
    else:
        return redirect('dashboard:staff_dashboard')

    
@login_required
def staff_dashboard(request):
    """Staff dashboard showing daily/weekly/monthly progress with projections"""
    user = request.user
    today = date.today()
    
    # Get or create today's points
    today_points, created = DailyPoints.objects.get_or_create(
        user=user,
        date=today,
        defaults={'points': Decimal('0.00')}
    )
    
    # Calculate week stats
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    
    week_points = DailyPoints.objects.filter(
        user=user,
        date__range=[week_start, week_end]
    ).aggregate(
        total=Sum('points'),
        days_worked=Count('id')
    )
    
    week_total = week_points['total'] or Decimal('0.00')
    week_days_worked = week_points['days_worked'] or 0
    week_average = (week_total / week_days_worked) if week_days_worked > 0 else Decimal('0.00')
    week_target = Decimal('50.00') * 5
    
    # TODAY'S ASSIGNED TASKS
    today_tasks = Task.objects.filter(
        assigned_staff=user,
        status__in=['assigned', 'in_progress']
    ).select_related(
        'task_type',
        'package__cat',
        'package__cat__owner'
    ).order_by('-id')[:10]
    
    # UPCOMING TASKS
    upcoming_tasks = Task.objects.filter(
        assigned_staff=user,
        status__in=['assigned', 'pending']
    ).select_related(
        'task_type',
        'package__cat',
        'package__cat__owner'
    ).order_by('-id')[:5]
    
    # COMPLETED TASKS
    completed_tasks_today = Task.objects.filter(
        assigned_staff=user,
        completed_at__date=today,
        status='completed'
        
    ).select_related('task_type', 'package__cat').order_by('-completed_at')[:20]
    
    # PENDING APPROVAL
    pending_approval = Task.objects.filter(
        assigned_staff=user,
        status='submitted'
    ).select_related('task_type', 'package__cat').order_by('-id')[:5]
    
    # Task-based points today
    task_points_today = completed_tasks_today.aggregate(
        total=Sum('points')
    )['total'] or 0
    
    # Count tasks
    tasks_count = {
        'today': today_tasks.count(),
        'completed': completed_tasks_today.count(),
        'pending_approval': pending_approval.count(),
        'upcoming': upcoming_tasks.count(),
    }
    
    # Calculate month stats
    month_start = today.replace(day=1)
    days_in_month = monthrange(today.year, today.month)[1]
    
    month_points = DailyPoints.objects.filter(
        user=user,
        date__year=today.year,
        date__month=today.month
    ).aggregate(
        total=Sum('points'),
        average=Avg('points'),
        days_worked=Count('id')
    )
    
    month_total = month_points['total'] or Decimal('0.00')
    month_average = month_points['average'] or Decimal('0.00')
    month_days_worked = month_points['days_worked'] or 0
    
    # Projections
    days_elapsed = today.day
    days_remaining = days_in_month - today.day
    
    if month_days_worked > 0:
        daily_average = month_total / month_days_worked
        projected_total = daily_average * days_in_month
    else:
        daily_average = Decimal('0.00')
        projected_total = Decimal('0.00')
    
    # Calculate points needed
    monthly_target = Decimal('1200.00')
    points_needed = max(monthly_target - month_total, 0)
    
    if days_remaining > 0:
        daily_points_required = points_needed / days_remaining
    else:
        daily_points_required = Decimal('0.00')
    
    # Status checks
    on_track = projected_total >= monthly_target
    in_danger_zone = projected_total < Decimal('850.00')
    will_get_bonus = projected_total > monthly_target
    
    # Bonus calculation
    if will_get_bonus:
        bonus_amount = (projected_total - monthly_target) * Decimal('0.50')
    else:
        bonus_amount = Decimal('0.00')
    
    # Get monthly incentive
    monthly_incentive, created = MonthlyIncentive.objects.get_or_create(
        user=user,
        month=month_start,
        defaults={'total_points': month_total}
    )
    
    if not created:
        monthly_incentive.total_points = month_total
        monthly_incentive.calculate_incentive()
    
    # Task suggestions
    task_suggestions = get_task_suggestions(user, daily_points_required)
    
    context = {
        'user': user,
        'today': today,
        'today_points': today_points,
        'today_progress': (today_points.points / Decimal('50.00')) * 100 if today_points.points else 0,
        'today_points_needed': max(Decimal('50.00') - today_points.points, 0),
        'week_total': week_total,
        'week_target': week_target,
        'week_progress': (week_total / week_target * 100) if week_target > 0 else 0,
        'week_average': week_average,
        'week_days_worked': week_days_worked,
        'month_total': month_total,
        'month_average': month_average,
        'month_days_worked': month_days_worked,
        'monthly_target': monthly_target,
        'month_progress': (month_total / monthly_target * 100) if monthly_target > 0 else 0,
        'days_elapsed': days_elapsed,
        'days_remaining': days_remaining,
        'daily_average': daily_average,
        'projected_total': projected_total,
        'points_needed': points_needed,
        'daily_points_required': daily_points_required,
        'on_track': on_track,
        'in_danger_zone': in_danger_zone,
        'will_get_bonus': will_get_bonus,
        'bonus_amount': bonus_amount,
        'monthly_incentive': monthly_incentive,
        'task_suggestions': task_suggestions,
        'today_tasks': today_tasks,
        'upcoming_tasks': upcoming_tasks,
        'completed_tasks_today': completed_tasks_today,
        'pending_approval': pending_approval,
        'tasks_count': tasks_count,
        'task_points_today': task_points_today,
    }
    
    return render(request, 'dashboard/staff_dashboard.html', context)

def get_task_suggestions(user, daily_points_required):
    """Generate task suggestions to meet daily points requirement"""
    if daily_points_required <= 0:
        return []
    
    task_types = TaskType.objects.filter(is_active=True).order_by('-points')  
    
    suggestions = []
    for task in task_types[:5]:  
        count_needed = int(daily_points_required / task.points) + 1  
        total_points = count_needed * task.points  
        
        suggestions.append({
            'task_name': task.name,
            'points_per_task': task.points,  
            'count_needed': count_needed,
            'total_points': total_points,
        })
    
    return suggestions


@login_required
def manager_dashboard(request):
    """MANAGER DASHBOARD - PostgreSQL Optimized + Personal Progress"""
    if request.user.role != 'manager':
        messages.error(request, 'Access denied. Manager role required.')
        return redirect('dashboard:staff_dashboard')
    
    user = request.user
    today = date.today()
    
    # ============ MANAGER'S PERSONAL PROGRESS (Same as Staff) ============
    # Get or create today's points
    today_points, created = DailyPoints.objects.get_or_create(
        user=user,
        date=today,
        defaults={'points': Decimal('0.00')}
    )
    
    # Calculate week stats
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    
    week_points = DailyPoints.objects.filter(
        user=user,
        date__range=[week_start, week_end]
    ).aggregate(
        total=Sum('points'),
        days_worked=Count('id')
    )
    
    week_total = week_points['total'] or Decimal('0.00')
    week_days_worked = week_points['days_worked'] or 0
    week_average = (week_total / week_days_worked) if week_days_worked > 0 else Decimal('0.00')
    week_target = Decimal('50.00') * 5
    
    # Calculate month stats
    month_start = today.replace(day=1)
    days_in_month = monthrange(today.year, today.month)[1]
    
    month_points = DailyPoints.objects.filter(
        user=user,
        date__year=today.year,
        date__month=today.month
    ).aggregate(
        total=Sum('points'),
        average=Avg('points'),
        days_worked=Count('id')
    )
    
    month_total = month_points['total'] or Decimal('0.00')
    month_average = month_points['average'] or Decimal('0.00')
    month_days_worked = month_points['days_worked'] or 0
    
    # Projections
    days_elapsed = today.day
    days_remaining = days_in_month - today.day
    
    if month_days_worked > 0:
        daily_average = month_total / month_days_worked
        projected_total = daily_average * days_in_month
    else:
        daily_average = Decimal('0.00')
        projected_total = Decimal('0.00')
    
    # Calculate points needed
    monthly_target = Decimal('1200.00')
    points_needed = max(monthly_target - month_total, 0)
    
    if days_remaining > 0:
        daily_points_required = points_needed / days_remaining
    else:
        daily_points_required = Decimal('0.00')
    
    # Status checks
    on_track = projected_total >= monthly_target
    
    # Manager's tasks
    manager_tasks_today = Task.objects.filter(
        assigned_staff=user,
        status__in=['assigned', 'in_progress']
    ).select_related('task_type', 'package__cat').order_by('-id')[:10]
    
    manager_completed_today = Task.objects.filter(
        assigned_staff=user,
        completed_at__date=today,
        status='completed'
    ).select_related('task_type', 'package__cat').order_by('-completed_at')[:10]
    
    task_points_today = manager_completed_today.aggregate(
        total=Sum('points')
    )['total'] or 0
    
    # ============ TEAM MANAGEMENT DATA ============
    # PENDING TASK PACKAGES
    pending_packages = TaskPackage.objects.filter(
        status='pending'
    ).prefetch_related('tasks').order_by('-id')[:10]
    
    # ACTIVE TASK PACKAGES
    active_packages = TaskPackage.objects.filter(
        status__in=['assigned', 'in_progress']
    ).prefetch_related('tasks').order_by('-id')[:10]
    
    # TASKS PENDING APPROVAL
    pending_approval = Task.objects.filter(
        status='submitted'
    ).select_related('task_type', 'assigned_staff', 'package__cat').order_by('-id')[:15]
    
    # TODAY'S COMPLETED TASKS (TEAM)
    completed_today = Task.objects.filter(
        status='completed'
    ).select_related('task_type', 'assigned_staff', 'package__cat').order_by('-id')[:20]
    
    # STAFF AVAILABILITY
    staff_members_base = User.objects.filter(
        is_active=True,
        role='staff'
    ).order_by('username')
    
    staff_list = []
    available_count = 0
    busy_count = 0
    
    for staff in staff_members_base[:20]:
        pending = Task.objects.filter(
            assigned_staff=staff,
            status__in=['pending', 'assigned']
        ).count()
        
        completed = Task.objects.filter(
            assigned_staff=staff,
            status='completed'
        ).count()
        
        total = pending + completed
        
        completed_tasks = Task.objects.filter(
            assigned_staff=staff,
            status='completed'
        ).select_related('task_type')
        
        points = 0
        for t in completed_tasks:
            if hasattr(t, 'task_type') and hasattr(t.task_type, 'points'):
                points += t.task_type.points
        
        staff.pending_tasks = pending
        staff.completed_tasks = completed
        staff.total_tasks_count = total
        staff.points_value = points
        
        if staff.get_full_name():
            names = staff.get_full_name().split()
            staff.initials = ''.join([n[0].upper() for n in names[:2]])
        else:
            staff.initials = staff.username[0].upper()
        
        if pending <= 5:
            available_count += 1
        else:
            busy_count += 1
        
        staff_list.append(staff)
    
    # STATISTICS
    stats = {
        'pending_packages': pending_packages.count(),
        'active_packages': active_packages.count(),
        'pending_approval': pending_approval.count(),
        'completed_today': completed_today.count(),
        'total_points_today': sum(
            t.task_type.points if hasattr(t, 'task_type') and hasattr(t.task_type, 'points') else 0
            for t in completed_today
        ),
        'available_staff': available_count,
        'busy_staff': busy_count,
    }
    
    context = {
        # Team Management
        'pending_packages': pending_packages,
        'active_packages': active_packages,
        'pending_approval': pending_approval,
        'completed_today': completed_today,
        'staff_members': staff_list,
        'stats': stats,
        'today': today,
        
        # Manager's Personal Progress
        'user': user,
        'today_points': today_points,
        'today_progress': (today_points.points / Decimal('50.00')) * 100 if today_points.points else 0,
        'today_points_needed': max(Decimal('50.00') - today_points.points, 0),
        'week_total': week_total,
        'week_target': week_target,
        'week_progress': (week_total / week_target * 100) if week_target > 0 else 0,
        'week_average': week_average,
        'week_days_worked': week_days_worked,
        'month_total': month_total,
        'month_average': month_average,
        'month_days_worked': month_days_worked,
        'monthly_target': monthly_target,
        'month_progress': (month_total / monthly_target * 100) if monthly_target > 0 else 0,
        'days_elapsed': days_elapsed,
        'days_remaining': days_remaining,
        'daily_average': daily_average,
        'projected_total': projected_total,
        'points_needed': points_needed,
        'daily_points_required': daily_points_required,
        'on_track': on_track,
        'manager_tasks_today': manager_tasks_today,
        'manager_completed_today': manager_completed_today,
        'task_points_today': task_points_today,
        'tasks_count': {
            'today': manager_tasks_today.count(),
            'completed': manager_completed_today.count(),
        },
    }
    
    return render(request, 'dashboard/manager_dashboard.html', context)


@login_required
def assign_task_package(request, package_id):
    """MANAGER ONLY - Assign tasks to staff"""
    if request.user.role != 'manager':
        messages.error(request, 'Access denied. Manager role required.')
        return redirect('dashboard:staff_dashboard')
    
    package = get_object_or_404(TaskPackage, package_id=package_id)
    
    if request.method == 'POST':
        try:
            assigned_count = 0
            
            for task in package.tasks.all():
                staff_id = request.POST.get(f'task_{task.id}')
                if staff_id:
                    staff = User.objects.get(id=staff_id)
                    task.assigned_staff = staff
                    task.assigned_at = timezone.now()
                    task.status = 'assigned'
                    task.save()
                    assigned_count += 1
            
            if assigned_count > 0:
                package.status = 'assigned'
                package.save()
                
                messages.success(
                    request,
                    f'✅ Successfully assigned {assigned_count} tasks!'
                )
            else:
                messages.warning(request, 'No tasks were assigned.')
            
            return redirect('dashboard:manager_dashboard')
            
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
            return redirect('assign_tasks', package_id=package_id)
    
    tasks = package.tasks.all().select_related('task_type')
    staff_list = User.objects.filter(
        is_active=True,
        role__in=['staff', 'manager']
    ).annotate(
        active_tasks=Count(
            'tm_assigned_tasks',
            filter=Q(tm_assigned_tasks__status__in=['pending', 'assigned', 'in_progress'])
        ),
        is_current_manager=Count('id', filter=Q(id=request.user.id))
    ).order_by('-is_current_manager', 'active_tasks', 'username')

    context = {
        'package': package,
        'tasks': tasks,
        'staff_list': staff_list,
        'current_user': request.user,
    }

    return render(request, 'dashboard/assign_tasks.html', context)

@login_required
def approve_task(request, task_id):
    """MANAGER ONLY - Approve or reject completed task"""
    if request.user.role != 'manager':
        messages.error(request, 'Access denied. Manager role required.')
        return redirect('dashboard:staff_dashboard')
    
    task = get_object_or_404(Task, task_id=task_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'approve':
            task.status = 'completed'
            task.approved_by = request.user
            task.approved_at = timezone.now()
            task.save()
            
            award_points_to_staff(task)
            
            messages.success(
                request,
                f'✅ Task approved! {task.assigned_staff.username} earned {task.task_type.points} points.'
            )
        
        elif action == 'reject':
            task.status = 'assigned'
            rejection_reason = request.POST.get('rejection_reason', '')
            
            if task.notes:
                task.notes = f'{task.notes}\n\n[REJECTED]: {rejection_reason}'
            else:
                task.notes = f'[REJECTED]: {rejection_reason}'
            
            task.save()
            
            messages.warning(request, 'Task rejected and sent back to staff.')
        
        return redirect('dashboard:manager_dashboard')
    
    context = {'task': task}
    return render(request, 'dashboard/approve_task.html', context)


def award_points_to_staff(task):
    """Award points when task is approved"""
    from decimal import Decimal
    
    today = timezone.now().date()
    user = task.assigned_staff
    
    if hasattr(task, 'task_type') and hasattr(task.task_type, 'points'):
        points = Decimal(str(task.task_type.points))
    else:
        points = Decimal('0.00')
    
    daily_points, created = DailyPoints.objects.get_or_create(
        user=user,
        date=today,
        defaults={
            'points': Decimal('0.00'),
            'grooming_points': Decimal('0.00'),
            'service_points': Decimal('0.00'),
            'booking_points': Decimal('0.00'),
            'bonus_points': Decimal('0.00'),
        }
    )
    
    if hasattr(task.task_type, 'category'):
        category = task.task_type.category
        if category == 'grooming' and hasattr(daily_points, 'grooming_points'):
            daily_points.grooming_points += points
            if hasattr(daily_points, 'grooming_count'):
                daily_points.grooming_count += 1
        elif category == 'sales' and hasattr(daily_points, 'booking_points'):
            daily_points.booking_points += points
            if hasattr(daily_points, 'booking_count'):
                daily_points.booking_count += 1
        else:
            if hasattr(daily_points, 'service_points'):
                daily_points.service_points += points
            if hasattr(daily_points, 'cat_service_count'):
                daily_points.cat_service_count += 1
    
    total = Decimal('0.00')
    if hasattr(daily_points, 'grooming_points'):
        total += daily_points.grooming_points
    if hasattr(daily_points, 'service_points'):
        total += daily_points.service_points
    if hasattr(daily_points, 'booking_points'):
        total += daily_points.booking_points
    if hasattr(daily_points, 'bonus_points'):
        total += daily_points.bonus_points
    
    daily_points.points = total
    daily_points.save()
    
    from performance.models import MonthlyIncentive
    first_day = today.replace(day=1)
    monthly_incentive, created = MonthlyIncentive.objects.get_or_create(
        user=user,
        month=first_day,
        defaults={'total_points': Decimal('0.00')}
    )
    
    monthly_incentive.total_points += points
    
    if hasattr(monthly_incentive, 'calculate_incentive'):
        monthly_incentive.calculate_incentive()
    
    monthly_incentive.save()


@login_required
def admin_dashboard(request):
    if request.user.role != 'admin':
        messages.error(request, 'Access denied. Admin role required.')
        return redirect('dashboard:staff_dashboard')
    
    today = date.today()
    month_start = today.replace(day=1)
    days_in_month = monthrange(today.year, today.month)[1]
    
    staff_members = User.objects.filter(role='staff', is_active=True)
    
    branches = [
        'hq', 'damansara_perdana', 'wangsa_maju', 'shah_alam', 'bangi', 'cheng_melaka',
        'johor_bahru', 'seremban', 'seri_kembangan', 'usj21', 'ipoh'
    ]
    branch_stats = []
    
    total_on_track = 0
    total_needs_improvement = 0
    total_warning = 0
    
    for branch_code in branches:
        branch_staff = staff_members.filter(branch=branch_code)
        
        if branch_staff.exists():
            branch_points = DailyPoints.objects.filter(
                user__in=branch_staff,
                date__year=today.year,
                date__month=today.month
            ).aggregate(
                total=Sum('points'),
                average=Avg('points')
            )
            
            staff_count = branch_staff.count()
            total_points = branch_points['total'] or Decimal('0.00')
            avg_points = total_points / staff_count if staff_count > 0 else Decimal('0.00')
            
            on_track_count = 0
            needs_improvement_count = 0
            warning_count = 0
            
            for staff in branch_staff:
                staff_total = DailyPoints.objects.filter(
                    user=staff,
                    date__year=today.year,
                    date__month=today.month
                ).aggregate(total=Sum('points'))['total'] or Decimal('0.00')
                
                days_worked = DailyPoints.objects.filter(
                    user=staff,
                    date__year=today.year,
                    date__month=today.month
                ).count()
                
                if days_worked > 0:
                    daily_avg = staff_total / days_worked
                    projected = daily_avg * days_in_month
                    
                    if projected >= 1200:
                        on_track_count += 1
                    elif projected >= 850:
                        needs_improvement_count += 1
                    else:
                        warning_count += 1
            
            total_on_track += on_track_count
            total_needs_improvement += needs_improvement_count
            total_warning += warning_count
            
            branch_stats.append({
                'name': dict(User.BRANCH_CHOICES)[branch_code],
                'code': branch_code,
                'staff_count': staff_count,
                'total_points': total_points,
                'average_points': avg_points,
                'on_track_count': on_track_count,
                'needs_improvement_count': needs_improvement_count,
                'warning_count': warning_count,
            })
    
    staff_performance = []
    
    for staff in staff_members:
        month_data = DailyPoints.objects.filter(
            user=staff,
            date__year=today.year,
            date__month=today.month
        ).aggregate(
            total=Sum('points'),
            days_worked=Count('id')
        )
        
        total_points = month_data['total'] or Decimal('0.00')
        days_worked = month_data['days_worked'] or 0
        
        if days_worked > 0:
            daily_avg = total_points / days_worked
            projected_total = daily_avg * days_in_month
        else:
            daily_avg = Decimal('0.00')
            projected_total = Decimal('0.00')
        
        if projected_total >= 1200:
            status = 'on_track'
            status_label = 'On Track'
            status_class = 'success'
        elif projected_total >= 850:
            status = 'needs_improvement'
            status_label = 'Needs Improvement'
            status_class = 'warning'
        else:
            status = 'warning'
            status_label = 'Warning Zone'
            status_class = 'danger'
        
        staff_performance.append({
            'user': staff,
            'current_points': total_points,
            'projected_total': projected_total,
            'daily_average': daily_avg,
            'days_worked': days_worked,
            'status': status,
            'status_label': status_label,
            'status_class': status_class,
        })
    
    staff_performance.sort(key=lambda x: x['projected_total'], reverse=True)
    
    stats = {
        'on_track_count': total_on_track,
        'needs_improvement_count': total_needs_improvement,
        'warning_count': total_warning,
        'total_staff': staff_members.count(),
    }
    
    context = {
        'today': today,
        'branch_stats': branch_stats,
        'staff_performance': staff_performance,
        'total_staff': staff_members.count(),
        'stats': stats,
    }
    
    return render(request, 'dashboard/admin_dashboard.html', context)


@login_required
def projection_calculator(request):
    """Point projection calculator"""
    today = date.today()
    days_in_month = monthrange(today.year, today.month)[1]
    days_remaining = days_in_month - today.day + 1
    
    daily_target = 50
    monthly_target = 1200
    current_points = 0
    projection = None
    
    if request.method == 'POST':
        current_points = int(request.POST.get('current_points', 0))
        points_needed = monthly_target - current_points
        
        if days_remaining > 0:
            daily_needed = points_needed / days_remaining
        else:
            daily_needed = 0
        
        projection = {
            'current_points': current_points,
            'points_needed': points_needed,
            'daily_needed': round(daily_needed, 1),
            'will_reach': current_points + (daily_target * days_remaining),
            'days_remaining': days_remaining,
        }
    
    context = {
        'today': today,
        'days_remaining': days_remaining,
        'daily_target': daily_target,
        'monthly_target': monthly_target,
        'projection': projection,
    }
    
    return render(request, 'dashboard/projection_calculator.html', context)


@login_required
def admin_manage_tasks(request):
    """Admin page to manage all tasks"""
    if request.user.role != 'admin':
        messages.error(request, 'Access denied. Admin role required.')
        return redirect('dashboard:admin_dashboard')
    
    all_tasks = Task.objects.all().select_related(
        'package__cat',
        'package__cat__owner',
        'assigned_staff',
        'task_type'
    ).order_by('-scheduled_date')[:100]
    
    task_stats = Task.objects.aggregate(
        total=Count('id'),
        assigned=Count('id', filter=Q(status='assigned')),
        in_progress=Count('id', filter=Q(status='in_progress')),
        submitted=Count('id', filter=Q(status='submitted')),
        completed=Count('id', filter=Q(status='completed'))
    )
    
    branch_task_stats = Task.objects.values('assigned_staff__branch').annotate(
        count=Count('id')
    )
    
    context = {
        'all_tasks': all_tasks,
        'task_stats': task_stats,
        'branch_task_stats': branch_task_stats,
    }
    return render(request, 'dashboard/admin/manage_tasks.html', context)


@login_required
def admin_manage_staff_page(request):
    """Admin manages staff with search/filter"""
    if request.user.role != 'admin':
        messages.error(request, 'Access denied. Admin only.')
        return redirect('dashboard:admin_dashboard')
    
    search_query = request.GET.get('search', '').strip()
    role_filter = request.GET.get('role', 'all')
    branch_filter = request.GET.get('branch', 'all')
    status_filter = request.GET.get('status', 'all')
    
    staff = User.objects.all().order_by('-date_joined')
    
    if search_query:
        staff = staff.filter(
            Q(username__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(employee_id__icontains=search_query) |
            Q(phone_number__icontains=search_query)
        )
    
    if role_filter != 'all':
        staff = staff.filter(role=role_filter)
    
    if branch_filter != 'all':
        staff = staff.filter(branch=branch_filter)
    
    if status_filter == 'active':
        staff = staff.filter(is_active=True)
    elif status_filter == 'inactive':
        staff = staff.filter(is_active=False)
    
    stats = {
        'total': User.objects.count(),
        'active': User.objects.filter(is_active=True).count(),
        'inactive': User.objects.filter(is_active=False).count(),
        'staff_role': User.objects.filter(role='staff').count(),
        'managers': User.objects.filter(role='manager').count(),
        'admins': User.objects.filter(role='admin').count(),
    }
    
    from django.core.paginator import Paginator
    paginator = Paginator(staff, 50)
    page_number = request.GET.get('page')
    staff_page = paginator.get_page(page_number)
    
    context = {
        'staff_list': staff_page,
        'stats': stats,
        'search_query': search_query,
        'role_filter': role_filter,
        'branch_filter': branch_filter,
        'status_filter': status_filter,
        'branch_choices': User.BRANCH_CHOICES,
        'role_choices': User.ROLE_CHOICES,
    }
    return render(request, 'dashboard/admin/manage_staff.html', context)


@login_required
@require_http_methods(["POST"])
def ajax_create_staff(request):
    """AJAX: Create new staff member"""
    if request.user.role != 'admin':
        return JsonResponse({'success': False, 'error': 'Access denied'}, status=403)
    
    try:
        data = json.loads(request.body)
        
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        role = data.get('role')
        branch = data.get('branch')
        
        if not all([username, email, role, branch]):
            return JsonResponse({
                'success': False,
                'error': 'Username, email, role, and branch are required'
            }, status=400)
        
        if User.objects.filter(username=username).exists():
            return JsonResponse({
                'success': False,
                'error': 'Username already exists'
            }, status=400)
        
        if User.objects.filter(email=email).exists():
            return JsonResponse({
                'success': False,
                'error': 'Email already exists'
            }, status=400)
        
        today = date.today()
        prefix = f"EMP{today.strftime('%y')}"
        last_emp = User.objects.filter(
            employee_id__startswith=prefix
        ).order_by('employee_id').last()
        
        if last_emp and last_emp.employee_id:
            last_num = int(last_emp.employee_id[5:])
            new_num = last_num + 1
        else:
            new_num = 1
        
        employee_id = f"{prefix}{new_num:04d}"
        
        password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))

        user = User.objects.create(
            username=username,
            email=email,
            employee_id=employee_id,
            role=role,
            branch=branch,
            first_name=data.get('first_name', ''),
            last_name=data.get('last_name', ''),
            phone_number=data.get('phone', ''),
            is_active=True,
            is_staff=True if role == 'admin' else False,
        )

        user.set_password(password)
        user.save()
        
        from task_management.models import log_admin_action
        log_admin_action(
            user=request.user,
            action='create',
            model_type='user',
            object_id=employee_id,
            object_repr=f"User: {username}",
            changes={
                'username': username,
                'email': email,
                'role': role,
                'branch': branch
            },
            notes=f"Generated employee_id: {employee_id}",
            request=request
        )
        
        try:
            send_mail(
                subject='CatzoTeam Account Created',
                message=f'''
                    Hello {user.first_name or username},

                    Your CatzoTeam account has been created!

                    Username: {username}
                    Password: {password}
                    Employee ID: {employee_id}

                    Please change your password after first login.

                    Best regards,
                    CatzoTeam Admin
                    ''',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=True,
            )
        except:
            pass
        
        return JsonResponse({
            'success': True,
            'message': f'Staff created successfully!',
            'employee_id': employee_id,
            'password': password,
            'user': {
                'id': user.id,
                'username': username,
                'email': email,
                'employee_id': employee_id,
                'role': role,
                'branch': branch
            }
        })
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def ajax_update_staff(request, user_id):
    """AJAX: Update staff member"""
    if request.user.role != 'admin':
        return JsonResponse({'success': False, 'error': 'Access denied'}, status=403)
    
    try:
        user = get_object_or_404(User, id=user_id)
        data = json.loads(request.body)
        
        old_values = {
            'role': user.role,
            'branch': user.branch,
            'is_active': user.is_active,
            'email': user.email
        }
        
        if 'first_name' in data:
            user.first_name = data['first_name'].strip()
        if 'last_name' in data:
            user.last_name = data['last_name'].strip()
        if 'email' in data:
            email = data['email'].strip()
            if User.objects.filter(email=email).exclude(id=user_id).exists():
                return JsonResponse({
                    'success': False,
                    'error': 'Email already in use'
                }, status=400)
            user.email = email
        
        if 'phone' in data:
            user.phone_number = data['phone'].strip() 
        if 'role' in data:
            user.role = data['role']
            user.is_staff = True if data['role'] == 'admin' else False
        if 'branch' in data:
            user.branch = data['branch']
        if 'is_active' in data:
            user.is_active = data['is_active']
        
        user.save()
        
        from task_management.models import log_admin_action
        log_admin_action(
            user=request.user,
            action='update',
            model_type='user',
            object_id=user.employee_id,
            object_repr=f"User: {user.username}",
            changes={'old': old_values, 'new': data},
            request=request
        )
        
        return JsonResponse({'success': True, 'message': 'Staff updated successfully'})
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def ajax_soft_delete_staff(request, user_id):
    """AJAX: Soft delete (deactivate) staff"""
    if request.user.role != 'admin':
        return JsonResponse({'success': False, 'error': 'Access denied'}, status=403)
    
    try:
        user = get_object_or_404(User, id=user_id)
        
        if user.id == request.user.id:
            return JsonResponse({
                'success': False,
                'error': 'Cannot deactivate your own account'
            }, status=400)
        
        user.is_active = False
        user.save()
        
        from task_management.models import log_admin_action
        log_admin_action(
            user=request.user,
            action='deactivate',
            model_type='user',
            object_id=user.employee_id,
            object_repr=f"User: {user.username}",
            request=request
        )
        
        return JsonResponse({'success': True, 'message': f'{user.username} deactivated'})
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def ajax_activate_staff(request, user_id):
    """AJAX: Reactivate staff"""
    if request.user.role != 'admin':
        return JsonResponse({'success': False, 'error': 'Access denied'}, status=403)
    
    try:
        user = get_object_or_404(User, id=user_id)
        
        user.is_active = True
        user.save()
        
        from task_management.models import log_admin_action
        log_admin_action(
            user=request.user,
            action='activate',
            model_type='user',
            object_id=user.employee_id,
            object_repr=f"User: {user.username}",
            request=request
        )
        
        return JsonResponse({'success': True, 'message': f'{user.username} activated'})
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def ajax_reset_staff_password(request, user_id):
    """AJAX: Reset staff password"""
    if request.user.role != 'admin':
        return JsonResponse({'success': False, 'error': 'Access denied'}, status=403)
    
    try:
        user = get_object_or_404(User, id=user_id)
        
        new_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))
        
        user.password = make_password(new_password)
        user.save()
        
        from task_management.models import log_admin_action
        log_admin_action(
            user=request.user,
            action='password_reset',
            model_type='user',
            object_id=user.employee_id,
            object_repr=f"User: {user.username}",
            request=request
        )
        
        try:
            send_mail(
                subject='CatzoTeam Password Reset',
                message=f'''
Hello {user.first_name or user.username},

Your password has been reset by an administrator.

New Password: {new_password}

Please change your password after login.

Best regards,
CatzoTeam Admin
''',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=True,
            )
        except:
            pass
        
        return JsonResponse({
            'success': True,
            'message': 'Password reset successfully',
            'new_password': new_password
        })
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def ajax_staff_performance(request, user_id):
    """AJAX: Get staff performance/points history"""
    if request.user.role != 'admin':
        return JsonResponse({'success': False, 'error': 'Access denied'}, status=403)
    
    try:
        user = get_object_or_404(User, id=user_id)
        
        from performance.models import DailyPoints, MonthlyIncentive
        from task_management.models import Task
        
        thirty_days_ago = date.today() - timedelta(days=30)
        daily_points = DailyPoints.objects.filter(
            user=user,
            date__gte=thirty_days_ago
        ).order_by('-date')[:30]
        
        first_day = date.today().replace(day=1)
        monthly = MonthlyIncentive.objects.filter(
            user=user,
            month=first_day
        ).first()
        
        task_stats = {
            'total': Task.objects.filter(assigned_staff=user).count(),
            'completed': Task.objects.filter(assigned_staff=user, status='completed').count(),
            'in_progress': Task.objects.filter(assigned_staff=user, status='in_progress').count(),
            'pending': Task.objects.filter(assigned_staff=user, status='assigned').count(),
        }
        
        points_data = {
            'dates': [dp.date.strftime('%Y-%m-%d') for dp in daily_points],
            'points': [float(dp.points) for dp in daily_points],
        }
        
        return JsonResponse({
            'success': True,
            'performance': {
                'task_stats': task_stats,
                'monthly_points': float(monthly.total_points) if monthly else 0,
                'daily_points': points_data,
                'total_incentive': float(monthly.total_incentive) if monthly and hasattr(monthly, 'total_incentive') else 0,
            }
        })
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def ajax_reassign_tasks(request, user_id):
    """AJAX: Reassign all tasks from one staff to another"""
    if request.user.role != 'admin':
        return JsonResponse({'success': False, 'error': 'Access denied'}, status=403)
    
    try:
        from_user = get_object_or_404(User, id=user_id)
        data = json.loads(request.body)
        to_user_id = data.get('to_user_id')
        
        if not to_user_id:
            return JsonResponse({
                'success': False,
                'error': 'Target staff member required'
            }, status=400)
        
        to_user = get_object_or_404(User, id=to_user_id)
        
        tasks_to_reassign = Task.objects.filter(
            assigned_staff=from_user,
            status__in=['assigned', 'in_progress']
        )
        
        count = tasks_to_reassign.count()
        tasks_to_reassign.update(assigned_staff=to_user)
        
        from task_management.models import log_admin_action
        log_admin_action(
            user=request.user,
            action='task_reassign',
            model_type='task',
            object_id=f"{from_user.employee_id}_to_{to_user.employee_id}",
            object_repr=f"Reassigned {count} tasks",
            changes={
                'from': from_user.username,
                'to': to_user.username,
                'count': count
            },
            request=request
        )
        
        return JsonResponse({
            'success': True,
            'message': f'{count} tasks reassigned from {from_user.username} to {to_user.username}'
        })
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)