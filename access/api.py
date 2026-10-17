from time import timezone

from django.contrib.admin import site
from ninja import Router

from accounts.access.bodycode import operator_site
from .schema import LiveBoardSchema,AttendanceRecordSchema, ManualAttendanceRecordSchema,MessageSchema,AttendanceRecordSchemaIn
from .models import AttendanceRecord
from core.authentication import JwtAuth
from core.permissions import siteadminOnly, platformAdminOnly, SupervisorOnly
from accounts.models import CustomUser, Role, Site, SiteLinks
from django.db import transaction ,IntegrityError

router = Router(tags=["Access Record"])

@router.post("/clock-in", response={201:AttendanceRecordSchema, 400:MessageSchema} , auth=[SupervisorOnly()])
def recording_worker_in(request , payload:AttendanceRecordSchemaIn):
    operator = request.user
    site = operator_site(operator, payload.site_id)
        
    if site is None:
        return 404 , {"message": "site not found"}
    
    worker = CustomUser.objects.filter(employee_id=payload.employee_id, organisation=operator.organisation, is_active=True).first()
    
    if worker is None:
        return 403, {"message": "Employee ID or PIN incorrect"}

    # 3. Check the PIN
    if worker.is_pin_locked():
        return 403, {"message": "PIN locked. See your supervisor."}

    if not worker.check_pin(payload.pin):
        return 403, {"message": "Employee ID or PIN incorrect"}

    try:
        with transaction.atomic():
            site = Site.objects.select_for_update().get(id = site.id)
            
            occupancy = AttendanceRecord.objects.filter(site = site, exited_at__isnull=True).count()
            
            if occupancy >= site.hard_capacity:
                return 403, {"message": f"site is full ({occupancy}/{site.hard_capacity})"}
            
            record = AttendanceRecord.objects.create(
                user = worker,
                site = site,
                method = payload.pin,
            ) 
            
            
            
    except IntegrityError:
        return 403, {"message": "not allowed"}
    
    
    return 201, record


@router.post("/clock-out", response={200:AttendanceRecordSchema, 400:MessageSchema,403: MessageSchema, 404: MessageSchema} , auth=[SupervisorOnly()])
def recording_worker_out(request , payload:AttendanceRecordSchemaIn):
    operator = request.user
    site = operator_site(operator, payload.site_id)
    
    if site is None:
        return 404 , {"message": "site not found"}
    
    worker = CustomUser.objects.filter(employee_id=payload.employee_id, organisation=operator.organisation, is_active=True).first()
    
    if worker is None:
        return 403, {"message": "Employee ID or PIN incorrect"}
    
    if worker.is_pin_locked():
        return 403, {"message": "PIN locked. See your supervisor."}
    
    if worker.check_pin(payload.pin) is False:
        return 403, {"message": "Employee ID or PIN incorrect"}
    
    with transaction.atomic():
        record = AttendanceRecord.objects.select_for_update().filter(site = site, user = worker, exited_at__isnull=True).first()
        
        if record is None:
            return 404, {"message": "no open attendance record found for this employee"}
        
        record.exited_at = timezone.now()
        record.save(update_fields=["exited_at"])
            
    return 200, record
    
    
    
from uuid import UUID


@router.get(
    "/sites/{site_id}/board",
    response={200: LiveBoardSchema, 404: MessageSchema},
    auth=[SupervisorOnly(),platformAdminOnly()],
)
def live_board(request, site_id: UUID):
    operator = request.user
    site = operator_site(operator, site_id)

    if site is None:
        return 404, {"message": "Site not found"}

    # 2. Everyone currently inside, oldest arrival first
    people = list(
        AttendanceRecord.objects.filter(site=site, exited_at__isnull=True)
        .select_related("user", "site")
        .order_by("entered_at")
    )

    # 3. The board
    return 200, {
        "site_name": site.name,
        "occupancy": len(people),
        "hard_capacity": site.hard_capacity,
        "people": people,
    }
    
@router.post("/sites/{site_id}/close", response={200: ManualAttendanceRecordSchema, 404: MessageSchema}, auth=[SupervisorOnly(),platformAdminOnly()])
def manual_clockout(request, site_id: UUID, payload: ManualAttendanceRecordSchema):
    operator = request.user
    
    site = operator_site(operator, site_id)

    if site is None:
        return 404, {"message": "Site not found"}
    
    with transaction.atomic():

        record = AttendanceRecord.objects.select_for_update().filter(site=site, user__employee_id=payload.employee_id, exited_at__isnull=True).first()
        
        if record is None:
            return 404, {"message": "no open attendance record found for this employee"}
        
        record.exited_at = payload.exited_at
        record.closed_by = operator.name
        record.close_reason = payload.close_reason 
        record.save(update_fields=["exited_at", "closed_by", "close_reason"])
        
    return 200, record