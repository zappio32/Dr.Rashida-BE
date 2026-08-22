from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.dependencies import require_role
from app.db.session import get_db
from app.models.appointment import Appointment
from app.models.availability import AvailabilityRule
from app.models.enums import Role
from app.models.misc import AuditLog
from app.models.notification import Notification
from app.models.service import Service
from app.models.user import DoctorProfile, User
from app.schemas.appointment import AppointmentOut, ServiceCreateRequest, ServiceOut, ServiceUpdateRequest
from app.schemas.auth import SessionUser
from app.schemas.availability import AvailabilityRuleOut, AvailabilityRuleUpsertRequest
from app.utils.ids import new_id

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _minutes(value: str) -> int:
    hours, mins = (int(part) for part in value.split(":"))
    return hours * 60 + mins


@router.get("/dashboard-summary", response_model=dict)
async def read_dashboard_summary(
    session: SessionUser = Depends(require_role("ADMIN")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    patients_count = (await db.execute(select(func.count()).select_from(User).where(User.role == Role.PATIENT))).scalar_one()
    services_count = (await db.execute(select(func.count()).select_from(Service).where(Service.active.is_(True)))).scalar_one()
    notifications_count = (await db.execute(select(func.count()).select_from(Notification))).scalar_one()
    return {"patientsCount": patients_count, "servicesCount": services_count, "notificationsCount": notifications_count}


@router.get("/appointments", response_model=dict)
async def list_all_appointments(
    session: SessionUser = Depends(require_role("ADMIN")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    query = (
        select(Appointment)
        .options(joinedload(Appointment.patient), joinedload(Appointment.service), joinedload(Appointment.payment))
        .order_by(Appointment.startsAt.desc())
    )
    result = await db.execute(query)
    appointments = result.unique().scalars().all()
    return {"appointments": [AppointmentOut.model_validate(item).model_dump(mode="json") for item in appointments]}


@router.get("/services", response_model=dict)
async def list_services(
    session: SessionUser = Depends(require_role("ADMIN")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await db.execute(select(Service).order_by(Service.createdAt.asc()))
    services = result.scalars().all()
    return {"services": [ServiceOut.model_validate(item).model_dump(mode="json") for item in services]}


@router.post("/services", response_model=dict, status_code=201)
async def create_service(
    payload: ServiceCreateRequest,
    session: SessionUser = Depends(require_role("ADMIN")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = Service(id=new_id(), **payload.model_dump())
    db.add(service)
    await db.flush()
    db.add(AuditLog(id=new_id(), userId=session.userId, action="SERVICE_CREATED", entity="Service", entityId=service.id))
    await db.commit()
    await db.refresh(service)
    return {"service": ServiceOut.model_validate(service).model_dump(mode="json")}


@router.get("/services/{service_id}", response_model=dict)
async def read_service(
    service_id: str,
    session: SessionUser = Depends(require_role("ADMIN")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = await db.get(Service, service_id)
    if not service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consultation service not found.")
    return {"service": ServiceOut.model_validate(service).model_dump(mode="json")}


@router.patch("/services/{service_id}", response_model=dict)
async def update_service(
    service_id: str,
    payload: ServiceUpdateRequest,
    session: SessionUser = Depends(require_role("ADMIN")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = await db.get(Service, service_id)
    if not service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consultation service not found.")
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(service, field, value)
    db.add(AuditLog(id=new_id(), userId=session.userId, action="SERVICE_UPDATED", entity="Service", entityId=service.id))
    await db.commit()
    await db.refresh(service)
    return {"service": ServiceOut.model_validate(service).model_dump(mode="json")}


@router.delete("/services/{service_id}", response_model=dict)
async def delete_service(
    service_id: str,
    session: SessionUser = Depends(require_role("ADMIN")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = await db.get(Service, service_id)
    if not service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consultation service not found.")

    in_use = (
        await db.execute(select(func.count()).select_from(Appointment).where(Appointment.serviceId == service_id))
    ).scalar_one()
    if in_use:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This consultation service has existing appointments and cannot be deleted. Deactivate it instead.",
        )

    await db.delete(service)
    db.add(AuditLog(id=new_id(), userId=session.userId, action="SERVICE_DELETED", entity="Service", entityId=service_id))
    await db.commit()
    return {"ok": True}


@router.get("/availability-rules", response_model=dict)
async def list_availability_rules(
    session: SessionUser = Depends(require_role("ADMIN")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await db.execute(select(AvailabilityRule).order_by(AvailabilityRule.weekday.asc()))
    rules = result.scalars().all()
    return {"rules": [AvailabilityRuleOut.model_validate(item).model_dump(mode="json") for item in rules]}


@router.post("/availability-rules", response_model=dict, status_code=201)
async def upsert_availability_rule(
    payload: AvailabilityRuleUpsertRequest,
    session: SessionUser = Depends(require_role("ADMIN")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    doctor_profile = (await db.execute(select(DoctorProfile).limit(1))).scalar_one_or_none()
    if not doctor_profile:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Doctor profile is not configured.")
    if _minutes(payload.startTime) >= _minutes(payload.endTime):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Start time must be before end time.")

    existing = (
        await db.execute(
            select(AvailabilityRule).where(
                AvailabilityRule.doctorId == doctor_profile.id, AvailabilityRule.weekday == payload.weekday
            )
        )
    ).scalar_one_or_none()

    if existing:
        for field, value in payload.model_dump().items():
            setattr(existing, field, value)
        rule = existing
        action = "AVAILABILITY_RULE_UPDATED"
    else:
        rule = AvailabilityRule(id=new_id(), doctorId=doctor_profile.id, **payload.model_dump())
        db.add(rule)
        action = "AVAILABILITY_RULE_CREATED"

    await db.flush()
    db.add(AuditLog(id=new_id(), userId=session.userId, action=action, entity="AvailabilityRule", entityId=rule.id))
    await db.commit()
    await db.refresh(rule)
    return {"rule": AvailabilityRuleOut.model_validate(rule).model_dump(mode="json")}


@router.patch("/availability-rules/{rule_id}", response_model=dict)
async def update_availability_rule(
    rule_id: str,
    payload: AvailabilityRuleUpsertRequest,
    session: SessionUser = Depends(require_role("ADMIN")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    rule = await db.get(AvailabilityRule, rule_id)
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Availability rule not found.")
    if _minutes(payload.startTime) >= _minutes(payload.endTime):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Start time must be before end time.")

    for field, value in payload.model_dump().items():
        setattr(rule, field, value)
    db.add(AuditLog(id=new_id(), userId=session.userId, action="AVAILABILITY_RULE_UPDATED", entity="AvailabilityRule", entityId=rule.id))
    await db.commit()
    await db.refresh(rule)
    return {"rule": AvailabilityRuleOut.model_validate(rule).model_dump(mode="json")}


@router.delete("/availability-rules/{rule_id}", response_model=dict)
async def delete_availability_rule(
    rule_id: str,
    session: SessionUser = Depends(require_role("ADMIN")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    rule = await db.get(AvailabilityRule, rule_id)
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Availability rule not found.")
    await db.delete(rule)
    db.add(AuditLog(id=new_id(), userId=session.userId, action="AVAILABILITY_RULE_DELETED", entity="AvailabilityRule", entityId=rule_id))
    await db.commit()
    return {"ok": True}
