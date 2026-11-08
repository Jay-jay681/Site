from typing import Optional

from django.db import IntegrityError, transaction , IntegrityError
from ninja import Router

from accounts.models import CustomUser
from certifications.models import Certification ,CertificationResponse
from certifications.schema import acceptIn, CertificationSchemaOut, MessageSchema, CertificationSchemaIn , CertifiactionResponseSchemaIn, CertifiactionResponseSchemaOut
from core.permissions import platformAdminOnly , SupervisorOnly, WorkerOnly
from uuid import UUID
from django.utils import timezone

router = Router(tags=["Certifications"])

@router.post("/certifications", response={201: CertificationSchemaOut, 400: MessageSchema} , auth = platformAdminOnly())
def create_certification(request, payload: CertificationSchemaIn):
    user = request.auth
    
    if user.organisation is None:
        return 400, {"message": "User does not belong to an organisation"}
    

    certification = Certification.objects.create(
        name=payload.name,
        description=payload.description,
        required_for_trade=payload.required_for_trade,
        organisation=user.organisation,
        created_by=user
    )
    
    return 201, certification

@router.get("/certifications", response=list[CertificationSchemaOut] , auth = platformAdminOnly())
def certification(request,):
    user = request.auth
    
    certificate = Certification.objects.filter(organisation=user.organisation, is_active = True)
    
    return certificate
    
    
    

@router.post(
    "/certificate-response/{certificate_response_id}",
    response={201: CertifiactionResponseSchemaOut, 400: MessageSchema, 404: MessageSchema},
    auth=[WorkerOnly(), platformAdminOnly()],
)
def certificate_response(request, certificate_response_id: UUID, payload: CertifiactionResponseSchemaIn):
    user = request.auth

    certificate = Certification.objects.filter(
        id=certificate_response_id, organisation=user.organisation
    ).first()

    if certificate is None:
        return 404, {"message": "Certification not found"}

    if payload.expiration_date < timezone.now():
        return 400, {"message": "Your certificate has expired"}

    certificate_responses = CertificationResponse.objects.create(
        certification=certificate,
        name=user,
        expiration_date=payload.expiration_date,
        type=payload.type,
        certificate_number=payload.certificate_number,
    )
    
    print(certificate_responses.id)

    return 201, certificate_responses



@router.get("/certificate-responses", response=list[CertifiactionResponseSchemaOut], auth=platformAdminOnly())
def get_certificate_responses(
    request,
    status: Optional[CertificationResponse.Status] = None,
    worker: Optional[str] = None,
    certification: Optional[str] = None,
):
    user = request.auth

    responses = CertificationResponse.objects.filter(
        certification__organisation=user.organisation
    ).select_related("certification", "name")

    if status:
        responses = responses.filter(status=status)

    if worker:
        worker = worker.strip()
        responses = responses.filter(name__name__icontains=worker)

    if certification:
        certification = certification.strip()
        responses = responses.filter(certification__name__icontains=certification)
    
    return responses

@router.post(
    "/certificate-response/{certificate_response_id}/accept-admin",
    response={200: MessageSchema, 400: MessageSchema, 404: MessageSchema},
    auth=platformAdminOnly(),
)
def certificate_response_accept(request, certificate_response_id: UUID):
    user = request.auth
    
    with transaction.atomic():
        certificate = CertificationResponse.objects.select_for_update().filter(
            id=certificate_response_id , certification__organisation=user.organisation , status= CertificationResponse.Status.PENDING,
        ).first()
        
            
        if certificate is None:
            return 404, {"message": "Certification not found"}

            
        certificate.status = CertificationResponse.Status.APPROVED
        certificate.save()
        
    return 200 ,{"message": "status updated"}
    
@router.post(
    "/certificate-response/{certificate_response_id}/reject-admin",
    response={200: MessageSchema, 400: MessageSchema, 404: MessageSchema},
    auth=platformAdminOnly(),
)
def certificate_response_reject(request, certificate_response_id: UUID):
    user = request.auth
    
    with transaction.atomic():
        certificate = CertificationResponse.objects.select_for_update().filter(
            id=certificate_response_id , certification__organisation=user.organisation , status= CertificationResponse.Status.PENDING,
        ).first()
        
            
        if certificate is None:
            return 404, {"message": "Certification not found"}

            
        certificate.status = CertificationResponse.Status.REJECTED
        certificate.save()
        
    return 200 ,{"message": "status updated"}

@router.get("/suggest/certifications", response=list[str], auth=platformAdminOnly())
def suggest_certifications(request, q: str):
    user = request.auth

    if len(q) < 2:
        return []

    names = (
        Certification.objects.filter(
            organisation=user.organisation, name__icontains=q, is_active=True
        )
        .order_by("name")
        .values_list("name", flat=True)[:5]
    )
    return list(names)


@router.get("/suggest/workers", response=list[str], auth=platformAdminOnly())
def suggest_workers(request, q: str):
    user = request.auth

    if len(q) < 2:
        return []

    names = (
        CustomUser.objects.filter(
            organisation=user.organisation, name__icontains=q, is_active=True
        )
        .order_by("name")
        .values_list("name", flat=True)[:5]
    )
    return list(names)
        
   

    
# eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI1MGUwMmEzNS1hZTdkLTQyYzAtODE3NC0xY2FmNTVkNGYzNmYiLCJ0b2tlbl90eXBlIjoiYWNjZXNzIiwidmVyIjowLCJpYXQiOjE3OTI0NDY4NDMsImV4cCI6MTc5MzM0Njg0M30.3ZwkRyvzjt0JYojvRoTMKgzuSoToiwzjxf4-f166aU8