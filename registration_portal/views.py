# registration_portal/views.py
# Complete registration portal views

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from datetime import date

from task_management.models import Customer, Cat, ServiceRequest
from accounts.models import User
from .models import RegistrationSession
from django.db import transaction
from task_management.models import (
    Customer, Cat, ServiceRequest, TaskGroup, TaskType, 
    TaskPackage, Task
)
from django.contrib.auth.decorators import login_required
from datetime import datetime
import json

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
    """Dashboard with statistics - SIMPLIFIED VERSION"""
    
    today = timezone.now().date()
    
    # TODAY'S STATISTICS (Simplified - no date filters to avoid field errors)
    today_customers = Customer.objects.count()
    today_cats = Cat.objects.count()
    today_packages = TaskPackage.objects.filter(status='pending').count()
    
    # SESSION STATISTICS
    session_stats = {
        'customers_registered': request.session.get('customers_registered', 0),
        'cats_registered': request.session.get('cats_registered', 0),
        'service_requests_created': request.session.get('service_requests_created', 0),
        'login_time': request.session.get('login_time', timezone.now())
    }
    
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
                session = RegistrationSession.objects.filter(id=session_id).first()
                if session:
                    session.customers_registered += 1
                    session.save()
            
            messages.success(request, f'✓ Customer {customer.customer_id} registered successfully!')
            return redirect('registration_portal:register_cat', customer_id=customer.customer_id)
        
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
            return redirect('registration_portal:register_customer')
    
    return render(request, 'registration_portal/register_customer.html')


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
                registered_by=request.registration_user
            )
            
            # Update session stats
            session_id = request.session.get('registration_session_id')
            if session_id:
                session = RegistrationSession.objects.filter(id=session_id).first()
                if session:
                    session.cats_registered += 1
                    session.save()
            
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
        'customer': customer,
        'cats': cats,
    }
    
    return render(request, 'registration_portal/register_cat.html', context)


# ============================================
# CREATE SERVICE REQUEST
# ============================================

@registration_login_required
def create_service_request(request, customer_id=None):
    """Create service request with task selection"""
    
    if request.method == 'POST':
        post_customer_id = request.POST.get('customer_id')
        cat_ids = request.POST.getlist('cat_ids')
        selected_tasks = request.POST.getlist('selected_tasks')
        notes = request.POST.get('notes', '')
        preferred_date = request.POST.get('preferred_date')
        preferred_time = request.POST.get('preferred_time')
        
        try:
            with transaction.atomic():
                customer = Customer.objects.get(customer_id=post_customer_id)
                cats = Cat.objects.filter(cat_id__in=cat_ids)
                
                if not cats.exists():
                    messages.error(request, 'Please select at least one cat.')
                    return redirect('registration_portal:create_service_request', customer_id=post_customer_id)
                
                if not selected_tasks:
                    messages.error(request, 'Please select at least one task.')
                    return redirect('registration_portal:create_service_request', customer_id=post_customer_id)
                
                created_packages = []
                total_all_points = 0
                
                # Create ONE task package per cat
                for cat in cats:
                    task_package = TaskPackage.objects.create(
                        cat=cat,
                        created_by=request.registration_user,  # ← Use request.registration_user
                        status='pending',
                        notes=notes or f'Service request for {cat.name}'
                    )
                    
                    # Create individual tasks for this package
                    package_points = 0
                    
                    for task_type_id in selected_tasks:
                        task_type = TaskType.objects.get(id=task_type_id)
                        
                        Task.objects.create(
                            package=task_package,
                            task_type=task_type,
                            points=task_type.points,
                            scheduled_date=preferred_date if preferred_date else None,
                            scheduled_time=preferred_time if preferred_time else '09:00',
                            status='pending',
                            notes=f'{task_type.name} for {cat.name}'
                        )
                        
                        package_points += task_type.points
                    
                    # Update task package total points
                    task_package.total_points = package_points
                    task_package.save()
                    
                    created_packages.append(task_package)
                    total_all_points += package_points
                
                # Success message
                package_ids = ', '.join([p.package_id for p in created_packages])
                messages.success(
                    request, 
                    f'✅ Created {len(created_packages)} task package(s): {package_ids} | '
                    f'Total: {total_all_points} points | {len(selected_tasks)} task types per cat'
                )
                
                # Update session stats
                session = request.session
                session['service_requests_created'] = session.get('service_requests_created', 0) + len(created_packages)
                request.session.modified = True
                
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
# CUSTOMER DETAIL (View & Edit)
# ============================================

@registration_login_required
def customer_detail(request, customer_id):
    """View customer details"""
    customer = get_object_or_404(Customer, customer_id=customer_id)
    cats = customer.cats.filter(is_active=True)
    service_requests = customer.service_requests.all().order_by('-created_at')[:10]
    
    context = {
        'customer': customer,
        'cats': cats,
        'service_requests': service_requests,
    }
    
    return render(request, 'registration_portal/customer_detail.html', context)


@login_required
def create_service_request(request, customer_id=None):
    """Create service request with task selection - CORRECTED for actual model structure"""
    
    if request.method == 'POST':
        post_customer_id = request.POST.get('customer_id')
        cat_ids = request.POST.getlist('cat_ids')
        selected_tasks = request.POST.getlist('selected_tasks')
        notes = request.POST.get('notes', '')
        preferred_date = request.POST.get('preferred_date')
        preferred_time = request.POST.get('preferred_time')
        
        try:
            with transaction.atomic():
                customer = Customer.objects.get(customer_id=post_customer_id)
                cats = Cat.objects.filter(cat_id__in=cat_ids)
                
                if not cats.exists():
                    messages.error(request, 'Please select at least one cat.')
                    return redirect('registration_portal:create_service_request', customer_id=post_customer_id)
                
                created_packages = []
                total_all_points = 0
                
                # Create ONE task package per cat (based on your model structure)
                for cat in cats:
                    # Create task package for this cat
                    task_package = TaskPackage.objects.create(
                        cat=cat,  # Your model uses 'cat', not 'customer'
                        created_by=request.user,
                        status='pending',
                        notes=notes or f'Service request for {cat.name}'
                    )
                    
                    # Create individual tasks for this package
                    package_points = 0
                    
                    if selected_tasks:
                        for task_type_id in selected_tasks:
                            task_type = TaskType.objects.get(id=task_type_id)
                            
                            # Create task
                            Task.objects.create(
                                package=task_package,  # Link to package
                                task_type=task_type,
                                points=task_type.points,
                                scheduled_date=preferred_date if preferred_date else None,
                                scheduled_time=preferred_time if preferred_time else '09:00',
                                status='pending',
                                notes=f'{task_type.name} for {cat.name}'
                            )
                            
                            package_points += task_type.points
                    
                    # Update task package total points
                    task_package.total_points = package_points
                    task_package.save()
                    
                    created_packages.append(task_package)
                    total_all_points += package_points
                
                # Success message
                package_ids = ', '.join([p.package_id for p in created_packages])
                messages.success(
                    request, 
                    f'✅ Created {len(created_packages)} task package(s): {package_ids} | '
                    f'Total: {total_all_points} points | {len(selected_tasks)} task types per cat'
                )
                
                # Update session stats
                session = request.session
                session['service_requests_created'] = session.get('service_requests_created', 0) + len(created_packages)
                request.session.modified = True
                
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
        'customer': customer,
        'cats': cats,
        'grooming_groups': grooming_groups,
        'sales_groups': sales_groups,
        'product_groups': product_groups,
        'other_groups': other_groups,
        'today': datetime.now().date()
    }
    
    return render(request, 'registration_portal/create_service_request.html', context)


@login_required
def get_task_details(request, task_type_id):
    """AJAX endpoint to get task type details"""
    try:
        task_type = TaskType.objects.get(id=task_type_id)
        return JsonResponse({
            'success': True,
            'name': task_type.name,
            'points': task_type.points,
            'description': task_type.description,
            'category': task_type.category,
            'requires_evidence': task_type.requires_evidence,
            'requires_approval': task_type.requires_approval,
            'rule_description': task_type.get_rule_description()
        })
    except TaskType.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Task type not found'})