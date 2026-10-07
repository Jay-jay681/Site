from datetime import datetime
from typing import Optional
from uuid import UUID
from .models import SiteLinks
from ninja import Field, Schema


class LoginSchema(Schema):
    phone : str
    password : str 
    
class LoginOut(Schema):
    refresh : str
    access : str

class RefreshIn(Schema):
    refresh : str

class MessageSchema(Schema):
    message : str
    

class SiteOption(Schema):
    id: UUID
    name: str


class RoleOption(Schema):
    value: str
    label: str


class Invite(Schema):
    name: str
    phone: str = Field(..., pattern=r"^\+[1-9]\d{7,14}$")
    role: str
    site_id: Optional[UUID] = None
    email: Optional[str] = None
    trade: str = ""
    employee_id: str = ""


class InviteOut(Schema):
    id: UUID
    name: str
    phone: str
    role: str
    tokens_exp: datetime
    
class InviteAccept(Schema):
    token: str
    password: str
    
class PIN(Schema):
    pin: str = Field(..., pattern=r"^\d{6}$")
    password: str
    
class ChangePIN(Schema):
    old_pin: str = Field(..., pattern=r"^\d{6}$")
    new_pin: str = Field(..., pattern=r"^\d{6}$")
    


class SiteRole(Schema):
    site_id: UUID
    site_name: str
    role: str


class Profile(Schema):
    id: UUID
    name: str
    phone: str
    email: Optional[str] = None
    organisation: Optional[str] = None
    is_platform_admin: bool
    has_pin: bool
    trade: str
    employee_id: str
    sites: list[SiteRole]

    @staticmethod
    def resolve_organisation(obj):
        return obj.organisation.name if obj.organisation else None

    @staticmethod
    def resolve_has_pin(obj):
        return bool(obj.pin_hash)

    @staticmethod
    def resolve_sites(obj):
        links = SiteLinks.objects.filter(
            user=obj, is_active=True, site__is_active=True
        ).select_related("site")
        return [
            {"site_id": link.site.id, "site_name": link.site.name, "role": link.roles}
            for link in links
        ]