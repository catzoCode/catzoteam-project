from django.contrib import admin
from .models import DailyPoints, MonthlyIncentive, PointsProjection, WarningLetter

@admin.register(DailyPoints)
class DailyPointsAdmin(admin.ModelAdmin):
    list_display = ['user', 'date', 'points', 'grooming_count', 'cat_service_count']
    list_filter = ['date', 'user__branch']
    search_fields = ['user__username']
    date_hierarchy = 'date'

@admin.register(MonthlyIncentive)
class MonthlyIncentiveAdmin(admin.ModelAdmin):
    list_display = ['user', 'month', 'total_points', 'incentive_earned', 'bonus_earned', 'paid']
    list_filter = ['month', 'paid', 'warning_issued']
    search_fields = ['user__username']
    date_hierarchy = 'month'
    
    actions = ['mark_as_paid', 'calculate_incentives']
    
    def mark_as_paid(self, request, queryset):
        from datetime import date
        queryset.update(paid=True, paid_date=date.today())
        self.message_user(request, f"{queryset.count()} incentives marked as paid.")
    mark_as_paid.short_description = "Mark selected as paid"
    
    def calculate_incentives(self, request, queryset):
        for incentive in queryset:
            incentive.calculate_incentive()
        self.message_user(request, f"{queryset.count()} incentives calculated.")
    calculate_incentives.short_description = "Recalculate incentives"

@admin.register(PointsProjection)
class PointsProjectionAdmin(admin.ModelAdmin):
    list_display = ['user', 'date', 'daily_average', 'projected_monthly_total', 'on_track']
    list_filter = ['date', 'on_track', 'will_reach_warning']
    search_fields = ['user__username']

@admin.register(WarningLetter)
class WarningLetterAdmin(admin.ModelAdmin):
    list_display = ['user', 'month', 'reason', 'points_achieved', 'issued_date', 'acknowledged']
    list_filter = ['reason', 'issued_date', 'acknowledged']
    search_fields = ['user__username', 'description']