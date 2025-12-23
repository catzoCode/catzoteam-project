from django import forms
from django.contrib.auth.forms import UserChangeForm
from .models import User, UserProfile


class UserProfileEditForm(forms.ModelForm):
    """Form for editing user basic information"""
    
    class Meta:
        model = User
        fields = [
            'first_name',
            'last_name',
            'email',
            'phone_number',
            'profile_picture'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'First Name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Last Name'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Email Address'
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Phone Number'
            }),
            'profile_picture': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            })
        }
    
    def clean_email(self):
        """Ensure email is unique (excluding current user)"""
        email = self.cleaned_data.get('email')
        user_id = self.instance.id
        
        if User.objects.filter(email=email).exclude(id=user_id).exists():
            raise forms.ValidationError('This email is already in use.')
        
        return email


class UserProfileExtendedForm(forms.ModelForm):
    """Form for extended profile information"""
    
    class Meta:
        model = UserProfile
        fields = [
            'bio',
            'address',
            'date_of_birth',
            'emergency_contact_name',
            'emergency_contact_phone'
        ]
        widgets = {
            'bio': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Tell us about yourself...'
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Your address'
            }),
            'date_of_birth': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'emergency_contact_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Emergency Contact Name'
            }),
            'emergency_contact_phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Emergency Contact Phone'
            })
        }


class ChangePasswordForm(forms.Form):
    """Custom password change form"""
    
    current_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Current Password'
        })
    )
    new_password1 = forms.CharField(
        label='New Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'New Password'
        })
    )
    new_password2 = forms.CharField(
        label='Confirm New Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm New Password'
        })
    )
    
    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
    
    def clean_current_password(self):
        """Verify current password"""
        current_password = self.cleaned_data.get('current_password')
        if not self.user.check_password(current_password):
            raise forms.ValidationError('Current password is incorrect.')
        return current_password
    
    def clean(self):
        """Verify new passwords match"""
        cleaned_data = super().clean()
        new_password1 = cleaned_data.get('new_password1')
        new_password2 = cleaned_data.get('new_password2')
        
        if new_password1 and new_password2:
            if new_password1 != new_password2:
                raise forms.ValidationError('New passwords do not match.')
            
            if len(new_password1) < 6:
                raise forms.ValidationError('Password must be at least 6 characters.')
        
        return cleaned_data
    
    def save(self):
        """Save the new password"""
        self.user.set_password(self.cleaned_data['new_password1'])
        self.user.save()
        return self.user