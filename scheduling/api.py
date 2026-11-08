
from uuid import UUID

from django.db import transaction ,IntegrityError
from django.utils import timezone
from ninja import Router


from accounts.access.bodycode import operator_site
from accounts.models import CustomUser
from core.permissions import WorkerOnly, siteadminOnly , platformAdminOnly
from .models import Schedule, ScheduleLinks
from .schema import ScheduleLinksSchemaIn, ScheduleSchemaIn, mySchedule,ScheduleSchemaOut, MessageSchema, scheduleLinksSchemaOut


router = Router(tags=["Scheduling"])

@router.post("/shifts/{site_id}", response={201: ScheduleSchemaOut, 400: MessageSchema} , auth =[siteadminOnly(), platformAdminOnly()])
def create_schedule(request, payload: ScheduleSchemaIn , site_id: UUID):
    user = request.auth
    
    site = operator_site(user, site_id)
    if site is None:
        return 404, {"message": "Site not found"}

    if not user:
        return 400, {"message": "User is not authorized to create a schedule"}
    if user.organisation is None:
        return 400, {"message": "User does not belong to an organisation"}
    
    if payload.start_time > timezone.now():
        return 400, {"message": "Start time must be in the past"}
    
    if payload.start_time >= payload.end_time:
        return 400, {"message": "Start time must be before end time"}

    schedule = Schedule.objects.create(
        name=payload.name,
        description=payload.description,
        start_time=payload.start_time,
        end_time=payload.end_time,
        organisation=user.organisation,
        created_by=user,
        site=site
    )

    return 201, schedule

@router.post(
    "/shifts/{schedule_id}/assign",
    response={201: scheduleLinksSchemaOut, 400: MessageSchema, 404: MessageSchema},
    auth=[siteadminOnly(), platformAdminOnly()],
)
def create_schedule_for_user(request, payload: ScheduleLinksSchemaIn, schedule_id: UUID):
    user = request.auth

    schedule = Schedule.objects.filter(
        id=schedule_id, organisation=user.organisation, is_active=True
    ).first()
    if schedule is None:
        return 404, {"message": "Schedule not found"}

    worker = CustomUser.objects.filter(
        id=payload.user_id, organisation=user.organisation, is_active=True
    ).first()
    if worker is None:
        return 404, {"message": "Worker not found"}

    try:
        with transaction.atomic():
            assignment = ScheduleLinks.objects.create(
                schedule=schedule,
                user=worker,
                assigned_by=user,
            )
    except IntegrityError:
        return 400, {"message": "Worker is already assigned to this shift"}

    return 201, assignment

@router.get("/shifts/{schedule_id}/workers", response={200 : list[scheduleLinksSchemaOut] , 404: MessageSchema}, auth=[siteadminOnly(), platformAdminOnly()])
def get_workers_for_schedule(request, schedule_id: UUID):
    user = request.auth

    schedule = Schedule.objects.filter(
        id=schedule_id, organisation=user.organisation, is_active=True
    ).first()
    if schedule is None:
        return 404, {"message": "Schedule not found"}

    assignments = ScheduleLinks.objects.filter(schedule=schedule).select_related(
        "user", "assigned_by", "schedule", "schedule__site" , "schedule__organisation","schedule__created_by",
    )

    return assignments


@router.get("/know-your-shift", response=list[mySchedule], auth=[WorkerOnly(),platformAdminOnly()])
def know_your_shift(request):
    user = request.auth

    shifts = Schedule.objects.filter(
        assignments__user=user,
        is_active=True,
        end_time__gte=timezone.now(),
    ).select_related("site").order_by("start_time")

    return shifts

@router.delete("/shifts/{schedule_id}/unassign/{user_id}", response={200: MessageSchema, 404: MessageSchema}, auth=[siteadminOnly(), platformAdminOnly()])
def unassign_worker_from_schedule(request, schedule_id: UUID, user_id: UUID):
    user = request.auth

    schedule = Schedule.objects.filter(
        id=schedule_id, organisation=user.organisation, is_active=True
    ).first()
    if schedule is None:
        return 404, {"message": "Schedule not found"}

    assignment = ScheduleLinks.objects.filter(schedule=schedule, user_id = user_id).first()
    if assignment is None:
        return 404, {"message": "Worker is not assigned to this shift"}

    assignment.delete()

    return 200, {"message": "Worker unassigned from shift successfully"}

@router.delete("/shifts/{schedule_id}/cancel", response={200: MessageSchema, 404: MessageSchema}, auth=[siteadminOnly(), platformAdminOnly()])
def delete_schedule(request, schedule_id: UUID):
    user = request.auth

    schedule = Schedule.objects.filter(
        id=schedule_id, organisation=user.organisation, is_active=True
    ).first()
    if schedule is None:
        return 404, {"message": "Schedule not found"}

    schedule.is_active = False
    schedule.save(update_fields=["is_active"])

    return 200, {"message": "Schedule cancelled successfully"}
#  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI1MGUwMmEzNS1hZTdkLTQyYzAtODE3NC0xY2FmNTVkNGYzNmYiLCJ0b2tlbl90eXBlIjoiYWNjZXNzIiwidmVyIjowLCJpYXQiOjE3OTM2NjI4ODYsImV4cCI6MTc5NDU2Mjg4Nn0.tLQ-IZpKZhGiqGtsTrEzNgqit0bhFAo5NlVy7ESG7NE"
# 94e5015b-7ba1-4f16-aeac-6b6ad921603e
# 50e02a35-ae7d-42c0-8174-1caf55d4f36f