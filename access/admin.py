from django.contrib import admin
from .models import AttendanceRecord



# Register your models here.

@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ("user", "site", "method", "entered_at", "exited_at", "closed_by", "close_reason")
    list_filter = ("site", "method", "entered_at", "exited_at")
    search_fields = ("user__name", "site__name", "closed_by__name")
    