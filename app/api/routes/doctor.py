from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import require_role
from app.db.session import get_db
from app.models.appointment import Appointment, AppointmentStatusHistory
from app.models.enums import AppointmentStatus, NotificationStatus
from app.models.notification import ReminderJob
from app.schemas.appointment import AppointmentOut, DoctorStatusUpdateRequest
from app.schemas.auth import SessionUser

router = APIRouter(prefix="/api/doctor", tags=["doctor"])


@router.patch("/appointments", response_model=dict)
def update_appointment_status(
    payload: DoctorStatusUpdateRequest,
    session: SessionUser = Depends(require_role("DOCTOR")),
    db: Session = Depends(get_db),
) -> dict:
    appointment = (
        db.query(Appointment)
        .filter(Appointment.id == payload.appointmentId, Appointment.doctorId == session.userId)
        .one_or_none()
    )
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found.")

    try:
        previous_status = appointment.status
        appointment.status = AppointmentStatus(payload.status)
        db.add(
            AppointmentStatusHistory(
                appointmentId=appointment.id,
                fromStatus=previous_status,
                toStatus=appointment.status,
                reason=payload.reason,
                changedById=session.userId,
            )
        )
        if appointment.status == AppointmentStatus.CANCELLED:
            db.query(ReminderJob).filter(
                ReminderJob.appointmentId == appointment.id, ReminderJob.status == NotificationStatus.QUEUED
            ).update({"status": NotificationStatus.FAILED})
        db.commit()
        db.refresh(appointment)
        return {"appointment": AppointmentOut.model_validate(appointment).model_dump(mode="json")}
    except HTTPException:
        db.rollback()
        raise
    except Exception as error:  # noqa: BLE001
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unable to update appointment.") from error
