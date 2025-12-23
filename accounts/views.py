from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import User, UserProfile
from .forms import UserProfileEditForm, UserProfileExtendedForm, ChangePasswordForm


def login_view(request):
    """Custom login view"""
    if request.user.is_authenticated:
        if request.user.role == 'admin':
            return redirect('dashboard:admin_dashboard')
        elif request.user.role == 'manager':
            return redirect('dashboard:manager_dashboard')
        else:
            return redirect('dashboard:staff_dashboard')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back, {user.username}!')

            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)

            if user.role == 'admin':
                return redirect('dashboard:admin_dashboard')
            elif user.role == 'manager':
                return redirect('dashboard:manager_dashboard')
            elif user.role == 'registration':
                return redirect('dashboard:staff_dashboard')
            else:
                return redirect('dashboard:staff_dashboard')
        else:
            messages.error(request, 'Invalid username or password.')

    return render(request, 'accounts/login.html')


def register_view(request):
    """Custom registration view"""
    if request.user.is_authenticated:
        if request.user.role == 'admin':
            return redirect('dashboard:admin_dashboard')
        elif request.user.role == 'manager':
            return redirect('dashboard:manager_dashboard')
        else:
            return redirect('dashboard:staff_dashboard')

    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        phone_number = request.POST.get('phone_number', '')

        if password1 != password2:
            messages.error(request, 'Passwords do not match.')
        elif User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
        elif User.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered.')
        elif len(password1) < 6:
            messages.error(request, 'Password must be at least 6 characters.')
        else:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password1,
                first_name=first_name,
                last_name=last_name,
                phone_number=phone_number,
                role='staff',
                branch='hq'
            )

            messages.success(request, f'Account created successfully! Welcome, {username}!')
            login(request, user)
            return redirect('dashboard:staff_dashboard')

    return render(request, 'accounts/register.html')


def logout_view(request):
    """Logout view"""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('accounts:login')


@login_required
def profile_view(request):
    """User profile view"""
    # Ensure user has a profile
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    context = {
        'user': request.user,
        'profile': profile
    }
    return render(request, 'accounts/profile.html', context)


@login_required
def edit_profile(request):
    """Edit user profile"""
    # Ensure user has a profile
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        user_form = UserProfileEditForm(request.POST, request.FILES, instance=request.user)
        profile_form = UserProfileExtendedForm(request.POST, instance=profile)
        
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            
            messages.success(request, 'Profile updated successfully!')
            return redirect('accounts:profile')
        else:
            for error in user_form.errors.values():
                messages.error(request, error)
            for error in profile_form.errors.values():
                messages.error(request, error)
    else:
        user_form = UserProfileEditForm(instance=request.user)
        profile_form = UserProfileExtendedForm(instance=profile)
    
    context = {
        'user_form': user_form,
        'profile_form': profile_form,
        'user': request.user,
        'profile': profile
    }
    return render(request, 'accounts/edit_profile.html', context)


@login_required
def change_password(request):
    """Change user password"""
    if request.method == 'POST':
        form = ChangePasswordForm(request.user, request.POST)
        
        if form.is_valid():
            form.save()
            # Update session to prevent logout
            update_session_auth_hash(request, request.user)
            
            messages.success(request, 'Password changed successfully!')
            return redirect('accounts:profile')
        else:
            for error in form.errors.values():
                messages.error(request, error)
    else:
        form = ChangePasswordForm(request.user)
    
    context = {
        'form': form
    }
    return render(request, 'accounts/change_password.html', context)


@login_required
def delete_profile_picture(request):
    """Delete user's profile picture"""
    if request.method == 'POST':
        if request.user.profile_picture:
            request.user.profile_picture.delete()
            request.user.save()
            messages.success(request, 'Profile picture removed successfully!')
        else:
            messages.info(request, 'No profile picture to remove.')
        
        return redirect('accounts:edit_profile')
    
    return redirect('accounts:profile')