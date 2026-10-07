import uuid
from django.contrib.auth.hashers import check_password, make_password

import secrets
import hashlib
from datetime import timedelta
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.core.validators import RegexValidator , MinValueValidator
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone 
from zoneinfo import available_timezones
from django.db.models import Q   

phone_validator = RegexValidator(r"^\+[1-9]\d{7,14}$",
    "Use international format,eg +23480123456789")

class Role(models.TextChoices):
    PLATFORM_ADMIN = "PLATFORMADMIN" , "Platform Admin"
    SITEADMIN = "SITEADMIN" , "Site Admin"
    SUPERVISORS = "SUPERVISORS" , "Supervisors"
    WORKER = "WORKER", "Worker"
       
       
def validate_timzone(value):
    if value not in available_timezones():
        raise ValidationError(f"'{value}' is not a valid timezone, e.g. Africa/Lagos.")


class UserManger(BaseUserManager):
    def create_user(self,phone, password=None, **extra_fields):
        if not phone:
            raise ValueError("Phone Number is required")
        user = self.model(phone=phone, **extra_fields)
        user.set_password(password)
        user.save()
        return user
        
        
    def create_superuser(self,phone, password, **extra_fields):
        extra_fields["is_staff"] = True
        extra_fields["is_superuser"] = True
        
        return self.create_user(phone, password, **extra_fields)
class Organisation(models.Model):
    id = models.UUIDField(primary_key=True , default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=120)
    is_active = models.BooleanField(default=True)
    contact_email =  models.EmailField(max_length=100, unique=True)
    
    date_created = models.DateTimeField(auto_now_add=True)
    
    
    def __str__(self):
        return f"{self.name}  ({self.contact_email})"
    
class Site(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organisation = models.ForeignKey(
        Organisation, on_delete=models.PROTECT, related_name="sites"
    )
    name = models.CharField(max_length=200)
    address = models.CharField(max_length=300, blank=True)
    hard_capacity = models.PositiveIntegerField(validators=[MinValueValidator(1)], help_text= "Maximum people allowed on site at once (from the fire safety plan).")
    timezone = models.CharField(max_length=64, default="Africa/Lagos",validators=[validate_timzone])
    is_active = models.BooleanField(default=True)
    date_created = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organisation", "name"], name="unique_site_name_per_org"
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.organisation})"
 
class CustomUser(AbstractBaseUser,  PermissionsMixin):
    PIN_ATTEMPT_LOCKDOWN_COUNTER= 5
    PIN_LOCKDOWN_TIME = timedelta(minutes=15)
    
    id = models.UUIDField(primary_key=True , default=uuid.uuid4, editable=False)
    
    # main fields
    name = models.CharField(max_length=120)
    email =  models.EmailField(max_length=100)
    phone = models.CharField(max_length=16, validators=[phone_validator] , unique=True)
    
    # also basics
    organisation = models.ForeignKey("Organisation",on_delete=models.PROTECT,related_name="users",null=True,blank=True,)
    is_active = models.BooleanField(default=True)
    is_platform_admin = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)
    
    # Now we need to link them like work they do employer and employee 
    trade = models.CharField(max_length=200, blank=True)
    employee_id = models.CharField(max_length=200, blank=True)
    employer = models.CharField(max_length=200,blank=True)
    
    # Now we have to attach user to their PiN
    pin_hash= models.CharField(max_length=128, blank=True)
    pin_failed_attempts = models.PositiveSmallIntegerField(default=0)
    pin_lockdown = models.DateTimeField(null=True, blank=True)
    
        # token revocation
    token_version = models.PositiveIntegerField(default=0)
    class Meta:
        constraints = [models.UniqueConstraint(
            fields=["organisation", "employee_id"],
            condition=~Q(employee_id=""),
            name="unique_employee_id_per_org",)]
    
    def set_pin(self, raw_pin):
        if not (raw_pin.isdigit() and len(raw_pin) == 6):
            raise ValueError("PIN must be exactly 6 digits.")
        self.pin_hash = make_password(raw_pin)
        self.pin_failed_attempts = 0
        self.pin_lockdown = None
        
    def is_pin_locked(self):
        return bool(self.pin_lockdown and self.pin_lockdown > timezone.now())
    
    def check_pin(self, raw_pin):
        if not self.pin_hash or self.is_pin_locked():
            return False

        if check_password(raw_pin, self.pin_hash):
            self.pin_failed_attempts = 0
            self.save(update_fields=["pin_failed_attempts"])
            return True

        self.pin_failed_attempts += 1
        if self.pin_failed_attempts >= self.PIN_ATTEMPT_LOCKDOWN_COUNTER:
            self.pin_lockdown = timezone.now() + self.PIN_LOCKDOWN_TIME
            self.pin_failed_attempts = 0
        self.save(update_fields=["pin_failed_attempts", "pin_lockdown"])
        return False
    
    # code revocation
    def revoke_all_tokens(self):
        CustomUser.objects.filter(pk=self.pk).update(token_version=models.F("token_version") + 1)
        self.refresh_from_db(fields=["token_version"])
        
    objects = UserManger()
    
    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = ["name"]
    
    def __str__(self):
        return f"{self.name}  ({self.phone})"



class SiteLinks(models.Model):
 
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey("accounts.CustomUser",on_delete=models.PROTECT, related_name="related_users")
    site =  models.ForeignKey(Site,on_delete=models.PROTECT, related_name="related_sites")
    roles = models.CharField(max_length=20 ,choices=Role)
    is_active = models.BooleanField(default=True)
    date_created = models.DateTimeField(auto_now_add=True)
    
    
    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "site", "roles"],  name="unique_role_per_user_per_site")]
    
    
    
    def __str__(self):
        return f"{self.user.name} - {self.roles} @ {self.site.name}"




# INVITATION MODELS THIS ONE IS JUST THE INVITATIONS BASICALLY
def token():
    return secrets.token_urlsafe(32)

def token_expires():
    return timezone.now() + timedelta(days=7)

class Invitation(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING" , "Pending Invite"
        ACCEPTED = "ACCEPTED" , "Accepted Invite"
        REJECTED = "REJECTED", "Rejected Invite"
        REVOKED = "REVOKED", "Revoked Invite"
        
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # TOKEN FOR INVITATION
    token_hash = models.CharField(max_length=64, unique=True, editable=False)
    tokens_exp = models.DateTimeField(default=token_expires)
    
    # MAIN ONE
    name = models.CharField(max_length=120)
    email =  models.EmailField(max_length=100,null=True, blank=True)
    phone = models.CharField(max_length=16, validators=[phone_validator])
    
    # INVITEE DETAILS
    role = models.CharField(max_length=200, choices=Role)
    invited_by = models.ForeignKey("accounts.CustomUser",on_delete=models.PROTECT, related_name="invited_by_user")
    organisation =  models.ForeignKey(Organisation,on_delete=models.PROTECT, related_name="invited_to_organisation")
    sites = models.ForeignKey(Site, on_delete=models.PROTECT, related_name="invited_to_site")

# INVITED MORE DETAILS
    trade = models.CharField(max_length=200, blank=True)
    employee_id = models.CharField(max_length=200, blank=True)
    
#    ACTIVITIES
    status = models.CharField(max_length=20, choices=Status, default=Status.PENDING)
    accepted_user = models.ForeignKey(
        "accounts.CustomUser", on_delete=models.PROTECT, related_name="+", null=True, blank=True
    )
    date_created = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organisation", "phone"],
                condition=Q(status="PENDING"),
                name="one_pending_invite_per_phone_per_org",
            ),
            # AI WRITTEN CODE
            models.CheckConstraint(
                condition=Q(role=Role.PLATFORM_ADMIN, sites__isnull=True)
                | (~Q(role=Role.PLATFORM_ADMIN) & Q(sites__isnull=False)),
                name="invite_site_matches_role",
            ),
        ]
        # END

    def __str__(self):
        return f"Invite {self.phone} as {self.get_role_display()} ({self.status})"

    # to hash token
    @staticmethod
    def hash_token(tokenzzz):
        return hashlib.sha256(tokenzzz.encode()).hexdigest()

    # AI WRITTEN
    @classmethod
    def issue(cls, **fields):
        raw_token = token()
        invitation = cls.objects.create(token_hash=cls.hash_token(raw_token), **fields)
        return invitation, raw_token

    @property
    def is_expired(self):
        return timezone.now() >= self.tokens_exp

    def is_usable(self):
        return self.status == self.Status.PENDING and not self.is_expired

    def revoke(self):
        self.status = self.Status.REVOKED
        self.revoked_at = timezone.now()
        self.save(update_fields=["status", "revoked_at"])
    # END