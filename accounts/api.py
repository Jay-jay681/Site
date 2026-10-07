from django.utils import timezone
from ninja import Router
from .schema import Profile, ChangePIN,PIN,Invite,InviteOut,InviteAccept, LoginOut , LoginSchema ,MessageSchema,RefreshIn, SiteOption,RoleOption
from core.token import create_access_token , create_refresh_token ,decode
from django.contrib.auth import authenticate
from .models import CustomUser ,Invitation ,Role, SiteLinks
from django.db import transaction ,IntegrityError
from core.permissions import platformAdminOnly
from core.authentication import JwtAuth    
from core.permissions import allowed_roles, allowed_sites
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .utils import is_weak_pin


# router = Router(tags="Accounts")

router = Router(tags=["Accounts"])

@router.post("/auth/login" , response={200 : LoginOut , 401 :MessageSchema})
def login(request , payload : LoginSchema):
    user = authenticate(request , username= payload.phone , password =payload.password)
    
    if user is None:
        return 401, {"message": "Invalid credentials"}

    return 200, {
        "access": create_access_token(user),
        "refresh": create_refresh_token(user),
    }
    
@router.post("/auth/refresh", response={200: LoginOut, 401:MessageSchema})
def refreshToken(request, payload:RefreshIn):
    results = decode(payload.refresh)
    
    if results is None or results.get("token_type") != "refresh":
        return 401, {"message": "Invalid or expired refresh token"}
    if results.get("ver") != user.token_version:
        return 401, {"message": "Invalid or expired refresh token"}
    user = CustomUser.objects.filter(id=results.get("sub") , is_active=True).first()
    
    if user is None:
        return 401, {"message": "Invalid or expired refresh token"}

    return 200, {
        "access": create_access_token(user),
        "refresh": create_refresh_token(user),
    }
    
    
@router.get(
    "/invite/roles",
    auth=JwtAuth(),
    response={200: list[RoleOption], 403: MessageSchema},
)
def invite_roles(request):
    roles = allowed_roles(request.auth)

    if not roles:
        return 403, {"message": "You are not allowed to send invitations"}

    return 200, [{"value": r.value, "label": r.label} for r in roles]


@router.get(
    "/invite/sites",
    auth=JwtAuth(),
    response={200: list[SiteOption], 403: MessageSchema},
)
def invite_sites(request):
    if not allowed_roles(request.auth):
        return 403, {"message": "You are not allowed to send invitations"}

    return 200, allowed_sites(request.auth)


@router.post(
    "/invites",
    auth=JwtAuth(),
    response={201: InviteOut, 400: MessageSchema, 403: MessageSchema, 404: MessageSchema},
)
def send_invite(request, payload: Invite):
    user = request.auth
    print("ROLE SENT:", repr(payload.role))
    print("USER:", user.phone, "| ORG:", user.organisation)
    print("ALLOWED:", [r.value for r in allowed_roles(user)])

    if payload.role not in allowed_roles(user):
        return 403, {"message": "You are not allowed to invite this role"}

    if payload.role == Role.PLATFORM_ADMIN:
        if payload.site_id is not None:
            return 400, {"message": "Platform admin invites must not include a site"}
        site = None
    else:
        if payload.site_id is None:
            return 400, {"message": "Choose a site for this role"}
        site = allowed_sites(user).filter(id=payload.site_id).first()
        if site is None:
            return 404, {"message": "Site not found"}

    if CustomUser.objects.filter(phone=payload.phone).exists():
        return 400, {"message": "A user with this phone number already exists"}

    try:
        with transaction.atomic():
            invite, raw_token = Invitation.issue(
                name=payload.name,
                email=payload.email,
                phone=payload.phone,
                role=payload.role,
                trade=payload.trade,
                employee_id=payload.employee_id,
                organisation=user.organisation,
                sites=site,
                invited_by=user,
            )
    except IntegrityError:
        return 400, {"message": "A pending invitation already exists for this phone number"}

    print(f"[DEV SMS] To {invite.phone}: http://127.0.0.1:8000/activate?token={raw_token}")
    return 201, invite
    
    
@router.post(
    "/invites/accept",
    response={200: MessageSchema, 400: MessageSchema, 404: MessageSchema},
)
def accept_invite(request, payload: InviteAccept):
    try:
        validate_password(payload.password)
    except ValueError as e:
        return 400, {"message": "".join(e.messages)}
    
    token_hash = Invitation.hash_token(payload.token)
    
    try:
        with transaction.atomic():
            invite = Invitation.objects.select_for_update().filter(token_hash=token_hash).first()
            if invite is None:
                return 404, {"message": "Invalid invitation link"}

            if not invite.is_usable():
                return 400, {"message": "This invitation has expired or has already been used"}

            user = CustomUser.objects.create_user(
                phone=invite.phone,
                password=payload.password,
                name=invite.name,
                email=invite.email,
                role=invite.role,
                trade=invite.trade,
                employee_id=invite.employee_id,
                organisation=invite.organisation,
            )
            if invite.role != Role.PLATFORM_ADMIN:
                SiteLinks.objects.create(user=user, site=invite.sites, roles=invite.role)
            invite.status = Invitation.Status.ACCEPTED
            invite.accepted_user = user
            invite.accepted_at = timezone.now()
            invite.save(update_fields=["status", "accepted_user", "accepted_at"])
    except IntegrityError:
                return 400, {"message": "An account with this phone number already exists"}

    return 200, {
    "access": create_access_token(user),
    "refresh": create_refresh_token(user),
    }
    
@router.post("/set-pin", response={200: MessageSchema, 400: MessageSchema}, auth=JwtAuth())
def set_pin(request, payload: PIN):
    user = request.auth

    if user.pin_hash:
        return 400, {"message": "PIN already set. Use change-pin instead."}

    if not user.check_password(payload.password):
        return 400, {"message": "Incorrect password"}

    if is_weak_pin(payload.pin):
        return 400, {"message": "This PIN is too easy to guess. Choose another."}

    try:
        user.set_pin(payload.pin)
    except ValueError as e:
        return 400, {"message": str(e)}

    user.save(update_fields=["pin_hash", "pin_failed_attempts", "pin_lockdown"])

    return 200, {"message": "PIN set successfully"}


@router.post("/change-pin", response={200: MessageSchema, 400: MessageSchema}, auth=JwtAuth())
def change_pin(request, payload: ChangePIN):
    user = request.auth

    if not user.pin_hash:
        return 400, {"message": "No PIN set yet. Use set-pin first."}

    if user.is_pin_locked():
        return 400, {"message": "PIN is locked. Try again later."}

    if not user.check_pin(payload.old_pin):
        return 400, {"message": "Incorrect PIN"}

    if payload.new_pin == payload.old_pin:
        return 400, {"message": "New PIN must be different from the old one."}

    if is_weak_pin(payload.new_pin):
        return 400, {"message": "This PIN is too easy to guess. Choose another."}

    try:
        user.set_pin(payload.new_pin)
    except ValueError as e:
        return 400, {"message": str(e)}

    user.save(update_fields=["pin_hash", "pin_failed_attempts", "pin_lockdown"])

    return 200, {"message": "PIN changed successfully"}
     
@router.get("/me", response={200:Profile} , auth=JwtAuth())
def profile(request):
    return 200 , request.user
#   "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI1MGUwMmEzNS1hZTdkLTQyYzAtODE3NC0xY2FmNTVkNGYzNmYiLCJ0b2tlbl90eXBlIjoicmVmcmVzaCIsInZlciI6MCwiaWF0IjoxNzkxMTk5NTk5LCJleHAiOjE3OTM3OTE1OTl9.OJUehiW2dSTdbkaPkfUiHq62QJOcl8BylG-nlFNEq3w",
#   "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI1MGUwMmEzNS1hZTdkLTQyYzAtODE3NC0xY2FmNTVkNGYzNmYiLCJ0b2tlbl90eXBlIjoiYWNjZXNzIiwidmVyIjowLCJpYXQiOjE3OTExOTk1OTksImV4cCI6MTc5MjA5OTU5OX0.81WcwMogUAyj9tH0_VKGe0K8y84c-F3IwpgsIcPwTUQ"
# }

# eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOI1MGUwMmEzNS1hZTdkLTQyYzAtODE3NC0xY2FmNTVkNGYzNmYiLCJ0b2tlbl90eXBlIjoiYWNjZXNzIiwidmVyIjowLCJpYXQiOjE3OTExOTk1OTksImV4cCI6MTc5MjA5OTU5OX0.81WcwMogUAyj9tH0_VKGe0K8y84c-F3IwpgsIcPwTUQ

# To +2348123456788: http://127.0.0.1:8000/activate?token=vzb-RjLhvzb7esD5tikO3GX81s2NDitxfHc8RXdIJ58