# CREATE FILE: task_management/management/commands/expire_pending_bookings.py

from django.core.management.base import BaseCommand
from django.utils import timezone
from task_management.models import PendingBooking

class Command(BaseCommand):
    help = 'Auto-expire pending bookings where scheduled_date has passed'

    def handle(self, *args, **options):
        today = timezone.now().date()
        
        # Find pending bookings scheduled BEFORE today
        expired_bookings = PendingBooking.objects.filter(
            scheduled_date__lt=today,
            status='pending_payment'
        )
        
        count = expired_bookings.count()
        
        if count > 0:
            self.stdout.write(f'Found {count} expired bookings...')
            
            for booking in expired_bookings:
                booking.mark_as_expired()
                self.stdout.write(
                    self.style.WARNING(
                        f'✗ Expired: {booking.booking_id} (scheduled {booking.scheduled_date})'
                    )
                )
            
            self.stdout.write(
                self.style.SUCCESS(f'✓ Successfully expired {count} bookings')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('✓ No bookings to expire')
            )
