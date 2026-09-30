import uuid

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone

phone_validator = RegexValidator(r"^\+[1-9]\d{7,14}$",
                                 "Use international format,eg +23480123456789"
                                )

class UserManger(BaseUserManager):
    def create_user(self,phone, password=None, **extra_fields):
        if not phone:
            raise ValueError("Phone Number is required")
        user = self.model(phone=phone, **extra_fields)
        user.set_password(password)
        user.save()
        
        
    def create_superuser(self,phone, password, **extra_fields):
        extra_fields["is_staff"] = True
        extra_fields["is_superuser"] = True
        
        return self.create_user(phone, password, **extra_fields)
    
class CustomUser(AbstractBaseUser):
    id = models.UUIDField(primary_key=True , default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=120,null=True, blank=True)
    email =  models.EmailField(max_length=100,  unique=True)
    phone = models.CharField(validators=[phone_validator] , unique=True)
    
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)
    
    objects = UserManger()
    
    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.phone})"
    
                    
    