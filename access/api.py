from datetime import timedelta
from uuid import UUID

from django.db import IntegrityError, transaction
from django.utils import timezone
from ninja import Router

from accounts.access.bodycode import operator_site
from accounts.models import CustomUser, Site, SiteLinks
from certifications.models import Certification, CertificationResponse
from core.permissions import SupervisorOnly, platformAdminOnly
from scheduling.models import Schedule

from .models import AttendanceRecord
from .schema import (
    AttendanceRecordSchema,
    AttendanceRecordSchemaIn,
    LiveBoardSchema,
    ManualAttendanceRecordSchema,
    MessageSchema,
)

router = Router(tags=["Access Record"])


@router.post(
    "/clock-in",
    response={201: AttendanceRecordSchema, 400: MessageSchema, 403: MessageSchema, 404: MessageSchema},
    auth=[SupervisorOnly(), platformAdminOnly()],
)
def recording_worker_in(request, payload: AttendanceRecordSchemaIn):
    operator = request.user

 
    site = operator_site(operator, payload.site_id)
    if site is None:
        return 404, {"message": "Site not found"}
    worker = CustomUser.objects.filter(
        employee_id=payload.employee_id, organisation=operator.organisation, is_active=True
    ).first()
    if worker is None:
        return 403, {"message": "Employee ID or PIN incorrect"}


    if worker.is_pin_locked():
        return 403, {"message": "PIN locked. See your supervisor."}

    if not worker.check_pin(payload.pin):
        return 403, {"message": "Employee ID or PIN incorrect"}

    assigned = SiteLinks.objects.filter(user=worker, site=site, is_active=True).exists()
    if not assigned:
        return 403, {"message": "You are not assigned to this site"}

    #this was kept for learning: checked ANY one certificate,
    # so a scaffolder with only First Aid got in, and workers whose
    # trade needs nothing were refused.
    # certification = CertificationResponse.objects.filter(name = worker, certification__organisation = operator.organisation, is_active=True).first()
    #
    # if not certification:
    #     return 403, {"message": "You do not have a valid certification"}
    #
    # if certification.expiration_date < timezone.now():
    #         return 403, {"message": "Your certificate has expired"}
    # if certification.status != "APPROVED":
    #     return 403, {"message": "Your certification is not approved yet"}

    if worker.trade:
        required_types = Certification.objects.filter(
            organisation=worker.organisation,
            required_for_trade=worker.trade,
            is_active=True,
        )

        for cert_type in required_types:
            has_valid = CertificationResponse.objects.filter(
                name=worker,
                certification=cert_type,
                status=CertificationResponse.Status.APPROVED,
                expiration_date__gt=timezone.now(),
                is_active=True,
            ).exists()

            if not has_valid:
                return 403, {"message": f"Your {cert_type.name} certificate is missing, not approved or expired"}


    now = timezone.now()
    early_allowance = timedelta(minutes=30)

    has_shift = Schedule.objects.filter(
        site=site,
        is_active=True,
        assignments__user=worker,
        start_time__lte=now + early_allowance,
        end_time__gte=now,
    ).exists()

    if not has_shift:
        return 403, {"message": "No shift for you at this site right now"}
    try:
        with transaction.atomic():
            site = Site.objects.select_for_update().get(id=site.id)
            occupancy = AttendanceRecord.objects.filter(site=site, exited_at__isnull=True).count()

            if occupancy >= site.hard_capacity:
                return 403, {"message": f"Site is full ({occupancy}/{site.hard_capacity}). Please wait."}

            record = AttendanceRecord.objects.create(
                user=worker,
                site=site,
                method=AttendanceRecord.Method.PIN,
            )
    except IntegrityError:
        return 403, {"message": "You are already clocked in"}

    return 201, record


@router.post(
    "/clock-out",
    response={200: AttendanceRecordSchema, 400: MessageSchema, 403: MessageSchema, 404: MessageSchema},
    auth=[SupervisorOnly(), platformAdminOnly()],
)
def recording_worker_out(request, payload: AttendanceRecordSchemaIn):
    operator = request.user

    site = operator_site(operator, payload.site_id)
    if site is None:
        return 404, {"message": "Site not found"}

    worker = CustomUser.objects.filter(
        employee_id=payload.employee_id, organisation=operator.organisation, is_active=True
    ).first()
    if worker is None:
        return 403, {"message": "Employee ID or PIN incorrect"}

    if worker.is_pin_locked():
        return 403, {"message": "PIN locked. See your supervisor."}

    if not worker.check_pin(payload.pin):
        return 403, {"message": "Employee ID or PIN incorrect"}

    with transaction.atomic():
        record = (
            AttendanceRecord.objects.select_for_update()
            .filter(site=site, user=worker, exited_at__isnull=True)
            .first()
        )

        if record is None:
            return 404, {"message": "You are not clocked in here"}

        record.exited_at = timezone.now()
        record.save(update_fields=["exited_at"])

    return 200, record


@router.get(
    "/sites/{site_id}/board",
    response={200: LiveBoardSchema, 404: MessageSchema},
    auth=[SupervisorOnly(), platformAdminOnly()],
)
def live_board(request, site_id: UUID):
    operator = request.user

    site = operator_site(operator, site_id)
    if site is None:
        return 404, {"message": "Site not found"}

    # Everyone currently inside, oldest arrival first
    people = list(
        AttendanceRecord.objects.filter(site=site, exited_at__isnull=True)
        .select_related("user", "site")
        .order_by("entered_at")
    )

    return 200, {
        "site_name": site.name,
        "occupancy": len(people),
        "hard_capacity": site.hard_capacity,
        "people": people,
    }


@router.post(
    "/sites/{site_id}/close",
    response={200: AttendanceRecordSchema, 400: MessageSchema, 404: MessageSchema},
    auth=[SupervisorOnly(), platformAdminOnly()],
)
def manual_clockout(request, site_id: UUID, payload: ManualAttendanceRecordSchema):
    operator = request.user

    site = operator_site(operator, site_id)
    if site is None:
        return 404, {"message": "Site not found"}

    with transaction.atomic():
        record = (
            AttendanceRecord.objects.select_for_update()
            .filter(site=site, user__employee_id=payload.employee_id, exited_at__isnull=True)
            .first()
        )

        if record is None:
            return 404, {"message": "No open attendance record found for this employee"}

        if payload.exited_at < record.entered_at:
            return 400, {"message": "Exit time cannot be before entry time"}

        if payload.exited_at > timezone.now():
            return 400, {"message": "Exit time cannot be in the future"}

        record.exited_at = payload.exited_at
        record.closed_by = operator
        record.close_reason = payload.close_reason
        record.save(update_fields=["exited_at", "closed_by", "close_reason"])

    return 200, record