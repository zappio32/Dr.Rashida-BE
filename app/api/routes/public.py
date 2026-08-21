from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.appointment import Appointment
from app.models.misc import SystemSetting
from app.models.service import Service
from app.models.user import DoctorProfile
from app.schemas.appointment import AppointmentOut, ServiceOut
from app.schemas.public import DoctorPublicOut, HomeResponse

router = APIRouter(prefix="/api/public", tags=["public"])


@router.get("/home", response_model=HomeResponse)
def read_home(db: Session = Depends(get_db)) -> HomeResponse:
    doctor = db.execute(select(DoctorProfile).limit(1)).scalar_one_or_none()
    services = db.execute(select(Service).where(Service.active.is_(True)).order_by(Service.createdAt.asc())).scalars().all()
    demo_setting = db.execute(select(SystemSetting).where(SystemSetting.key == "DEMO_MODE")).scalar_one_or_none()
    return HomeResponse(
        doctor=DoctorPublicOut.model_validate(doctor) if doctor else None,
        services=[ServiceOut.model_validate(item) for item in services],
        demoMode=bool(demo_setting.value) if demo_setting else False,
    )


@router.get("/services", response_model=dict)
def read_services(db: Session = Depends(get_db)) -> dict:
    services = db.execute(select(Service).where(Service.active.is_(True)).order_by(Service.createdAt.asc())).scalars().all()
    return {"services": [ServiceOut.model_validate(item).model_dump(mode="json") for item in services]}


@router.get("/appointments/{booking_id}", response_model=dict)
def read_appointment_by_booking_id(booking_id: str, db: Session = Depends(get_db)) -> dict:
    appointment = db.query(Appointment).filter(Appointment.bookingId == booking_id).one_or_none()
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found.")
    return {"appointment": AppointmentOut.model_validate(appointment).model_dump(mode="json")}
