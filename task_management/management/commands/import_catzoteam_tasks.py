# task_management/management/commands/import_catzoteam_tasks.py
# Complete import command with JSON support

from django.core.management.base import BaseCommand
from django.db import transaction
from task_management.models import TaskGroup, TaskType
import json
import os

class Command(BaseCommand):
    help = 'Import all CatzoTeam task types from JSON file'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('🚀 CATZOTEAM TASK TYPE IMPORT'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write('')
        
        # Find JSON file
        json_path = self.find_json_file()
        if not json_path:
            self.stdout.write(self.style.ERROR('❌ Could not find catzoteam_tasks.json'))
            self.stdout.write('Please place catzoteam_tasks.json in:')
            self.stdout.write('  - task_management/ folder, OR')
            self.stdout.write('  - project root folder')
            return
        
        self.stdout.write(f'📁 Found JSON file: {json_path}')
        self.stdout.write('')
        
        try:
            with transaction.atomic():
                # Step 1: Load JSON data
                self.stdout.write('📥 Loading task data from JSON...')
                with open(json_path, 'r', encoding='utf-8') as f:
                    tasks_data = json.load(f)
                self.stdout.write(self.style.SUCCESS(f'✓ Loaded {len(tasks_data)} tasks'))
                self.stdout.write('')
                
                # Step 2: Create Task Groups
                self.stdout.write('📁 Creating Task Groups...')
                groups_created = self.create_task_groups(tasks_data)
                self.stdout.write(self.style.SUCCESS(f'✓ Created/Updated {groups_created} task groups'))
                self.stdout.write('')
                
                # Step 3: Create Task Types
                self.stdout.write('📋 Creating Task Types...')
                types_created, types_updated = self.create_task_types(tasks_data)
                self.stdout.write(self.style.SUCCESS(f'✓ Created {types_created} new task types'))
                self.stdout.write(self.style.SUCCESS(f'✓ Updated {types_updated} existing task types'))
                self.stdout.write('')
                
                # Step 4: Summary
                self.print_summary()
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Import failed: {str(e)}'))
            raise

    def find_json_file(self):
        """Find the JSON file in various possible locations"""
        possible_paths = [
            'catzoteam_tasks.json',  # Current directory
            'task_management/catzoteam_tasks.json',  # In app folder
            '../catzoteam_tasks.json',  # Parent directory
            os.path.join(os.path.dirname(__file__), 'catzoteam_tasks.json'),  # Same as command
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        return None

    def create_task_groups(self, tasks_data):
        """Extract unique groups from tasks and create them"""
        # Get unique group names
        group_names = list(set(task['group_name'] for task in tasks_data))
        
        # Assign order based on predefined categories
        group_order = {
            'Grooming - Beauty': 1,
            'Grooming - Wellness': 2,
            'Grooming - Catzospa+': 3,
            'Grooming - Ultraspa': 4,
            'Grooming - Biospa': 5,
            'Grooming - Lion Cut': 6,
            'Grooming - Teddy Bear Cut': 7,
            'Grooming - Styling': 8,
            'Grooming - Extras': 9,
            'Sales & Booking': 10,
            'Catzolife Products': 11,
            'Media & Marketing': 12,
            'Housekeeping - Rooms': 13,
            'Housekeeping - General': 14,
            'Daily Cleaning': 15,
        }
        
        count = 0
        for group_name in sorted(group_names, key=lambda x: group_order.get(x, 99)):
            group, created = TaskGroup.objects.update_or_create(
                name=group_name,
                defaults={
                    'description': f'{group_name} tasks',
                    'order': group_order.get(group_name, 99),
                    'is_active': True
                }
            )
            if created:
                count += 1
                self.stdout.write(f'  ✓ Created: {group.name}')
            else:
                self.stdout.write(f'  → Updated: {group.name}')
        
        return count

    def create_task_types(self, tasks_data):
        """Create all task types from JSON data"""
        created_count = 0
        updated_count = 0
        
        for idx, task_data in enumerate(tasks_data, 1):
            try:
                group = TaskGroup.objects.get(name=task_data['group_name'])
                
                # Prepare defaults
                defaults = {
                    'group': group,
                    'points': task_data.get('points', 0),
                    'description': task_data.get('description', ''),
                    'category': task_data.get('category', ''),
                    'rule_type': task_data.get('rule_type', ''),
                    'price_min': task_data.get('price_min'),
                    'price_max': task_data.get('price_max'),
                    'count_min': task_data.get('count_min'),
                    'count_max': task_data.get('count_max'),
                    'view_min': task_data.get('view_min'),
                    'view_max': task_data.get('view_max'),
                    'time_limit_hours': task_data.get('time_limit_hours'),
                    'time_limit_days': task_data.get('time_limit_days'),
                    'max_per_day': task_data.get('max_per_day'),
                    'max_per_month': task_data.get('max_per_month'),
                    'requires_evidence': task_data.get('requires_evidence', False),
                    'requires_approval': task_data.get('requires_approval', False),
                    'auto_complete': task_data.get('auto_complete', True),
                    'is_active': True,
                    'order': task_data.get('order', idx)
                }
                
                task_type, created = TaskType.objects.update_or_create(
                    name=task_data['name'],
                    defaults=defaults
                )
                
                if created:
                    created_count += 1
                else:
                    updated_count += 1
                
                # Progress indicator
                if (created_count + updated_count) % 20 == 0:
                    self.stdout.write(f'  → Processed {created_count + updated_count} tasks...')
                    
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'  ⚠ Skipped: {task_data["name"]} - {str(e)}'))
                continue
        
        return created_count, updated_count

    def print_summary(self):
        """Print import summary with statistics"""
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('✅ IMPORT COMPLETE!'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write('')
        
        # Count by category
        categories = {}
        for group in TaskGroup.objects.all():
            task_count = group.task_types.filter(is_active=True).count()
            if task_count > 0:
                categories[group.name] = task_count
        
        self.stdout.write('📊 TASK BREAKDOWN BY GROUP:')
        self.stdout.write('')
        total = 0
        for group_name, count in sorted(categories.items()):
            self.stdout.write(f'  {group_name:40} : {count:3} tasks')
            total += count
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'  {"TOTAL":40} : {total:3} tasks'))
        self.stdout.write('')
        
        # Breakdown by requires_evidence
        evidence_count = TaskType.objects.filter(is_active=True, requires_evidence=True).count()
        approval_count = TaskType.objects.filter(is_active=True, requires_approval=True).count()
        auto_count = TaskType.objects.filter(is_active=True, auto_complete=True).count()
        
        self.stdout.write('📌 TASK CHARACTERISTICS:')
        self.stdout.write(f'  Auto-complete tasks    : {auto_count}')
        self.stdout.write(f'  Requires evidence      : {evidence_count}')
        self.stdout.write(f'  Requires approval      : {approval_count}')
        self.stdout.write('')
        
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write('')
        self.stdout.write('✨ Next steps:')
        self.stdout.write('  1. Visit Django Admin to review tasks')
        self.stdout.write('  2. Test task assignment workflow')
        self.stdout.write('  3. Continue with registration portal integration')
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('🎉 Ready to assign tasks and award points!'))
        self.stdout.write('')