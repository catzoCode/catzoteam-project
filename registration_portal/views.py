# registration_portal/views.py
# Complete registration portal views - CORRECTED VERSION

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from django.http import JsonResponse
from datetime import date, datetime
from django.db import transaction

from task_management.models import (
    Customer, Cat, ServiceRequest, TaskGroup, TaskType, 
    TaskPackage, Task
)
from accounts.models import User
from .models import RegistrationSession

# ============================================
# LOGIN/LOGOUT (Employee ID Only)
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
            
            # Create session
            session = RegistrationSession.objects.create(
                user=user,
                is_active=True
            )
            
            # Store in Django session
            request.session['registration_user_id'] = user.id
            request.session['registration_session_id'] = session.id
            
            messages.success(request, f'Welcome {user.first_name or user.username}!')
            return redirect('registration_portal:dashboard')
        
        except User.DoesNotExist:
            messages.error(request, f'Invalid Employee ID: {employee_id}')
            return redirect('registration_portal:login')
    
    # Check if already logged in
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
    
    # Clear session
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
            # Also set request.user for compatibility
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
    
    # TODAY'S STATISTICS
    today_customers = Customer.objects.count()
    today_cats = Cat.objects.count()
    today_packages = TaskPackage.objects.filter(status='pending').count()
    
    # SESSION STATISTICS
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
    
    # RECENT CUSTOMERS (Last 5)
    recent_customers = Customer.objects.all().order_by('-id')[:5]
    
    # RECENT TASK PACKAGES (Pending, Last 5)
    recent_packages = TaskPackage.objects.filter(
        status='pending'
    ).select_related(
        'cat', 
        'cat__owner', 
        'created_by'
    ).prefetch_related(
        'tasks'
    ).order_by('-id')[:5]
    
    context = {
        'user': request.registration_user,
        'today': today,
        'today_customers': today_customers,
        'today_cats': today_cats,
        'today_requests': today_packages,
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
        
        # Get search parameters
        search_query = request.POST.get('search_query', '') or request.GET.get('search_query', '')
        search_ic = request.POST.get('search_ic', '') or request.GET.get('search_ic', '')
        search_phone = request.POST.get('search_phone', '') or request.GET.get('search_phone', '')
        search_email = request.POST.get('search_email', '') or request.GET.get('search_email', '')
        
        # Build query
        query = Q()
        
        if search_query:
            query |= Q(name__icontains=search_query)
            query |= Q(customer_id__icontains=search_query)
        
        if search_ic:
            query &= Q(ic_number__icontains=search_ic)
        
        if search_phone:
            query &= Q(phone__icontains=search_phone)
        
        if search_email:
            query &= Q(email__icontains=search_email)
        
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
        # Get form data
        name = request.POST.get('name', '').strip()
        phone = request.POST.get('phone', '').strip()
        email = request.POST.get('email', '').strip()
        ic_number = request.POST.get('ic_number', '').strip()
        address = request.POST.get('address', '').strip()
        emergency_contact = request.POST.get('emergency_contact', '').strip()
        
        # Validate
        if not name or not phone:
            messages.error(request, 'Name and Phone are required')
            return redirect('registration_portal:register_customer')
        
        # Check duplicates
        if Customer.objects.filter(phone=phone).exists():
            messages.error(request, f'Customer with phone {phone} already exists')
            return redirect('registration_portal:customer_search')
        
        if ic_number and Customer.objects.filter(ic_number=ic_number).exists():
            messages.error(request, f'Customer with IC {ic_number} already exists')
            return redirect('registration_portal:customer_search')
        
        # Create customer
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
            
            # Update session stats
            session_id = request.session.get('registration_session_id')
            if session_id:
                try:
                    session = RegistrationSession.objects.get(id=session_id)
                    session.customers_registered += 1
                    session.save()
                except RegistrationSession.DoesNotExist:
                    pass
            
            messages.success(request, f'✓ Customer {customer.customer_id} registered successfully!')
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
        # Get form data
        name = request.POST.get('name', '').strip()
        breed = request.POST.get('breed', 'mixed')
        age = request.POST.get('age', 0)
        gender = request.POST.get('gender', 'male')
        color = request.POST.get('color', '').strip()
        weight = request.POST.get('weight', 0) or None
        vaccination_status = request.POST.get('vaccination_status', 'unknown')
        medical_notes = request.POST.get('medical_notes', '').strip()
        special_requirements = request.POST.get('special_requirements', '').strip()
        photo = request.FILES.get('photo')  # Handle photo upload
        
        # Validate
        if not name:
            messages.error(request, 'Cat name is required')
            return redirect('registration_portal:register_cat', customer_id=customer_id)
        
        # Create cat
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
                photo=photo,  # Save photo
                registered_by=request.registration_user
            )
            
            # Update session stats
            session_id = request.session.get('registration_session_id')
            if session_id:
                try:
                    session = RegistrationSession.objects.get(id=session_id)
                    session.cats_registered += 1
                    session.save()
                except RegistrationSession.DoesNotExist:
                    pass
            
            messages.success(request, f'✓ Cat {cat.cat_id} - {cat.name} registered successfully!')
            
            # Ask if want to add another cat or create service request
            action = request.POST.get('action', 'another')
            
            if action == 'service':
                return redirect('registration_portal:create_service_request', customer_id=customer_id)
            else:
                return redirect('registration_portal:register_cat', customer_id=customer_id)
        
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
            return redirect('registration_portal:register_cat', customer_id=customer_id)
    
    # Get customer's cats
    cats = customer.cats.filter(is_active=True).order_by('-registration_date')
    
    context = {
        'user': request.registration_user,
        'customer': customer,
        'cats': cats,
    }
    
    return render(request, 'registration_portal/register_cat.html', context)


# ============================================
# CREATE SERVICE REQUEST (ONLY ONE VERSION)
# ============================================

# UPDATED create_service_request VIEW
# Replace in registration_portal/views.py

@registration_login_required
def create_service_request(request, customer_id=None):
    """Create service request with NEXT BOOKING SYSTEM support"""
    
    if request.method == 'POST':
        post_customer_id = request.POST.get('customer_id')
        cat_ids = request.POST.getlist('cat_ids')
        selected_tasks = request.POST.getlist('selected_tasks')
        notes = request.POST.get('notes', '')
        preferred_date = request.POST.get('preferred_date')
        preferred_time = request.POST.get('preferred_time')
        
        # ============ NEXT BOOKING FIELDS ============
        booking_type = request.POST.get('booking_type', 'type_c')  # Default: Hold points
        payment_proof = request.FILES.get('payment_proof')  # Type A: Screenshot
        is_combo = request.POST.get('is_combo') == 'on'  # Type B: Combo checkbox
        combo_session = request.POST.get('combo_session')  # e.g., "2"
        combo_total = request.POST.get('combo_total')  # e.g., "4"
        
        try:
            with transaction.atomic():
                customer = Customer.objects.get(customer_id=post_customer_id)
                cats = Cat.objects.filter(cat_id__in=cat_ids)
                
                if not cats.exists():
                    messages.error(request, 'Please select at least one cat.')
                    return redirect('registration_portal:create_service_request', customer_id=post_customer_id)
                
                if not selected_tasks:
                    messages.error(request, 'Please select at least one service.')
                    return redirect('registration_portal:create_service_request', customer_id=post_customer_id)
                
                # Validation: Type A requires payment proof
                if booking_type == 'type_a' and not payment_proof:
                    messages.error(request, '⚠️ Type A requires payment proof screenshot!')
                    return redirect('registration_portal:create_service_request', customer_id=post_customer_id)
                
                # Validation: Type B requires combo info
                if booking_type == 'type_b' or is_combo:
                    booking_type = 'type_b'  # Force Type B if combo checked
                    if not combo_session or not combo_total:
                        messages.error(request, '⚠️ Combo package requires session numbers (e.g., 2 of 4)')
                        return redirect('registration_portal:create_service_request', customer_id=post_customer_id)
                
                created_packages = []
                total_all_points = 0
                
                # Create ONE task package per cat
                for cat in cats:
                    # Create task package with Next Booking fields
                    task_package = TaskPackage.objects.create(
                        cat=cat,
                        created_by=request.registration_user,
                        status='pending',
                        notes=notes or f'Service request for {cat.name}',
                        branch=request.registration_user.branch,  # Auto-detect branch
                        
                        # NEXT BOOKING FIELDS
                        booking_type=booking_type,
                        payment_proof=payment_proof if booking_type == 'type_a' else None,
                        is_combo_package=(booking_type == 'type_b'),
                        combo_session_number=int(combo_session) if combo_session else None,
                        combo_total_sessions=int(combo_total) if combo_total else None,
                        scheduled_date=preferred_date if preferred_date else None,
                        arrival_status='pending',
                        points_awarded=False,  # Start with no points
                    )
                    
                    # Create individual tasks for this package
                    package_points = 0
                    
                    for task_type_id in selected_tasks:
                        task_type = TaskType.objects.get(id=task_type_id)
                        
                        Task.objects.create(
                            package=task_package,
                            task_type=task_type,
                            points=task_type.points,
                            scheduled_date=preferred_date if preferred_date else timezone.now().date(),
                            scheduled_time=preferred_time if preferred_time else '09:00',
                            status='pending',
                            notes=f'{task_type.name} for {cat.name}'
                        )
                        
                        package_points += task_type.points
                    
                    # Update task package total points
                    task_package.total_points = package_points
                    task_package.save()
                    
                    # ============ AWARD POINTS BASED ON TYPE ============
                    
                    if booking_type == 'type_a':
                        # TYPE A: Award points IMMEDIATELY!
                        success = task_package.award_points_immediately()
                        if success:
                            messages.success(
                                request,
                                f'✅ {task_package.package_id}: Payment proof uploaded! '
                                f'You got {package_points} points NOW!'
                            )
                        else:
                            messages.warning(
                                request,
                                f'⚠️ {task_package.package_id}: Created but points not awarded. Check logs.'
                            )
                    
                    elif booking_type == 'type_b':
                        # TYPE B: Combo package - NO points!
                        messages.info(
                            request,
                            f'❌ {task_package.package_id}: Combo session {combo_session}/{combo_total} - '
                            f'No points (already got when package sold)'
                        )
                    
                    else:  # type_c
                        # TYPE C: Points on HOLD!
                        messages.warning(
                            request,
                            f'⏸️ {task_package.package_id}: {package_points} points ON HOLD - '
                            f'Will be released when customer arrives on {preferred_date}'
                        )
                    
                    created_packages.append(task_package)
                    total_all_points += package_points
                
                # Update session stats
                session_id = request.session.get('registration_session_id')
                if session_id:
                    try:
                        session = RegistrationSession.objects.get(id=session_id)
                        session.service_requests_created += len(created_packages)
                        session.save()
                    except RegistrationSession.DoesNotExist:
                        pass
                
                # Overall success message
                package_ids = ', '.join([p.package_id for p in created_packages])
                messages.success(
                    request, 
                    f'🎉 Created {len(created_packages)} booking(s): {package_ids}'
                )
                
                return redirect('registration_portal:dashboard')
                
        except Customer.DoesNotExist:
            messages.error(request, 'Customer not found')
            return redirect('registration_portal:customer_search')
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
            import traceback
            print(traceback.format_exc())
            return redirect('registration_portal:customer_search')
    
    # GET request - show form
    if not customer_id:
        customer_id = request.GET.get('customer_id')
    
    customer = None
    cats = []
    
    if customer_id:
        try:
            customer = Customer.objects.get(customer_id=customer_id)
            cats = customer.cats.all()
        except Customer.DoesNotExist:
            messages.error(request, 'Customer not found')
            return redirect('registration_portal:customer_search')
    
    # Get all task types organized by group
    task_groups = TaskGroup.objects.filter(is_active=True).prefetch_related('task_types')
    
    # Organize tasks by category
    grooming_groups = task_groups.filter(name__icontains='Grooming')
    sales_groups = task_groups.filter(name__icontains='Sales')
    product_groups = task_groups.filter(name__icontains='Product')
    other_groups = task_groups.exclude(
        name__icontains='Grooming'
    ).exclude(
        name__icontains='Sales'
    ).exclude(
        name__icontains='Product'
    )
    
    context = {
        'user': request.registration_user,
        'customer': customer,
        'cats': cats,
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
    
    # Get recent task packages for this customer's cats
    recent_packages = TaskPackage.objects.filter(
        cat__owner=customer
    ).select_related('cat', 'created_by').prefetch_related('tasks').order_by('-created_at')[:10]
    
    context = {
        'user': request.registration_user,
        'customer': customer,
        'cats': cats,
        'recent_packages': recent_packages,
    }
    
    return render(request, 'registration_portal/customer_detail.html', context)


# ============================================
# AJAX ENDPOINTS
# ============================================

@registration_login_required
def ajax_search_tasks(request):
    """AJAX endpoint for live task search"""
    query = request.GET.get('q', '').strip()
    
    if len(query) < 2:
        return JsonResponse({'tasks': []})
    
    tasks = TaskType.objects.filter(
        Q(name__icontains=query) | Q(description__icontains=query),
        is_active=True
    ).select_related('group').values(
        'id', 'name', 'points', 'price', 'description', 'group__name'
    )[:20]
    
    return JsonResponse({'tasks': list(tasks)})


@registration_login_required
def get_task_details(request, task_type_id):
    """AJAX endpoint to get task type details"""
    try:
        task_type = TaskType.objects.get(id=task_type_id)
        return JsonResponse({
            'success': True,
            'id': task_type.id,
            'name': task_type.name,
            'points': task_type.points,
            'price': float(task_type.price) if task_type.price else 0,
            'description': task_type.description,
            'category': task_type.category,
        })
    except TaskType.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Task type not found'})
    

@registration_login_required
def manager_arrivals(request):
    """Manager page to confirm customer arrivals and release held points"""
    
    # Only managers and admins can access
    if request.registration_user.role not in ['manager', 'admin']:
        messages.error(request, '❌ Only managers can access this page')
        return redirect('registration_portal:dashboard')
    
    today = timezone.now().date()
    
    # Get today's scheduled bookings
    todays_bookings = TaskPackage.objects.filter(
        scheduled_date=today
    ).select_related(
        'cat',
        'cat__owner',
        'created_by',
        'confirmed_by'
    ).order_by('arrival_status', 'created_at')
    
    # Organize by type
    pending_arrivals = todays_bookings.filter(
        booking_type='type_c',
        arrival_status='pending',
        points_awarded=False
    )
    
    got_proof_bookings = todays_bookings.filter(
        booking_type='type_a'
    )
    
    combo_bookings = todays_bookings.filter(
        booking_type='type_b'
    )
    
    arrived_bookings = todays_bookings.filter(
        arrival_status='arrived'
    )
    
    no_show_bookings = todays_bookings.filter(
        arrival_status='no_show'
    )
    
    # Statistics
    stats = {
        'total_scheduled': todays_bookings.count(),
        'pending': pending_arrivals.count(),
        'arrived': arrived_bookings.count(),
        'no_show': no_show_bookings.count(),
        'points_on_hold': sum(pkg.total_points for pkg in pending_arrivals),
    }
    
    context = {
        'user': request.registration_user,
        'today': today,
        'pending_arrivals': pending_arrivals,
        'got_proof_bookings': got_proof_bookings,
        'combo_bookings': combo_bookings,
        'arrived_bookings': arrived_bookings,
        'no_show_bookings': no_show_bookings,
        'stats': stats,
    }
    
    return render(request, 'registration_portal/manager_arrivals.html', context)


@registration_login_required
def confirm_arrival(request, package_id):
    """Confirm customer arrived (releases held points)"""
    
    # Only managers and admins
    if request.registration_user.role not in ['manager', 'admin']:
        messages.error(request, '❌ Only managers can confirm arrivals')
        return redirect('registration_portal:dashboard')
    
    try:
        package = TaskPackage.objects.get(package_id=package_id)
        
        if package.arrival_status == 'arrived':
            messages.warning(request, f'⚠️ {package_id} already confirmed as arrived')
        else:
            success = package.confirm_arrival(request.registration_user)
            
            if success:
                if package.booking_type == 'type_c' and package.points_awarded:
                    messages.success(
                        request,
                        f'✅ {package_id} - Customer ARRIVED! '
                        f'{package.total_points} points released to {package.created_by.first_name}'
                    )
                else:
                    messages.success(request, f'✅ {package_id} - Arrival confirmed')
            else:
                messages.error(request, f'❌ Error confirming arrival for {package_id}')
        
    except TaskPackage.DoesNotExist:
        messages.error(request, f'❌ Package {package_id} not found')
    except Exception as e:
        messages.error(request, f'❌ Error: {str(e)}')
    
    return redirect('registration_portal:manager_arrivals')


@registration_login_required
def mark_no_show(request, package_id):
    """Mark customer as no-show (points NOT awarded)"""
    
    # Only managers and admins
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
                messages.warning(
                    request,
                    f'⚠️ {package_id} - Marked as NO-SHOW. '
                    f'{package.total_points} points NOT awarded.'
                )
            else:
                messages.error(request, f'❌ Error marking no-show for {package_id}')
        
    except TaskPackage.DoesNotExist:
        messages.error(request, f'❌ Package {package_id} not found')
    except Exception as e:
        messages.error(request, f'❌ Error: {str(e)}')
    
    return redirect('registration_portal:manager_arrivals')


@registration_login_required
def auto_crosscheck_customer(request, customer_id):
    """
    Auto-crosscheck when customer arrives
    Automatically confirm all pending bookings for this customer
    """
    
    try:
        customer = Customer.objects.get(customer_id=customer_id)
        
        # Find all pending arrivals for this customer
        pending_packages = TaskPackage.objects.filter(
            cat__owner=customer,
            booking_type='type_c',
            arrival_status='pending',
            points_awarded=False,
            scheduled_date__lte=timezone.now().date()
        )
        
        confirmed_count = 0
        total_points_released = 0
        
        for package in pending_packages:
            success = package.confirm_arrival(request.registration_user)
            if success:
                confirmed_count += 1
                total_points_released += package.total_points
        
        if confirmed_count > 0:
            messages.success(
                request,
                f'🎉 AUTO-CROSSCHECK: Confirmed {confirmed_count} booking(s) for {customer.name}! '
                f'{total_points_released} points released!'
            )
        else:
            messages.info(request, f'ℹ️ No pending bookings found for {customer.name}')
        
    except Customer.DoesNotExist:
        messages.error(request, f'❌ Customer not found')
    except Exception as e:
        messages.error(request, f'❌ Error: {str(e)}')
    
    return redirect('registration_portal:manager_arrivals')