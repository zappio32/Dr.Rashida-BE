from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.db.session import get_db
from app.models.appointment import Appointment
from app.models.department import Department
from app.models.misc import SystemSetting
from app.models.service import Service
from app.models.user import DoctorProfile, User
from app.schemas.appointment import AppointmentOut, ServiceOut
from app.schemas.department import DepartmentOut
from app.schemas.doctor import DoctorOut
from app.schemas.public import DoctorPublicOut, HomeResponse

router = APIRouter(prefix="/api/public", tags=["public"])


@router.get("/home", response_model=HomeResponse)
async def read_home(db: AsyncSession = Depends(get_db)) -> HomeResponse:
    doctor = (await db.execute(select(DoctorProfile).limit(1))).scalar_one_or_none()
    services = (await db.execute(select(Service).where(Service.active.is_(True)).order_by(Service.createdAt.asc()))).scalars().all()
    demo_setting = (await db.execute(select(SystemSetting).where(SystemSetting.key == "DEMO_MODE"))).scalar_one_or_none()
    return HomeResponse(
        doctor=DoctorPublicOut.model_validate(doctor) if doctor else None,
        services=[ServiceOut.model_validate(item) for item in services],
        demoMode=bool(demo_setting.value) if demo_setting else False,
    )


@router.get("/services", response_model=dict)
async def read_services(db: AsyncSession = Depends(get_db)) -> dict:
    result = await db.execute(select(Service).where(Service.active.is_(True)).order_by(Service.createdAt.asc()))
    services = result.scalars().all()
    return {"services": [ServiceOut.model_validate(item).model_dump(mode="json") for item in services]}


@router.get("/departments", response_model=dict)
async def read_departments(db: AsyncSession = Depends(get_db)) -> dict:
    result = await db.execute(select(Department).where(Department.active.is_(True)).order_by(Department.name.asc()))
    departments = result.scalars().all()
    return {"departments": [DepartmentOut.model_validate(item).model_dump(mode="json") for item in departments]}


@router.get("/doctors", response_model=dict)
async def read_doctors(departmentId: str | None = Query(default=None), db: AsyncSession = Depends(get_db)) -> dict:
    query = (
        select(DoctorProfile, User, Department)
        .join(User, User.id == DoctorProfile.userId)
        .outerjoin(Department, Department.id == DoctorProfile.departmentId)
        .where(User.isActive.is_(True))
    )
    if departmentId:
        query = query.where(DoctorProfile.departmentId == departmentId, Department.active.is_(True))
    result = await db.execute(query.order_by(User.name.asc()))
    rows = result.all()
    doctors = [
        DoctorOut(
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
            departmentName=department.name if department else None,
        ).model_dump(mode="json")
        for profile, user, department in rows
    ]
    return {"doctors": doctors}


@router.get("/appointments/{booking_id}", response_model=dict)
async def read_appointment_by_booking_id(booking_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    result = await db.execute(
        select(Appointment)
        .options(joinedload(Appointment.service), joinedload(Appointment.patient), joinedload(Appointment.payment))
        .where(Appointment.bookingId == booking_id)
    )
    appointment = result.scalar_one_or_none()
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found.")
    return {"appointment": AppointmentOut.model_validate(appointment).model_dump(mode="json")}
