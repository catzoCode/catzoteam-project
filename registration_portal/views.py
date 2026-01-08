# registration_portal/views.py
# COMPLETE VERSION with PendingBooking System + OCR + Combo Packages

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from django.http import JsonResponse
from datetime import date, datetime
from django.db import transaction
from decimal import Decimal
import json
import re

from django.db import transaction, IntegrityError
from .models import Customer, Cat, RegistrationSession
from task_management.models import (
    Customer, Cat, TaskGroup, TaskType, 
    TaskPackage, Task, ComboPackageOwnership, PendingBooking
)
from accounts.models import User
from .models import RegistrationSession

# ============================================
# LOGIN/LOGOUT
# ============================================

def registration_login(request):
    """Simple login with employee ID only"""
    if request.method == 'POST':
        employee_id = request.POST.get('employee_id', '').strip()
        
        if not employee_id:
            messages.error(request, 'Please enter your Employee ID')
            return redirect('registration_portal:login')
        
        try:
            user = User.objects.get(employee_id=employee_id, is_active=True)
            
            session = RegistrationSession.objects.create(
                user=user,
                is_active=True
            )
            
            request.session['registration_user_id'] = user.id
            request.session['registration_session_id'] = session.id
            
            messages.success(request, f'Welcome {user.first_name or user.username}!')
            return redirect('registration_portal:dashboard')
        
        except User.DoesNotExist:
            messages.error(request, f'Invalid Employee ID: {employee_id}')
            return redirect('registration_portal:login')
    
    if request.session.get('registration_user_id'):
        return redirect('registration_portal:dashboard')
    
    return render(request, 'registration_portal/login.html')


def registration_logout(request):
    """Logout from registration portal"""
    session_id = request.session.get('registration_session_id')
    
    if session_id:
        try:
            session = RegistrationSession.objects.get(id=session_id)
            session.end_session()
        except RegistrationSession.DoesNotExist:
            pass
    
    # Clear cart session to prevent errors
    request.session.pop('apple_cart', None)
    request.session.pop('registration_user_id', None)
    request.session.pop('registration_session_id', None)
    
    messages.success(request, 'Logged out successfully')
    return redirect('registration_portal:login')


# ============================================
# AUTHENTICATION DECORATOR
# ============================================

def registration_login_required(view_func):
    """Custom decorator for registration portal authentication"""
    def wrapper(request, *args, **kwargs):
        user_id = request.session.get('registration_user_id')
        
        if not user_id:
            messages.warning(request, 'Please login first')
            return redirect('registration_portal:login')
        
        try:
            request.registration_user = User.objects.get(id=user_id, is_active=True)
            request.user = request.registration_user
            return view_func(request, *args, **kwargs)
        except User.DoesNotExist:
            request.session.pop('registration_user_id', None)
            messages.error(request, 'Session expired. Please login again.')
            return redirect('registration_portal:login')
    
    return wrapper


# ============================================
# DASHBOARD
# ============================================

@registration_login_required
def dashboard(request):
    """Dashboard with statistics"""
    
    today = timezone.now().date()
    
    today_customers = Customer.objects.filter(created_at__date=today).count()
    today_cats = Cat.objects.filter(registration_date=today).count()
    today_packages = TaskPackage.objects.filter(created_at__date=today, status='pending').count()
    
    # Pending bookings count
    pending_bookings_count = PendingBooking.objects.filter(
        status='pending_payment',
        created_by=request.registration_user
    ).count()
    
    session_id = request.session.get('registration_session_id')
    session_stats = {
        'customers_registered': 0,
        'cats_registered': 0,
        'service_requests_created': 0,
    }
    
    if session_id:
        try:
            session = RegistrationSession.objects.get(id=session_id)
            session_stats = {
                'customers_registered': session.customers_registered,
                'cats_registered': session.cats_registered,
                'service_requests_created': session.service_requests_created,
            }
        except RegistrationSession.DoesNotExist:
            pass
    
    recent_customers = Customer.objects.all().order_by('-created_at')[:5]
    
    recent_packages = TaskPackage.objects.filter(
        status='pending'
    ).select_related(
        'cat', 
        'cat__owner', 
        'created_by'
    ).prefetch_related(
        'tasks'
    ).order_by('-created_at')[:5]
    
    context = {
        'user': request.registration_user,
        'today': today,
        'today_customers': today_customers,
        'today_cats': today_cats,
        'today_requests': today_packages,
        'pending_bookings_count': pending_bookings_count,
        'session': session_stats,
        'recent_customers': recent_customers,
        'recent_requests': recent_packages,
    }
    
    return render(request, 'registration_portal/dashboard.html', context)


# ============================================
# CUSTOMER SEARCH
# ============================================

@registration_login_required
def customer_search(request):
    """Advanced customer search"""
    customers = []
    search_performed = False
    
    if request.method == 'POST' or request.GET.get('search'):
        search_performed = True
        
        search_query = request.POST.get('search_query', '') or request.GET.get('search_query', '')
        search_phone = request.POST.get('search_phone', '') or request.GET.get('search_phone', '')
        
        query = Q()
        
        if search_query:
            query |= Q(name__icontains=search_query)
            query |= Q(customer_id__icontains=search_query)
        
        if search_phone:
            query &= Q(phone__icontains=search_phone)
        
        if query:
            customers = Customer.objects.filter(query).order_by('-created_at')
    
    context = {
        'user': request.registration_user,
        'customers': customers,
        'search_performed': search_performed,
    }
    
    return render(request, 'registration_portal/customer_search.html', context)


# ============================================
# REGISTER CUSTOMER
# ============================================

@registration_login_required
def register_customer(request):
    """Register new customer"""
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        phone = request.POST.get('phone', '').strip()
        email = request.POST.get('email', '').strip()
        ic_number = request.POST.get('ic_number', '').strip()
        address = request.POST.get('address', '').strip()
        emergency_contact = request.POST.get('emergency_contact', '').strip()
        
        if not name or not phone:
            messages.error(request, 'Name and Phone are required')
            return redirect('registration_portal:register_customer')
        
        if Customer.objects.filter(phone=phone).exists():
            messages.error(request, f'Customer with phone {phone} already exists')
            return redirect('registration_portal:customer_search')
        
        if ic_number and Customer.objects.filter(ic_number=ic_number).exists():
            messages.error(request, f'Customer with IC {ic_number} already exists')
            return redirect('registration_portal:customer_search')
        
        try:
            customer = Customer.objects.create(
                name=name,
                phone=phone,
                email=email,
                ic_number=ic_number,
                address=address,
                emergency_contact=emergency_contact,
                registered_by=request.registration_user
            )
            
            session_id = request.session.get('registration_session_id')
            if session_id:
                try:
                    session = RegistrationSession.objects.get(id=session_id)
                    session.customers_registered += 1
                    session.save()
                except RegistrationSession.DoesNotExist:
                    pass
            
            messages.success(request, f'✅ Customer {customer.customer_id} registered successfully!')
            return redirect('registration_portal:register_cat', customer_id=customer.customer_id)
        
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
            return redirect('registration_portal:register_customer')
    
    context = {
        'user': request.registration_user,
    }
    
    return render(request, 'registration_portal/register_customer.html', context)


# ============================================
# REGISTER CAT
# ============================================

@registration_login_required
def register_cat(request, customer_id):
    """Register cat for customer"""
    customer = get_object_or_404(Customer, customer_id=customer_id)
    
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        breed = request.POST.get('breed', 'mixed')
        age = request.POST.get('age', 0)
        gender = request.POST.get('gender', 'male')
        color = request.POST.get('color', '').strip()
        weight = request.POST.get('weight', 0) or None
        vaccination_status = request.POST.get('vaccination_status', 'unknown')
        medical_notes = request.POST.get('medical_notes', '').strip()
        special_requirements = request.POST.get('special_requirements', '').strip()
        photo = request.FILES.get('photo')
        
        if not name:
            messages.error(request, 'Cat name is required')
            return redirect('registration_portal:register_cat', customer_id=customer_id)
        
        try:
            cat = Cat.objects.create(
                name=name,
                owner=customer,
                breed=breed,
                age=int(age),
                gender=gender,
                color=color,
                weight=weight,
                vaccination_status=vaccination_status,
                medical_notes=medical_notes,
                special_requirements=special_requirements,
                photo=photo,
                registered_by=request.registration_user
            )
            
            session_id = request.session.get('registration_session_id')
            if session_id:
                try:
                    session = RegistrationSession.objects.get(id=session_id)
                    session.cats_registered += 1
                    session.save()
                except RegistrationSession.DoesNotExist:
                    pass
            
            messages.success(request, f'✅ Cat {cat.cat_id} - {cat.name} registered successfully!')
            
            action = request.POST.get('action', 'another')
            
            if action == 'service':
                return redirect('registration_portal:create_service_request', customer_id=customer_id)
            else:
                return redirect('registration_portal:register_cat', customer_id=customer_id)
        
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
            return redirect('registration_portal:register_cat', customer_id=customer_id)
    
    cats = customer.cats.filter(is_active=True).order_by('-registration_date')
    
    context = {
        'user': request.registration_user,
        'customer': customer,
        'cats': cats,
    }
    
    return render(request, 'registration_portal/register_cat.html', context)


# ============================================
# CREATE SERVICE REQUEST - WITH PENDING BOOKING
# ============================================

@registration_login_required
def create_service_request(request, customer_id=None):
    """
    Create service request - FIXED LOGIC:
    - NO payment proof → Create PendingBooking (appears in pending page)
    - WITH payment proof → Create TaskPackage + Award points immediately
    """
    
    if request.method == 'POST':
        post_customer_id = request.POST.get('customer_id')
        cat_ids = request.POST.getlist('cat_ids')
        selected_tasks = request.POST.getlist('selected_tasks')
        notes = request.POST.get('notes', '')
        preferred_date = request.POST.get('preferred_date')
        preferred_time = request.POST.get('preferred_time')
        payment_proof = request.FILES.get('payment_proof')  # KEY: Check if uploaded
        use_combo_id = request.POST.get('use_combo_package')
        
        try:
            with transaction.atomic():
                customer = Customer.objects.get(customer_id=post_customer_id)
                cats = Cat.objects.filter(cat_id__in=cat_ids)
                
                if not cats.exists():
                    messages.error(request, 'Please select at least one cat.')
                    return redirect('registration_portal:create_service_request', customer_id=post_customer_id)
                
                if not selected_tasks and not use_combo_id:
                    messages.error(request, 'Please select at least one service.')
                    return redirect('registration_portal:create_service_request', customer_id=post_customer_id)
                
                # ============ USING EXISTING COMBO ============
                if use_combo_id:
                    combo_ownership = ComboPackageOwnership.objects.get(
                        ownership_id=use_combo_id,
                        is_active=True
                    )
                    
                    if combo_ownership.sessions_remaining <= 0:
                        messages.error(request, f'❌ Combo package has no sessions remaining!')
                        return redirect('registration_portal:create_service_request', customer_id=post_customer_id)
                    
                    # Create TaskPackage for combo usage (no points)
                    task_package = TaskPackage.objects.create(
                        cat=combo_ownership.cat,
                        created_by=request.registration_user,
                        status='pending',
                        notes=f'Combo session {combo_ownership.sessions_used + 1}/{combo_ownership.total_sessions}',
                        branch=request.registration_user.branch,
                        booking_type='type_b',
                        is_combo_package=True,
                        combo_session_number=combo_ownership.sessions_used + 1,
                        combo_total_sessions=combo_ownership.total_sessions,
                        scheduled_date=preferred_date if preferred_date else timezone.now().date(),
                        arrival_status='pending',
                        points_awarded=False,
                        total_points=0,
                    )
                    
                    combo_ownership.use_session()
                    
                    messages.success(
                        request,
                        f'✅ Combo session used! {combo_ownership.sessions_remaining} sessions remaining'
                    )
                
                # ============ NEW BOOKING - KEY DECISION POINT ============
                else:
                    for cat in cats:
                        task_types = TaskType.objects.filter(id__in=selected_tasks)
                        package_points = sum(tt.points for tt in task_types)
                        
                        is_combo_front = any('Combo Front' in tt.name for tt in task_types)
                        
                        # ========================================
                        # FIXED LOGIC: Check payment_proof first
                        # ========================================
                        
                        if payment_proof:
                            # ✅ HAS PAYMENT PROOF → Create TaskPackage + Award Points NOW
                            
                            task_package = TaskPackage.objects.create(
                                cat=cat,
                                created_by=request.registration_user,
                                status='pending',
                                notes=notes or f'Service request for {cat.name}',
                                branch=request.registration_user.branch,
                                booking_type='type_a',  # Type A: Got proof
                                payment_proof=payment_proof,
                                scheduled_date=preferred_date if preferred_date else timezone.now().date(),
                                arrival_status='arrived',  # Already confirmed
                                points_awarded=False,  # Will be set to True below
                                total_points=package_points,
                            )
                            
                            # Create tasks
                            for task_type in task_types:
                                Task.objects.create(
                                    package=task_package,
                                    task_type=task_type,
                                    points=task_type.points,
                                    scheduled_date=preferred_date if preferred_date else timezone.now().date(),
                                    scheduled_time=preferred_time if preferred_time else '09:00',
                                    status='pending',
                                )
                            
                            # ✅ AWARD POINTS IMMEDIATELY
                            success = task_package.award_points_immediately()
                            
                            if success:
                                # Handle combo ownership
                                if is_combo_front:
                                    combo_front_task = next((tt for tt in task_types if 'Combo Front' in tt.name), None)
                                    match = re.search(r'(\d+)', combo_front_task.name)
                                    total_sessions = int(match.group(1)) if match else 4
                                    
                                    ComboPackageOwnership.objects.create(
                                        customer=customer,
                                        cat=cat,
                                        combo_task_type=combo_front_task,
                                        total_sessions=total_sessions,
                                        sessions_used=0,
                                        sessions_remaining=total_sessions,
                                        points_awarded=package_points,
                                        awarded_to=request.registration_user,
                                        awarded_at=timezone.now(),
                                        purchase_package=task_package,
                                        is_active=True,
                                    )
                                    
                                    messages.success(
                                        request,
                                        f'🎉 {task_package.package_id}: Combo sold! You got {package_points} points NOW!'
                                    )
                                else:
                                    messages.success(
                                        request,
                                        f'✅ {task_package.package_id}: Payment confirmed! You got {package_points} points NOW!'
                                    )
                            else:
                                messages.warning(
                                    request,
                                    f'⚠️ {task_package.package_id} created but points not awarded'
                                )
                        
                        else:
                            # ❌ NO PAYMENT PROOF → Create PendingBooking
                            # This will appear on the pending bookings page
                            
                            pending_booking = PendingBooking.objects.create(
                                customer=customer,
                                cat=cat,
                                scheduled_date=preferred_date if preferred_date else timezone.now().date(),
                                scheduled_time=preferred_time if preferred_time else '09:00',
                                notes=notes or f'Pending booking for {cat.name}',
                                created_by=request.registration_user,
                                branch=request.registration_user.branch,
                                status='pending_payment',
                            )
                            
                            # Store tasks as JSON
                            pending_booking.set_selected_tasks(task_types)
                            pending_booking.save()
                            
                            messages.warning(
                                request,
                                f'⏸️ {pending_booking.booking_id}: Pending booking created! '
                                f'Customer must pay when they arrive. '
                                f'You will get 2 POINTS when customer arrives and payment is confirmed. '
                                f'(Task completion points awarded separately when work is done)'
                            )
                
                # Update session stats
                session_id = request.session.get('registration_session_id')
                if session_id:
                    try:
                        session = RegistrationSession.objects.get(id=session_id)
                        session.service_requests_created += 1
                        session.save()
                    except RegistrationSession.DoesNotExist:
                        pass
                
                return redirect('registration_portal:dashboard')
                
        except Customer.DoesNotExist:
            messages.error(request, 'Customer not found')
            return redirect('registration_portal:customer_search')
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
            import traceback
            print(traceback.format_exc())
            return redirect('registration_portal:customer_search')
    
    # GET request - same as before
    if not customer_id:
        customer_id = request.GET.get('customer_id')
    
    customer = None
    cats = []
    owned_combos = []
    
    if customer_id:
        try:
            customer = Customer.objects.get(customer_id=customer_id)
            cats = customer.cats.filter(is_active=True)
            
            owned_combos = ComboPackageOwnership.objects.filter(
                customer=customer,
                is_active=True,
                sessions_remaining__gt=0
            ).select_related('combo_task_type', 'cat')
            
        except Customer.DoesNotExist:
            messages.error(request, 'Customer not found')
            return redirect('registration_portal:customer_search')
    
    # Get task groups
    task_groups = TaskGroup.objects.filter(is_active=True).prefetch_related('task_types')
    task_groups = task_groups.exclude(name__icontains='Other')
    
    grooming_groups = task_groups.filter(name__icontains='Grooming')
    sales_groups = task_groups.filter(Q(name__icontains='Sales') | Q(name__icontains='Combo'))
    product_groups = task_groups.filter(name__icontains='Product')
    other_groups = task_groups.exclude(
        name__icontains='Grooming'
    ).exclude(
        Q(name__icontains='Sales') | Q(name__icontains='Combo')
    ).exclude(
        name__icontains='Product'
    )
    
    context = {
        'user': request.registration_user,
        'customer': customer,
        'cats': cats,
        'owned_combos': owned_combos,
        'grooming_groups': grooming_groups,
        'sales_groups': sales_groups,
        'product_groups': product_groups,
        'other_groups': other_groups,
        'today': datetime.now().date()
    }
    
    return render(request, 'registration_portal/create_service_request.html', context)


# ============================================
# CUSTOMER DETAIL
# ============================================

@registration_login_required
def customer_detail(request, customer_id):
    """View customer details"""
    customer = get_object_or_404(Customer, customer_id=customer_id)
    cats = customer.cats.filter(is_active=True)
    
    recent_packages = TaskPackage.objects.filter(
        cat__owner=customer
    ).select_related('cat', 'created_by').prefetch_related('tasks').order_by('-created_at')[:10]
    
    owned_combos = ComboPackageOwnership.objects.filter(
        customer=customer
    ).select_related('combo_task_type', 'cat', 'awarded_to').order_by('-purchased_at')
    
    context = {
        'user': request.registration_user,
        'customer': customer,
        'cats': cats,
        'recent_packages': recent_packages,
        'owned_combos': owned_combos,
    }
    
    return render(request, 'registration_portal/customer_detail.html', context)


# ============================================
# PENDING BOOKINGS
# ============================================

@registration_login_required
def pending_bookings(request):
    """View all pending bookings"""
    
    user = request.registration_user
    today = timezone.now().date()
    
    if user.role in ['manager', 'admin']:
        bookings = PendingBooking.objects.filter(
            branch=user.branch,
            status='pending_payment'
        )
    else:
        bookings = PendingBooking.objects.filter(
            created_by=user,
            status='pending_payment'
        )
    
    todays_bookings = bookings.filter(scheduled_date=today)
    upcoming_bookings = bookings.filter(scheduled_date__gt=today)
    overdue_bookings = bookings.filter(scheduled_date__lt=today)
    
    context = {
        'user': user,
        'today': today,
        'todays_bookings': todays_bookings,
        'upcoming_bookings': upcoming_bookings,
        'overdue_bookings': overdue_bookings,
        'total_pending': bookings.count(),
    }
    
    return render(request, 'registration_portal/pending_bookings.html', context)


@registration_login_required
def cancel_pending_booking(request, booking_id):
    """Cancel pending booking"""
    
    try:
        booking = PendingBooking.objects.get(booking_id=booking_id)
        
        if request.registration_user.role not in ['manager', 'admin']:
            if booking.created_by != request.registration_user:
                messages.error(request, '❌ You can only cancel your own bookings')
                return redirect('registration_portal:pending_bookings')
        
        if booking.cancel(request.registration_user):
            messages.success(request, f'✅ {booking.booking_id} cancelled')
        else:
            messages.error(request, f'❌ Cannot cancel {booking.booking_id}')
        
    except PendingBooking.DoesNotExist:
        messages.error(request, '❌ Booking not found')
    
    return redirect('registration_portal:pending_bookings')


@registration_login_required
def my_bookings(request):
    """View booking history"""
    
    user = request.registration_user
    
    pending_bookings = PendingBooking.objects.filter(created_by=user).order_by('-created_at')[:20]
    task_packages = TaskPackage.objects.filter(created_by=user).order_by('-created_at')[:20]
    
    context = {
        'user': user,
        'pending_bookings': pending_bookings,
        'task_packages': task_packages,
    }
    
    return render(request, 'registration_portal/my_bookings.html', context)


@registration_login_required
def branch_bookings(request):
    """Manager view of all branch bookings"""
    
    user = request.registration_user
    
    if user.role not in ['manager', 'admin']:
        messages.error(request, '❌ Only managers can access this page')
        return redirect('registration_portal:dashboard')
    
    pending_bookings = PendingBooking.objects.filter(branch=user.branch).order_by('-created_at')[:50]
    task_packages = TaskPackage.objects.filter(branch=user.branch).order_by('-created_at')[:50]
    
    staff_list = User.objects.filter(branch=user.branch, is_active=True).order_by('first_name')
    
    context = {
        'user': user,
        'pending_bookings': pending_bookings,
        'task_packages': task_packages,
        'staff_list': staff_list,
    }
    
    return render(request, 'registration_portal/branch_bookings.html', context)


# ============================================
# MANAGER ARRIVALS
# ============================================

@registration_login_required
def manager_arrivals(request):
    """Manager confirms arrivals for Type C bookings"""
    
    if request.registration_user.role not in ['manager', 'admin']:
        messages.error(request, '❌ Only managers can access this page')
        return redirect('registration_portal:dashboard')
    
    today = timezone.now().date()
    
    todays_bookings = TaskPackage.objects.filter(
        scheduled_date=today
    ).select_related('cat', 'cat__owner', 'created_by').order_by('arrival_status', 'created_at')
    
    pending_arrivals = todays_bookings.filter(
        booking_type='type_c',
        arrival_status='pending',
        points_awarded=False
    )
    
    context = {
        'user': request.registration_user,
        'today': today,
        'pending_arrivals': pending_arrivals,
    }
    
    return render(request, 'registration_portal/manager_arrivals.html', context)


@registration_login_required
def confirm_arrival(request, package_id):
    """Confirm arrival for Type C"""
    
    if request.registration_user.role not in ['manager', 'admin']:
        messages.error(request, '❌ Only managers can confirm arrivals')
        return redirect('registration_portal:dashboard')
    
    try:
        package = TaskPackage.objects.get(package_id=package_id)
        
        if package.arrival_status == 'arrived':
            messages.warning(request, f'⚠️ {package_id} already confirmed')
        else:
            success = package.confirm_arrival(request.registration_user)
            
            if success and package.points_awarded:
                messages.success(request, f'✅ {package_id} confirmed! {package.total_points} points released!')
            else:
                messages.success(request, f'✅ {package_id} confirmed')
        
    except TaskPackage.DoesNotExist:
        messages.error(request, f'❌ Package not found')
    except Exception as e:
        messages.error(request, f'❌ Error: {str(e)}')
    
    return redirect('registration_portal:manager_arrivals')


@registration_login_required
def mark_no_show(request, package_id):
    """Mark as no-show"""
    
    if request.registration_user.role not in ['manager', 'admin']:
        messages.error(request, '❌ Only managers can mark no-shows')
        return redirect('registration_portal:dashboard')
    
    try:
        package = TaskPackage.objects.get(package_id=package_id)
        
        if package.arrival_status == 'no_show':
            messages.warning(request, f'⚠️ {package_id} already marked as no-show')
        else:
            success = package.mark_no_show(request.registration_user)
            
            if success:
                messages.warning(request, f'⚠️ {package_id} - NO-SHOW. Points NOT awarded.')
        
    except TaskPackage.DoesNotExist:
        messages.error(request, f'❌ Package not found')
    except Exception as e:
        messages.error(request, f'❌ Error: {str(e)}')
    
    return redirect('registration_portal:manager_arrivals')

@registration_login_required
def confirm_pending_booking(request, booking_id):
    
    
    if request.method != 'POST':
        return redirect('registration_portal:pending_bookings')
    
    try:
        booking = PendingBooking.objects.get(booking_id=booking_id)
        
        # Check permissions
        if request.registration_user.role not in ['manager', 'admin']:
            if booking.created_by != request.registration_user:
                messages.error(request, '❌ You can only confirm your own bookings')
                return redirect('registration_portal:pending_bookings')
        
        # ✅ CHECK IF FILE WAS UPLOADED!
        payment_proof = request.FILES.get('payment_proof')
        if not payment_proof:
            messages.error(request, '⚠️ Payment proof is required! Please select a file.')
            return redirect('registration_portal:pending_bookings')
        
        # ✅ CHECK FILE SIZE (max 5MB)
        if payment_proof.size > 5 * 1024 * 1024:
            messages.error(request, '⚠️ File too large! Maximum 5MB.')
            return redirect('registration_portal:pending_bookings')
        
        # ✅ CHECK FILE TYPE
        allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp']
        if payment_proof.content_type not in allowed_types:
            messages.error(request, '⚠️ Only JPG, PNG, WEBP images allowed!')
            return redirect('registration_portal:pending_bookings')
        
        # Now confirm
        success, task_package, error = booking.confirm_and_convert(
            confirmed_by_user=request.registration_user,
            payment_proof_file=payment_proof
        )
        
        if success:
            # ✅ FIXED MESSAGE: 2 points awarded for booking confirmation!
            messages.success(
                request,
                f'✅ {booking.booking_id} confirmed! {task_package.package_id} created. '
                f'You got 2 POINTS for booking confirmation! '
                f'(Task completion points will be awarded when tasks are done)'
            )
        else:
            messages.error(request, f'❌ Error: {error}')
        
    except PendingBooking.DoesNotExist:
        messages.error(request, '❌ Booking not found')
    except Exception as e:
        messages.error(request, f'❌ Error: {str(e)}')
        import traceback
        print(traceback.format_exc())
    
    return redirect('registration_portal:pending_bookings')

# ============================================
# OCR SCREENSHOT UPLOAD
# ============================================

try:
    from .ocr_utils import extract_text_from_image, parse_portal_collar_data, validate_extracted_data
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False


@registration_login_required
def upload_screenshot(request):
    """Upload screenshot for OCR"""
    
    if not OCR_AVAILABLE:
        messages.error(request, '❌ OCR feature not available. Install pytesseract.')
        return redirect('registration_portal:dashboard')
    
    if request.method == 'POST':
        screenshot = request.FILES.get('screenshot')
        
        if not screenshot:
            messages.error(request, '⚠️ Please upload a screenshot')
            return redirect('registration_portal:upload_screenshot')
        
        allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp']
        if screenshot.content_type not in allowed_types:
            messages.error(request, '⚠️ Only JPG, PNG, WEBP images supported')
            return redirect('registration_portal:upload_screenshot')
        
        if screenshot.size > 5 * 1024 * 1024:
            messages.error(request, '⚠️ Image too large. Max 5MB.')
            return redirect('registration_portal:upload_screenshot')
        
        try:
            extracted_text = extract_text_from_image(screenshot)
            
            if not extracted_text:
                messages.error(request, '❌ Could not extract text. Try a clearer screenshot.')
                return redirect('registration_portal:upload_screenshot')
            
            parsed_data = parse_portal_collar_data(extracted_text)
            is_valid, confidence, errors = validate_extracted_data(parsed_data)
            
            request.session['ocr_data'] = {
                'name': parsed_data['name'],
                'phone': parsed_data['phone'],
                'ic_number': parsed_data['ic_number'],
                'service': parsed_data['service'],
                'date': parsed_data['date'],
                'notes': parsed_data['notes'],
                'raw_text': parsed_data['raw_text'],
                'confidence': confidence,
                'errors': errors,
                'is_valid': is_valid,
            }
            
            return redirect('registration_portal:review_ocr_data')
        
        except Exception as e:
            messages.error(request, f'❌ OCR Error: {str(e)}')
            return redirect('registration_portal:upload_screenshot')
    
    context = {
        'user': request.registration_user,
    }
    
    return render(request, 'registration_portal/upload_screenshot.html', context)

@registration_login_required
def review_ocr_data(request):
    """Review OCR data and create customer + cat"""
    
    ocr_data = request.session.get('ocr_data')
    
    if not ocr_data:
        messages.warning(request, '⚠️ No OCR data found. Please upload a screenshot first.')
        return redirect('registration_portal:upload_screenshot')
    
    # Calculate confidence percentage
    if 'confidence' in ocr_data and ocr_data['confidence']:
        try:
            ocr_data['confidence_percent'] = int(float(ocr_data['confidence']) * 100)
        except (ValueError, TypeError):
            ocr_data['confidence_percent'] = 0
    else:
        ocr_data['confidence_percent'] = 0
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        print(f"DEBUG: POST received, action={action}")
        print(f"DEBUG: All POST keys: {list(request.POST.keys())}")
        
        if action == 'cancel':
            request.session.pop('ocr_data', None)
            messages.info(request, 'OCR data discarded')
            return redirect('registration_portal:upload_screenshot')
        
        elif action == 'create':
            # Get customer data
            name = request.POST.get('name', '').strip()
            phone = request.POST.get('phone', '').strip()
            ic_number = request.POST.get('ic_number', '').strip()
            email = request.POST.get('email', '').strip()
            address = request.POST.get('address', '').strip()
            
            # Get cat data
            cat_name = request.POST.get('cat_name', '').strip()
            breed = request.POST.get('breed', '').strip() or 'mixed'
            age = request.POST.get('age', '').strip() or '0'
            gender = request.POST.get('gender', '').strip() or 'male'
            color = request.POST.get('color', '').strip()
            weight = request.POST.get('weight', '').strip()
            vaccination_status = request.POST.get('vaccination_status', '').strip() or 'unknown'
            medical_notes = request.POST.get('medical_notes', '').strip()
            special_requirements = request.POST.get('special_requirements', '').strip()
            
            print(f"DEBUG: Customer name='{name}', phone='{phone}'")
            print(f"DEBUG: Cat name='{cat_name}', breed='{breed}'")
            
            # Validation
            errors = []
            
            # Check if form was actually submitted with data
            if not name and not phone and not cat_name:
                messages.error(request, '❌ No data received from form. Please try again.')
                print(f"DEBUG: Form submitted but no data extracted")
                print(f"DEBUG: POST data: {dict(request.POST)}")
                print(f"DEBUG: OCR data in session: {ocr_data}")
                return redirect('registration_portal:review_ocr_data')
            
            if not name:
                errors.append('Customer name is required')
            
            if not phone:
                errors.append('Phone number is required')
            
            if not cat_name:
                errors.append('Cat name is required')
            
            if errors:
                for error in errors:
                    messages.error(request, f'❌ {error}')
                return redirect('registration_portal:review_ocr_data')
            
            # Check if customer already exists
            if phone:
                existing = Customer.objects.filter(phone=phone).first()
                if existing:
                    messages.warning(
                        request,
                        f'⚠️ Customer with phone {phone} already exists: {existing.customer_id}'
                    )
                    return redirect('registration_portal:customer_detail', customer_id=existing.customer_id)
            
            try:
                with transaction.atomic():
                    # Create customer
                    print(f"DEBUG: About to create customer with name={name}")
                    
                    customer = Customer.objects.create(
                        name=name.upper(),
                        phone=phone,
                        ic_number=ic_number if ic_number else '',
                        email=email if email else '',
                        address=address if address else '',
                        registered_by=request.registration_user
                    )
                    
                    print(f"✓ Customer created: {customer.customer_id} - {customer.name}")
                    
                    # Convert age to integer
                    try:
                        cat_age = int(age) if age and age.isdigit() else 0
                    except ValueError:
                        cat_age = 0
                        print(f"⚠️ Invalid age value: {age}, defaulting to 0")
                    
                    # Convert weight to decimal
                    try:
                        cat_weight = float(weight) if weight else None
                    except ValueError:
                        cat_weight = None
                        print(f"⚠️ Invalid weight value: {weight}, defaulting to None")
                    
                    # Validate gender
                    if gender not in ['male', 'female']:
                        gender = 'male'
                        print(f"⚠️ Invalid gender, defaulting to male")
                    
                    # Validate vaccination status
                    valid_vaccination = ['up_to_date', 'partial', 'none', 'unknown']
                    if vaccination_status not in valid_vaccination:
                        vaccination_status = 'unknown'
                    
                    print(f"DEBUG: About to create cat with name={cat_name}, breed={breed}, age={cat_age}")
                    
                    # Create cat
                    cat = Cat.objects.create(
                        name=cat_name.upper(),
                        owner=customer,
                        breed=breed if breed else 'mixed',
                        age=cat_age,
                        gender=gender.lower(),
                        color=color if color else '',
                        weight=cat_weight,
                        vaccination_status=vaccination_status,
                        medical_notes=medical_notes if medical_notes else '',
                        special_requirements=special_requirements if special_requirements else '',
                        registered_by=request.registration_user
                    )
                    
                    print(f"✓ Cat created: {cat.cat_id} - {cat.name}")
                    
                    # Update session stats
                    session_id = request.session.get('registration_session_id')
                    if session_id:
                        try:
                            session = RegistrationSession.objects.get(id=session_id)
                            session.customers_registered += 1
                            session.cats_registered += 1
                            session.save()
                            print(f"✓ Session stats updated")
                        except RegistrationSession.DoesNotExist:
                            print(f"⚠️ Session {session_id} not found, skipping stats update")
                    
                    # Clear OCR data from session
                    request.session.pop('ocr_data', None)
                    
                    messages.success(
                        request,
                        f'✅ Success! Customer {customer.customer_id} and Cat {cat.cat_id} - {cat.name} created from screenshot!'
                    )
                    
                    print(f"✓ All done! Redirecting to create_service_request")
                    
                    # Redirect to create service request
                    return redirect('registration_portal:create_service_request', customer_id=customer.customer_id)
            
            except IntegrityError as e:
                error_msg = str(e)
                if 'UNIQUE constraint' in error_msg or 'duplicate' in error_msg.lower():
                    messages.error(request, f'❌ Duplicate entry detected. A customer with this phone number may already exist.')
                else:
                    messages.error(request, f'❌ Database integrity error: {error_msg}')
                print(f"✗ IntegrityError: {error_msg}")
                import traceback
                print(traceback.format_exc())
                return redirect('registration_portal:review_ocr_data')
            
            except Exception as e:
                messages.error(request, f'❌ Error creating records: {str(e)}')
                print(f"✗ Exception type: {type(e).__name__}")
                print(f"✗ Exception: {str(e)}")
                import traceback
                print(traceback.format_exc())
                return redirect('registration_portal:review_ocr_data')
    
    # GET request - show form
    context = {
        'user': request.registration_user,
        'ocr_data': ocr_data,
    }
    
    return render(request, 'registration_portal/review_ocr_data.html', context)