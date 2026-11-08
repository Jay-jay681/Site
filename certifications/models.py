from django.db import models
import uuid

# Create your models here.
class Certification(models.Model):
    id  = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)  
    name = models.CharField(max_length=255)
    required_for_trade = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True,)
    organisation = models.ForeignKey('accounts.Organisation', on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey('accounts.CustomUser', on_delete=models.PROTECT)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name}"
    
class CertificationResponse(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        
    id  = models.UUIDField(primary_key=True, default=uuid.uuid4 , editable= False)
    name = models.ForeignKey('accounts.CustomUser', on_delete=models.PROTECT)
    certification = models.ForeignKey(Certification , on_delete=models.PROTECT) 
    expiration_date = models.DateTimeField()
    type =  models.CharField(max_length=255)
    certificate_number =  models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    is_active = models.BooleanField(default=True)
    

