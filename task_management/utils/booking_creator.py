# task_management/utils/booking_creator.py

from django.db import transaction
from django.utils import timezone
from datetime import datetime

from task_management.models import (
    Customer, Cat, TaskPackage, Task, TaskType, Notification
)
from accounts.models import User


def create_booking_from_email(email_data, parsed_data):
    """
    Create Customer, Cat, and TaskPackage from parsed email data
    
    Returns: dict with results
    """
    
    result = {
        'success': False,
        'package_id': None,
        'customer_id': None,
        'cat_id': None,
        'tasks_created': 0,
        'tasks_not_found': [],
        'message': '',
        'errors': []
    }
    
    # Validate required fields
    required = ['customer_name', 'customer_phone', 'cat_name']
    missing = [f for f in required if not parsed_data.get(f)]
    
    if missing:
        result['errors'].append(f"Missing required fields: {', '.join(missing)}")
        result['message'] = 'Incomplete booking data'
        return result
    
    try:
        with transaction.atomic():
            
            # 1. Create or get Customer
            customer, created = Customer.objects.get_or_create(
                phone=parsed_data['customer_phone'],
                defaults={
                    'name': parsed_data.get('customer_name', 'Unknown'),
                    'email': parsed_data.get('customer_email', ''),
                    'ic_number': parsed_data.get('customer_ic', ''),
                }
            )
            
            if not created and parsed_data.get('customer_email'):
                customer.email = parsed_data['customer_email']
                customer.save()
            
            result['customer_id'] = customer.customer_id
            
            # 2. Create or get Cat
            cat, created = Cat.objects.get_or_create(
                name=parsed_data['cat_name'],
                owner=customer,
                defaults={
                    'breed': parsed_data.get('cat_breed', 'mixed'),
                    'gender': parsed_data.get('cat_gender', 'male'),
                    'age': parsed_data.get('cat_age', 1),
                    'weight': 0,
                    'medical_notes': parsed_data.get('special_notes', ''),
                }
            )
            
            result['cat_id'] = cat.cat_id
            
            # 3. Create TaskPackage
            package = TaskPackage.objects.create(
                cat=cat,
                created_by=None,  # System-generated
                status='pending',
                notes=f"""Email Booking
Order ID: {parsed_data.get('order_id', 'N/A')}
From: {email_data.get('from_email', 'N/A')}
Date: {email_data.get('date', 'N/A')}

{parsed_data.get('special_notes', '')}"""
            )
            
            result['package_id'] = package.package_id
            
            # 4. Create Tasks from services
            scheduled_date = parsed_data.get('preferred_date')
            if scheduled_date and isinstance(scheduled_date, str):
                try:
                    scheduled_date = datetime.strptime(scheduled_date, '%Y-%m-%d').date()
                except:
                    scheduled_date = timezone.now().date()
            else:
                scheduled_date = timezone.now().date()
            
            scheduled_time = parsed_data.get('preferred_time', '09:00')
            
            # Process each service - FLEXIBLE MATCHING (NO HARD-CODED MAPPING)
            for service_name in parsed_data.get('services', []):
                service_name_clean = service_name.strip()
                
                # Try exact match first (case-insensitive)
                task_type = TaskType.objects.filter(
                    name__iexact=service_name_clean,
                    is_active=True
                ).first()
                
                # If not found, try partial match (contains)
                if not task_type:
                    task_type = TaskType.objects.filter(
                        name__icontains=service_name_clean,
                        is_active=True
                    ).first()
                
                if task_type:
                    Task.objects.create(
                        package=package,
                        task_type=task_type,
                        points=task_type.points,
                        scheduled_date=scheduled_date,
                        scheduled_time=scheduled_time,
                        status='pending'
                    )
                    result['tasks_created'] += 1
                else:
                    result['tasks_not_found'].append(service_name)
            
            # Calculate points
            package.calculate_total_points()
            
            # 5. Notify managers - ONLY FOR CORRECT BRANCH
            branch = parsed_data.get('branch')
            
            # Debug logging
            print(f"\n{'='*60}")
            print(f"📍 BRANCH DETECTION:")
            print(f"   Branch from email: {branch}")
            
            if not branch:
                print(f"❌ ERROR: No branch detected in email!")
                print(f"💡 Package {package.package_id} created but no manager notified")
                print(f"   Manager must manually find this package")
                result['errors'].append("No branch detected - manager notification skipped")
            else:
                # Find managers for THIS SPECIFIC BRANCH ONLY
                managers = User.objects.filter(
                    role__in=['manager', 'admin'],
                    branch=branch,  # CRITICAL: Must match exactly
                    is_active=True
                )
                
                print(f"   Searching for managers in branch: '{branch}'")
                print(f"   Found {managers.count()} manager(s):")
                
                for manager in managers:
                    print(f"      ✓ {manager.username} (Branch: {manager.branch}, Role: {manager.get_role_display()})")
                
                if managers.count() == 0:
                    print(f"❌ WARNING: No active managers found for branch '{branch}'!")
                    print(f"💡 Available branches in system:")
                    all_branches = User.objects.values_list('branch', flat=True).distinct()
                    for b in all_branches:
                        print(f"      - {b}")
                    result['errors'].append(f"No managers found for branch '{branch}'")
                else:
                    # Notify each manager
                    for manager in managers:
                        Notification.objects.create(
                            user=manager,
                            notification_type='package_created',
                            title=f'📧 Email Booking - {customer.name}',
                            message=f'''New booking from email!

Package: {package.package_id}
Customer: {customer.name} ({customer.phone})
Cat: {cat.name} ({cat.cat_id})
Services: {result['tasks_created']} task(s) created
Branch: {branch.upper()}

Please assign tasks to staff.''',
                            link='/task-management/unassigned/'
                        )
                        print(f"   📧 Notification sent to: {manager.username}")
            
            print(f"{'='*60}\n")
            
            result['success'] = True
            result['message'] = f"Package {package.package_id} created successfully!"
            
    except Exception as e:
        result['message'] = f"Error: {str(e)}"
        result['errors'].append(str(e))
    
    return result
