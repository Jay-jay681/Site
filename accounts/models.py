from django.db import models 
from django.contrib.auth.models import BaseUserManager ,AbstractBaseUser,PermissionsMixin


class UserManager(BaseUserManager):

    def create_user(self, phone, password=None, **extra_fields):
        if not phone:
            raise ValueError("phone number must be set")

        if self.model.objects.filter(phone=phone).exists():
            raise ValueError("A user with this phone number already exists")

        user = self.model(
            phone=phone,
            **extra_fields
        )

        user.set_password(password)
        user.save(using=self._db)

        return user

    def create_superuser(self, phone, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True")

        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True")

        return self.create_user(
            phone=phone,
            password=password,
            **extra_fields
        )
     
class CustomUser(AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        SITEADMIN = "SITEADMIN" , "Site admin"
        SUPERVISORS = "SUPERVISORS", "Supervisors"
        WORKER = "WORKER", "site worker"
        
    sitename = models.CharField(max_length=128, unique=True)
    name = models.CharField(max_length=128 , unique=True, )
    email = models.EmailField(max_length=120, unique=True, blank=True, null=True)
    phone = models.CharField(max_length=120 , unique=True)
    role = models.CharField(max_length=20, choices=Role , default=Role.SITEADMIN)
    is_staff = models.BooleanField(default= True)
    is_active = models.BooleanField(default=False)
    
    objects = UserManager()
    
    USERNAME_FIELDS = "phone"
    REQUIRED_FIELDS = ["name"]
    
    
    class Meta:
        db_table = "USERS"
        indexes = [
            models.Index(fields=["name", "is_active", "sitename"]),
        ]

    def __str__(self):
        return f"{self.phone} and {self.sitename}"
    