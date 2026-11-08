from django.contrib import admin

from scheduling.models import Schedule, ScheduleLinks

# Register your models here.
@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ('name', 'organisation', 'site', 'start_time', 'end_time', 'is_active')
    list_filter = ('organisation', 'site', 'is_active')
    search_fields = ('name', 'description')
    
    def has_add_permission(self, request):
        return False

@admin.register(ScheduleLinks)
class ScheduleLinksAdmin(admin.ModelAdmin):
    list_display = ('schedule', 'user', 'assigned_by', 'assigned_at')
    list_filter = ('schedule', 'user', 'assigned_by')
    search_fields = ('schedule__name', 'user__name', 'assigned_by__name')
    
    def has_add_permission(self, request):
        return False

    