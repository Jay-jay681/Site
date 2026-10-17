from django.db import models
import uuid
from accounts.models import Site
from django.db.models import Q



class AttendanceRecord(models.Model):
    class Method(models.TextChoices):
            PIN = "PIN", "PIN"
            FACE = "FACE", "Face"
            
    id = models.UUIDField(primary_key=True, editable=False, default=uuid.uuid4)
    user = models.ForeignKey("accounts.CustomUser", related_name="user", on_delete=models.PROTECT)
    method = models.CharField(max_length=10, choices=Method)
    site = models.ForeignKey(Site, related_name="SITE", on_delete=models.PROTECT)
    method	= models.CharField(max_length=128, choices=Method)
    entered_at = models.DateTimeField(auto_now_add=True)
    exited_at= models.DateTimeField( blank= True , null=True)
    closed_by =  models.ForeignKey("accounts.CustomUser", related_name="closed_attendance_records",
            on_delete=models.PROTECT,
            null=True,
            blank=True,)
    close_reason = models.CharField(max_length=128, blank= True , null=True)
    
    class meta:
        constraints = [models.UniqueConstraint(fields=["user"], condition=Q(exited_at__isnull=True),
                name="one_open_attendance_per_user",)]
        indexes = [models.Index(fields=["site", "exited_at"], name="attendance_site_open_idx")]
        
    def __str__(self):
        status = "on site" if self.exited_at is None else "left"
        return f"{self.user.name} @ {self.site.name} ({status})"
    
    @property
    def is_open(self):
        return self.exited_at is None
    
