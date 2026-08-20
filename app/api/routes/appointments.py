from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.dependencies import get_current_session
from app.db.session import get_db
from app.models.appointment import Appointment, AppointmentStatusHistory
from app.models.enums import AppointmentStatus, NotificationStatus
from app.models.notification import ReminderJob
from app.schemas.appointment import (
    AppointmentCreateRequest,
    AppointmentCreateResponse,
    AppointmentOut,
    AppointmentUpdateRequest,
)
from app.schemas.auth import SessionUser
from app.services.appointment_service import DoctorNotConfiguredError, SlotUnavailableError, create_appointment

router = APIRouter(prefix="/api/appointments", tags=["appointments"])


@router.post("", response_model=AppointmentCreateResponse)
def book_appointment(
    payload: AppointmentCreateRequest,
    session: SessionUser = Depends(get_current_session),
    db: Session = Depends(get_db),
) -> AppointmentCreateResponse:
    if session.role != "PATIENT":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="You must be signed in as a patient to book.")
    try:
        appointment = create_appointment(
            db,
            patient_id=session.userId,
            service_id=payload.serviceId,
            consultation_type=payload.consultationType,
            local_date=payload.localDate,
            local_time=payload.localTime,
            concern=payload.concern,
            notes=payload.notes,
        )
        return AppointmentCreateResponse(bookingId=appointment.bookingId)
    except SlotUnavailableError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Sorry, this appointment slot was just booked by another patient. Please select another available time.",
        ) from error
    except DoctorNotConfiguredError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unable to create the appointment.") from error
    except Exception as error:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unable to create the appointment.") from error


@router.get("", response_model=dict)
def list_appointments(
    session: SessionUser = Depends(get_current_session),
    db: Session = Depends(get_db),
) -> dict:
    query = select(Appointment).options(joinedload(Appointment.service), joinedload(Appointment.patient))
    if session.role == "PATIENT":
        query = query.where(Appointment.patientId == session.userId)
    elif session.role == "DOCTOR":
        query = query.where(Appointment.doctorId == session.userId)
    query = query.order_by(Appointment.startsAt.desc())
    appointments = db.execute(query).unique().scalars().all()
    return {"appointments": [AppointmentOut.model_validate(item).model_dump(mode="json") for item in appointments]}


@router.patch("/{appointment_id}", response_model=dict)
def update_appointment(
    appointment_id: str,
    payload: AppointmentUpdateRequest,
    session: SessionUser = Depends(get_current_session),
    db: Session = Depends(get_db),
) -> dict:
    appointment = db.get(Appointment, appointment_id)
    if not appointment:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to access this information.")
    if (session.role == "PATIENT" and appointment.patientId != session.userId) or (
        session.role == "DOCTOR" and appointment.doctorId != session.userId
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to access this information.")

    try:
        if payload.action == "CANCEL":
            previous_status = appointment.status
            appointment.status = AppointmentStatus.CANCELLED
            db.add(
                AppointmentStatusHistory(
                    appointmentId=appointment_id,
                    fromStatus=previous_status,
                    toStatus=AppointmentStatus.CANCELLED,
                    reason=payload.reason,
                    changedById=session.userId,
                )
            )
            db.query(ReminderJob).filter(
                ReminderJob.appointmentId == appointment_id, ReminderJob.status == NotificationStatus.QUEUED
            ).update({"status": NotificationStatus.FAILED})
            db.commit()
            db.refresh(appointment)
            return {"appointment": AppointmentOut.model_validate(appointment).model_dump(mode="json")}

        if not payload.localDate or not payload.localTime:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A new date and time are required.")

        conflict = db.execute(
            select(Appointment).where(
                Appointment.doctorId == appointment.doctorId,
                Appointment.localDate == payload.localDate,
                Appointment.localTime == payload.localTime,
                Appointment.status.notin_([AppointmentStatus.CANCELLED, AppointmentStatus.NO_SHOW]),
                Appointment.id != appointment_id,
            )
        ).scalar_one_or_none()
        if conflict:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="That appointment slot is no longer available.")

        previous_status = appointment.status
        appointment.localDate = payload.localDate
        appointment.localTime = payload.localTime
        appointment.status = AppointmentStatus.RESCHEDULED
        db.add(
            AppointmentStatusHistory(
                appointmentId=appointment_id,
                fromStatus=previous_status,
                toStatus=AppointmentStatus.RESCHEDULED,
                reason=payload.reason,
                changedById=session.userId,
            )
        )
        db.commit()
        db.refresh(appointment)
        return {"appointment": AppointmentOut.model_validate(appointment).model_dump(mode="json")}
    except HTTPException:
        db.rollback()
        raise
    except Exception as error:  # noqa: BLE001
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unable to update appointment.") from error
