import uuid

from django.db import models

# Create your models here.

class Schedule(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    organisation = models.ForeignKey('accounts.Organisation', on_delete=models.PROTECT)
    site = models.ForeignKey('accounts.Site', on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey('accounts.CustomUser', on_delete=models.PROTECT)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name}"

class ScheduleLinks(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    schedule = models.ForeignKey(Schedule, on_delete=models.PROTECT, related_name='assignments')
    user = models.ForeignKey('accounts.CustomUser', on_delete=models.PROTECT, related_name='schedule_links')
    assigned_by = models.ForeignKey('accounts.CustomUser', on_delete=models.PROTECT, related_name='schedule_links_created')
    assigned_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['schedule', 'user'], name='unique_worker_per_schedule')
        ]

    def __str__(self):
        return f"{self.schedule.name} - {self.user.name}"