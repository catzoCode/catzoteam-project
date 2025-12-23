from django.core.management.base import BaseCommand
from accounts.models import User
import os

class Command(BaseCommand):
    help = 'Create default superuser if none exists'

    def handle(self, *args, **kwargs):
        if not User.objects.filter(is_superuser=True).exists():
            # Get credentials from environment variables or use defaults
            username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'admin')
            email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'catzo.code@gmail.com')
            password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', 'CatzoAdmin2024!')
            
            User.objects.create_superuser(
                username=username,
                email=email,
                password=password,
                first_name='Admin',
                last_name='User'
            )
            self.stdout.write(self.style.SUCCESS(f'✅ Superuser "{username}" created successfully!'))
        else:
            self.stdout.write(self.style.SUCCESS('✅ Superuser already exists'))