# task_management/management/commands/fetch_booking_emails.py

from django.core.management.base import BaseCommand
from task_management.utils.gmail_fetcher import fetch_booking_emails, mark_email_as_read
from task_management.utils.email_parser import parse_booking_email
from task_management.utils.booking_creator import create_booking_from_email


class Command(BaseCommand):
    help = 'Fetch booking emails and create task packages'

    def add_arguments(self, parser):
        parser.add_argument(
            '--max',
            type=int,
            default=10,
            help='Maximum number of emails to fetch'
        )

    def handle(self, *args, **options):
        max_emails = options['max']
        
        self.stdout.write(self.style.SUCCESS('📧 Fetching booking emails from Gmail...'))
        
        # Fetch emails
        emails = fetch_booking_emails(max_emails=max_emails)
        
        if not emails:
            self.stdout.write('✓ No new booking emails found.')
            return
        
        self.stdout.write(f'Found {len(emails)} email(s)\n')
        
        processed = 0
        failed = 0
        
        for email_data in emails:
            self.stdout.write(f"\n{'='*70}")
            self.stdout.write(f"📧 Subject: {email_data['subject']}")
            self.stdout.write(f"📧 From: {email_data['from_email']}")
            self.stdout.write(f"📧 Date: {email_data['date']}")
            
            # Parse email
            parsed_data = parse_booking_email(
                email_data['subject'],
                email_data['body']
            )
            
            self.stdout.write(f"\n📋 Extracted Data:")
            self.stdout.write(f"  Order ID: {parsed_data.get('order_id', 'N/A')}")
            self.stdout.write(f"  Customer: {parsed_data.get('customer_name', 'N/A')}")
            self.stdout.write(f"  Phone: {parsed_data.get('customer_phone', 'N/A')}")
            self.stdout.write(f"  Cat: {parsed_data.get('cat_name', 'N/A')}")
            self.stdout.write(f"  Services: {len(parsed_data.get('services', []))}")
            self.stdout.write(f"  Branch: {parsed_data.get('branch', 'N/A').upper()}")
            
            # Create booking
            result = create_booking_from_email(email_data, parsed_data)
            
            if result['success']:
                self.stdout.write(self.style.SUCCESS(f"\n✅ SUCCESS!"))
                self.stdout.write(f"  Package ID: {result['package_id']}")
                self.stdout.write(f"  Customer ID: {result['customer_id']}")
                self.stdout.write(f"  Cat ID: {result['cat_id']}")
                self.stdout.write(f"  Tasks Created: {result['tasks_created']}")
                
                if result['tasks_not_found']:
                    self.stdout.write(self.style.WARNING(
                        f"  ⚠️ Services not matched: {', '.join(result['tasks_not_found'])}"
                    ))
                
                # Mark email as read
                if mark_email_as_read(email_data['email_id']):
                    self.stdout.write(self.style.SUCCESS("  ✓ Email marked as read"))
                
                processed += 1
            else:
                self.stdout.write(self.style.ERROR(f"\n❌ FAILED: {result['message']}"))
                if result['errors']:
                    for error in result['errors']:
                        self.stdout.write(self.style.ERROR(f"   - {error}"))
                failed += 1
        
        self.stdout.write(f"\n{'='*70}")
        self.stdout.write(self.style.SUCCESS(
            f'\n✅ Summary: {processed} successful, {failed} failed'
        ))