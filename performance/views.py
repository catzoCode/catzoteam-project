# performance/views.py - COMPLETE FIXED VERSION
# NO cat_hotel imports - removed CatBooking dependency

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum
from datetime import date
from calendar import monthrange
from decimal import Decimal
from .models import DailyPoints, MonthlyIncentive
from accounts.models import User

@login_required
def my_points_view(request):
    """Staff view for their own points"""
    user = request.user
    today = date.today()
    
    # Get current month dates
    month_start = today.replace(day=1)
    days_in_month = monthrange(today.year, today.month)[1]
    month_end = today.replace(day=days_in_month)
    
    # Get all points for current month
    points = DailyPoints.objects.filter(
        user=user,
        date__range=[month_start, month_end]
    ).order_by('-date')
    
    # Calculate totals
    total_points = points.aggregate(total=Sum('points'))['total'] or 0
    days_worked = points.count()
    
    # Get today's points
    today_points = DailyPoints.objects.filter(
        user=user,
        date=today
    ).first()
    
    context = {
        'points': points,
        'total_points': total_points,
        'days_worked': days_worked,
        'today_points': today_points,
        'month_start': month_start,
        'month_end': month_end,
    }
    
    return render(request, 'performance/my_points.html', context)


@login_required
def my_incentives_view(request):
    """Staff view for their incentives"""
    user = request.user
    
    # Get all incentives
    incentives = MonthlyIncentive.objects.filter(
        user=user
    ).order_by('-month')
    
    # Get current month incentive
    today = date.today()
    current_incentive = MonthlyIncentive.objects.filter(
        user=user,
        month__year=today.year,
        month__month=today.month
    ).first()
    
    context = {
        'incentives': incentives,
        'current_incentive': current_incentive,
    }
    
    return render(request, 'performance/my_incentives.html', context)


@login_required
def projection_calculator(request):
    """Point projection calculator with multiple scenarios"""
    user = request.user
    today = date.today()
    
    # Get current month data
    month_start = today.replace(day=1)
    days_in_month = monthrange(today.year, today.month)[1]
    days_remaining = days_in_month - today.day + 1
    
    # Get current month's total points
    current_total = DailyPoints.objects.filter(
        user=user,
        date__year=today.year,
        date__month=today.month
    ).aggregate(total=Sum('points'))['total'] or Decimal('0')
    
    # Handle custom average input
    custom_average = request.GET.get('average', '')
    
    # Define scenarios to calculate
    scenario_averages = [30, 35, 40, 45, 50, 55, 60]
    
    # Add custom average if provided
    if custom_average:
        try:
            custom_avg = Decimal(custom_average)
            if custom_avg > 0 and custom_avg <= 100:
                scenario_averages.append(float(custom_avg))
                scenario_averages = sorted(set(scenario_averages))
        except (ValueError, TypeError):
            pass
    
    scenarios = []
    for avg in scenario_averages:
        avg_decimal = Decimal(str(avg))
        projected_total = current_total + (avg_decimal * days_remaining)
        
        # Calculate bonus
        bonus = Decimal('0')
        if projected_total >= 1200:
            excess = projected_total - 1200
            bonus = excess * Decimal('0.50')
        
        # Determine status and message
        if projected_total >= 1200:
            status = 'success'
            message = '✓ Target Reached!'
        elif projected_total >= 850:
            status = 'warning'
            message = '⚠ Safe Zone'
        else:
            status = 'danger'
            message = '✗ Warning Zone'
        
        scenarios.append({
            'average': avg,
            'projected_total': projected_total,
            'bonus': bonus,
            'status': status,
            'message': message
        })
    
    context = {
        'current_total': current_total,
        'days_remaining': days_remaining,
        'scenarios': scenarios,
        'custom_average': custom_average,
    }
    
    return render(request, 'performance/projection_calculator.html', context)


@login_required
def record_points(request):
    """
    Staff records completed tasks for today
    FIXED: Removed CatBooking dependency - staff manually enters counts
    """
    user = request.user
    today = date.today()
    
    # Get or create today's points
    daily_points, created = DailyPoints.objects.get_or_create(
        user=user,
        date=today,
        defaults={
            'grooming_count': 0,
            'cat_service_count': 0,
            'booking_count': 0,
            'grooming_points': 0,
            'service_points': 0,
            'booking_points': 0,
            'points': 0,
        }
    )
    
    if request.method == 'POST':
        # Get counts from form
        grooming_count = int(request.POST.get('grooming_count', 0))
        service_count = int(request.POST.get('service_count', 0))
        booking_count = int(request.POST.get('booking_count', 0))
        
        # Calculate individual points
        grooming_points = grooming_count * 20
        service_points = service_count * 15
        booking_points = booking_count * 15
        
        # Update counts
        daily_points.grooming_count = grooming_count
        daily_points.cat_service_count = service_count
        daily_points.booking_count = booking_count
        
        # Update individual points
        daily_points.grooming_points = grooming_points
        daily_points.service_points = service_points
        daily_points.booking_points = booking_points
        
        # Calculate total points
        daily_points.points = grooming_points + service_points + booking_points
        
        daily_points.save()
        
        messages.success(request, f'Points recorded! Total today: {daily_points.points} points')
        return redirect('record_points')
    
    context = {
        'daily_points': daily_points,
        'today': today,
    }
    
    return render(request, 'performance/record_points.html', context)


@login_required
def points_history(request):
    """View points history for current month"""
    user = request.user
    today = date.today()
    
    # Get current month points
    month_start = today.replace(day=1)
    
    points = DailyPoints.objects.filter(
        user=user,
        date__gte=month_start
    ).order_by('-date')
    
    # Calculate totals
    total_points = sum(p.points for p in points)
    total_grooming = sum(p.grooming_count for p in points)
    total_services = sum(p.cat_service_count for p in points)
    total_bookings = sum(p.booking_count for p in points)
    
    context = {
        'points': points,
        'total_points': total_points,
        'total_grooming': total_grooming,
        'total_services': total_services,
        'total_bookings': total_bookings,
    }
    
    return render(request, 'performance/points_history.html', context)