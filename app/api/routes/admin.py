from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.dependencies import require_role
from app.core.security import hash_password
from app.db.session import get_db
from app.models.appointment import Appointment
from app.models.availability import AvailabilityRule, BlockedSlot, Holiday
from app.models.department import Department
from app.models.enums import Role
from app.models.misc import AuditLog
from app.models.notification import Notification
from app.models.service import Service
from app.models.user import DoctorProfile, User
from app.schemas.appointment import AppointmentOut, ServiceCreateRequest, ServiceOut, ServiceUpdateRequest
from app.schemas.auth import SessionUser
from app.schemas.availability import (
    AvailabilityRuleOut,
    AvailabilityRuleUpsertRequest,
    BlockedSlotCreateRequest,
    BlockedSlotOut,
    HolidayCreateRequest,
    HolidayOut,
)
from app.schemas.department import DepartmentCreateRequest, DepartmentOut, DepartmentUpdateRequest
from app.schemas.doctor import DoctorAdminOut, DoctorCreateRequest, DoctorUpdateRequest
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


@router.get("/departments", response_model=dict)
async def list_departments(
    session: SessionUser = Depends(require_role("ADMIN")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await db.execute(select(Department).order_by(Department.name.asc()))
    departments = result.scalars().all()
    return {"departments": [DepartmentOut.model_validate(item).model_dump(mode="json") for item in departments]}


@router.post("/departments", response_model=dict, status_code=201)
async def create_department(
    payload: DepartmentCreateRequest,
    session: SessionUser = Depends(require_role("ADMIN")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    existing = (await db.execute(select(Department).where(Department.name == payload.name))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A department with that name already exists.")
    department = Department(id=new_id(), **payload.model_dump())
    db.add(department)
    await db.flush()
    db.add(AuditLog(id=new_id(), userId=session.userId, action="DEPARTMENT_CREATED", entity="Department", entityId=department.id))
    await db.commit()
    await db.refresh(department)
    return {"department": DepartmentOut.model_validate(department).model_dump(mode="json")}


@router.get("/departments/{department_id}", response_model=dict)
async def read_department(
    department_id: str,
    session: SessionUser = Depends(require_role("ADMIN")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    department = await db.get(Department, department_id)
    if not department:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found.")
    return {"department": DepartmentOut.model_validate(department).model_dump(mode="json")}


@router.patch("/departments/{department_id}", response_model=dict)
async def update_department(
    department_id: str,
    payload: DepartmentUpdateRequest,
    session: SessionUser = Depends(require_role("ADMIN")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    department = await db.get(Department, department_id)
    if not department:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found.")
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(department, field, value)
    db.add(
        AuditLog(id=new_id(), userId=session.userId, action="DEPARTMENT_UPDATED", entity="Department", entityId=department.id)
    )
    await db.commit()
    await db.refresh(department)
    return {"department": DepartmentOut.model_validate(department).model_dump(mode="json")}


@router.delete("/departments/{department_id}", response_model=dict)
async def delete_department(
    department_id: str,
    session: SessionUser = Depends(require_role("ADMIN")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    department = await db.get(Department, department_id)
    if not department:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found.")

    in_use = (
        await db.execute(select(func.count()).select_from(DoctorProfile).where(DoctorProfile.departmentId == department_id))
    ).scalar_one()
    if in_use:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This department has doctors assigned to it and cannot be deleted. Deactivate it instead.",
        )

    await db.delete(department)
    db.add(
        AuditLog(id=new_id(), userId=session.userId, action="DEPARTMENT_DELETED", entity="Department", entityId=department_id)
    )
    await db.commit()
    return {"ok": True}


def _doctor_admin_out(profile: DoctorProfile, user: User, department_name: str | None) -> dict:
    return DoctorAdminOut(
        id=user.id,
        displayName=profile.displayName,
        qualification=profile.qualification,
        specialization=profile.specialization,
        experience=profile.experience,
        bio=profile.bio,
        languages=profile.languages,
        clinicAddress=profile.clinicAddress,
        timezone=profile.timezone,
        departmentId=profile.departmentId,
        departmentName=department_name,
        email=user.email,
        phone=user.phone,
        isActive=user.isActive,
        onlineFee=profile.onlineFee,
        clinicFee=profile.clinicFee,
        durationMinutes=profile.durationMinutes,
    ).model_dump(mode="json")


@router.get("/doctors", response_model=dict)
async def list_doctors(
    session: SessionUser = Depends(require_role("ADMIN")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await db.execute(
        select(DoctorProfile, User, Department)
        .join(User, User.id == DoctorProfile.userId)
        .outerjoin(Department, Department.id == DoctorProfile.departmentId)
        .order_by(User.name.asc())
    )
    rows = result.all()
    return {"doctors": [_doctor_admin_out(profile, user, department.name if department else None) for profile, user, department in rows]}


@router.post("/doctors", response_model=dict, status_code=201)
async def create_doctor(
    payload: DoctorCreateRequest,
    session: SessionUser = Depends(require_role("ADMIN")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    existing = (await db.execute(select(User).where(User.email == payload.email.lower()))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with that email already exists.")

    department = None
    if payload.departmentId:
        department = await db.get(Department, payload.departmentId)
        if not department:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Selected department was not found.")

    user = User(
        id=new_id(),
        name=payload.name,
        email=payload.email.lower(),
        passwordHash=hash_password(payload.password),
        role=Role.DOCTOR,
    )
    db.add(user)
    await db.flush()

    profile = DoctorProfile(
        id=new_id(),
        userId=user.id,
        departmentId=payload.departmentId,
        displayName=payload.name,
        qualification=payload.qualification,
        specialization=payload.specialization,
        experience=payload.experience,
        bio=payload.bio,
        languages=payload.languages,
        clinicAddress=payload.clinicAddress,
        timezone=payload.timezone,
        onlineFee=payload.onlineFee,
        clinicFee=payload.clinicFee,
        durationMinutes=payload.durationMinutes,
    )
    db.add(profile)
    await db.flush()
    db.add(AuditLog(id=new_id(), userId=session.userId, action="DOCTOR_CREATED", entity="DoctorProfile", entityId=profile.id))
    await db.commit()
    await db.refresh(profile)
    await db.refresh(user)
    return {"doctor": _doctor_admin_out(profile, user, department.name if department else None)}


async def _get_doctor_profile_or_404(db: AsyncSession, doctor_id: str) -> tuple[DoctorProfile, User]:
    row = (
        await db.execute(select(DoctorProfile, User).join(User, User.id == DoctorProfile.userId).where(User.id == doctor_id))
    ).one_or_none()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found.")
    return row


@router.get("/doctors/{doctor_id}", response_model=dict)
async def read_doctor(
    doctor_id: str,
    session: SessionUser = Depends(require_role("ADMIN")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    profile, user = await _get_doctor_profile_or_404(db, doctor_id)
    department = await db.get(Department, profile.departmentId) if profile.departmentId else None
    return {"doctor": _doctor_admin_out(profile, user, department.name if department else None)}


@router.patch("/doctors/{doctor_id}", response_model=dict)
async def update_doctor(
    doctor_id: str,
    payload: DoctorUpdateRequest,
    session: SessionUser = Depends(require_role("ADMIN")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    profile, user = await _get_doctor_profile_or_404(db, doctor_id)
    updates = payload.model_dump(exclude_unset=True)

    if "departmentId" in updates and updates["departmentId"]:
        department = await db.get(Department, updates["departmentId"])
        if not department:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Selected department was not found.")

    is_active = updates.pop("isActive", None)
    name = updates.pop("name", None)
    for field, value in updates.items():
        setattr(profile, field, value)
    if name is not None:
        profile.displayName = name
        user.name = name
    if is_active is not None:
        user.isActive = is_active

    db.add(AuditLog(id=new_id(), userId=session.userId, action="DOCTOR_UPDATED", entity="DoctorProfile", entityId=profile.id))
    await db.commit()
    await db.refresh(profile)
    await db.refresh(user)
    department = await db.get(Department, profile.departmentId) if profile.departmentId else None
    return {"doctor": _doctor_admin_out(profile, user, department.name if department else None)}


@router.delete("/doctors/{doctor_id}", response_model=dict)
async def delete_doctor(
    doctor_id: str,
    session: SessionUser = Depends(require_role("ADMIN")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    profile, user = await _get_doctor_profile_or_404(db, doctor_id)

    in_use = (
        await db.execute(select(func.count()).select_from(Appointment).where(Appointment.doctorId == doctor_id))
    ).scalar_one()
    if in_use:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This doctor has existing appointments and cannot be deleted. Deactivate the doctor instead.",
        )

    await db.delete(profile)
    db.add(AuditLog(id=new_id(), userId=session.userId, action="DOCTOR_DELETED", entity="DoctorProfile", entityId=doctor_id))
    await db.commit()
    return {"ok": True}


@router.get("/doctors/{doctor_id}/availability-rules", response_model=dict)
async def list_availability_rules(
    doctor_id: str,
    session: SessionUser = Depends(require_role("ADMIN")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    profile, _user = await _get_doctor_profile_or_404(db, doctor_id)
    result = await db.execute(
        select(AvailabilityRule).where(AvailabilityRule.doctorId == profile.id).order_by(AvailabilityRule.weekday.asc())
    )
    rules = result.scalars().all()
    return {"rules": [AvailabilityRuleOut.model_validate(item).model_dump(mode="json") for item in rules]}


@router.post("/doctors/{doctor_id}/availability-rules", response_model=dict, status_code=201)
async def upsert_availability_rule(
    doctor_id: str,
    payload: AvailabilityRuleUpsertRequest,
    session: SessionUser = Depends(require_role("ADMIN")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    profile, _user = await _get_doctor_profile_or_404(db, doctor_id)
    if _minutes(payload.startTime) >= _minutes(payload.endTime):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Start time must be before end time.")

    existing = (
        await db.execute(
            select(AvailabilityRule).where(AvailabilityRule.doctorId == profile.id, AvailabilityRule.weekday == payload.weekday)
        )
    ).scalar_one_or_none()

    if existing:
        for field, value in payload.model_dump().items():
            setattr(existing, field, value)
        rule = existing
        action = "AVAILABILITY_RULE_UPDATED"
    else:
        rule = AvailabilityRule(id=new_id(), doctorId=profile.id, **payload.model_dump())
        db.add(rule)
        action = "AVAILABILITY_RULE_CREATED"

    await db.flush()
    db.add(AuditLog(id=new_id(), userId=session.userId, action=action, entity="AvailabilityRule", entityId=rule.id))
    await db.commit()
    await db.refresh(rule)
    return {"rule": AvailabilityRuleOut.model_validate(rule).model_dump(mode="json")}


@router.patch("/doctors/{doctor_id}/availability-rules/{rule_id}", response_model=dict)
async def update_availability_rule(
    doctor_id: str,
    rule_id: str,
    payload: AvailabilityRuleUpsertRequest,
    session: SessionUser = Depends(require_role("ADMIN")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    profile, _user = await _get_doctor_profile_or_404(db, doctor_id)
    rule = await db.get(AvailabilityRule, rule_id)
    if not rule or rule.doctorId != profile.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Availability rule not found.")
    if _minutes(payload.startTime) >= _minutes(payload.endTime):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Start time must be before end time.")

    for field, value in payload.model_dump().items():
        setattr(rule, field, value)
    db.add(AuditLog(id=new_id(), userId=session.userId, action="AVAILABILITY_RULE_UPDATED", entity="AvailabilityRule", entityId=rule.id))
    await db.commit()
    await db.refresh(rule)
    return {"rule": AvailabilityRuleOut.model_validate(rule).model_dump(mode="json")}


@router.delete("/doctors/{doctor_id}/availability-rules/{rule_id}", response_model=dict)
async def delete_availability_rule(
    doctor_id: str,
    rule_id: str,
    session: SessionUser = Depends(require_role("ADMIN")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    profile, _user = await _get_doctor_profile_or_404(db, doctor_id)
    rule = await db.get(AvailabilityRule, rule_id)
    if not rule or rule.doctorId != profile.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Availability rule not found.")
    await db.delete(rule)
    db.add(AuditLog(id=new_id(), userId=session.userId, action="AVAILABILITY_RULE_DELETED", entity="AvailabilityRule", entityId=rule_id))
    await db.commit()
    return {"ok": True}


@router.get("/doctors/{doctor_id}/holidays", response_model=dict)
async def list_holidays(
    doctor_id: str,
    session: SessionUser = Depends(require_role("ADMIN")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    profile, _user = await _get_doctor_profile_or_404(db, doctor_id)
    result = await db.execute(select(Holiday).where(Holiday.doctorId == profile.id).order_by(Holiday.date.asc()))
    holidays = result.scalars().all()
    return {"holidays": [HolidayOut.model_validate(item).model_dump(mode="json") for item in holidays]}


@router.post("/doctors/{doctor_id}/holidays", response_model=dict, status_code=201)
async def create_holiday(
    doctor_id: str,
    payload: HolidayCreateRequest,
    session: SessionUser = Depends(require_role("ADMIN")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    profile, _user = await _get_doctor_profile_or_404(db, doctor_id)
    holiday = Holiday(id=new_id(), doctorId=profile.id, date=payload.date, label=payload.label)
    db.add(holiday)
    await db.flush()
    db.add(AuditLog(id=new_id(), userId=session.userId, action="HOLIDAY_CREATED", entity="Holiday", entityId=holiday.id))
    await db.commit()
    await db.refresh(holiday)
    return {"holiday": HolidayOut.model_validate(holiday).model_dump(mode="json")}


@router.delete("/doctors/{doctor_id}/holidays/{holiday_id}", response_model=dict)
async def delete_holiday(
    doctor_id: str,
    holiday_id: str,
    session: SessionUser = Depends(require_role("ADMIN")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    profile, _user = await _get_doctor_profile_or_404(db, doctor_id)
    holiday = await db.get(Holiday, holiday_id)
    if not holiday or holiday.doctorId != profile.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Holiday not found.")
    await db.delete(holiday)
    db.add(AuditLog(id=new_id(), userId=session.userId, action="HOLIDAY_DELETED", entity="Holiday", entityId=holiday_id))
    await db.commit()
    return {"ok": True}


@router.get("/doctors/{doctor_id}/blocked-slots", response_model=dict)
async def list_blocked_slots(
    doctor_id: str,
    session: SessionUser = Depends(require_role("ADMIN")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    profile, _user = await _get_doctor_profile_or_404(db, doctor_id)
    result = await db.execute(select(BlockedSlot).where(BlockedSlot.doctorId == profile.id).order_by(BlockedSlot.date.asc()))
    blocked = result.scalars().all()
    return {"blockedSlots": [BlockedSlotOut.model_validate(item).model_dump(mode="json") for item in blocked]}


@router.post("/doctors/{doctor_id}/blocked-slots", response_model=dict, status_code=201)
async def create_blocked_slot(
    doctor_id: str,
    payload: BlockedSlotCreateRequest,
    session: SessionUser = Depends(require_role("ADMIN")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    profile, _user = await _get_doctor_profile_or_404(db, doctor_id)
    blocked_slot = BlockedSlot(id=new_id(), doctorId=profile.id, date=payload.date, time=payload.time)
    db.add(blocked_slot)
    await db.flush()
    db.add(AuditLog(id=new_id(), userId=session.userId, action="BLOCKED_SLOT_CREATED", entity="BlockedSlot", entityId=blocked_slot.id))
    await db.commit()
    await db.refresh(blocked_slot)
    return {"blockedSlot": BlockedSlotOut.model_validate(blocked_slot).model_dump(mode="json")}


@router.delete("/doctors/{doctor_id}/blocked-slots/{blocked_slot_id}", response_model=dict)
async def delete_blocked_slot(
    doctor_id: str,
    blocked_slot_id: str,
    session: SessionUser = Depends(require_role("ADMIN")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    profile, _user = await _get_doctor_profile_or_404(db, doctor_id)
    blocked_slot = await db.get(BlockedSlot, blocked_slot_id)
    if not blocked_slot or blocked_slot.doctorId != profile.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Blocked slot not found.")
    await db.delete(blocked_slot)
    db.add(
        AuditLog(
            id=new_id(), userId=session.userId, action="BLOCKED_SLOT_DELETED", entity="BlockedSlot", entityId=blocked_slot_id
        )
    )
    await db.commit()
    return {"ok": True}

