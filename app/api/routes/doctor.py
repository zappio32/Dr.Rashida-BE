from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_role
from app.db.session import get_db
from app.models.appointment import Appointment, AppointmentStatusHistory
from app.models.enums import AppointmentStatus, NotificationStatus
from app.models.notification import ReminderJob
from app.models.user import DoctorProfile
from app.schemas.appointment import AppointmentOut, DoctorStatusUpdateRequest
from app.schemas.auth import SessionUser

router = APIRouter(prefix="/api/doctor", tags=["doctor"])


@router.patch("/appointments", response_model=dict)
async def update_appointment_status(
    payload: DoctorStatusUpdateRequest,
    session: SessionUser = Depends(require_role("DOCTOR")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await db.execute(
        select(Appointment).where(
            Appointment.id == payload.appointmentId,
            or_(
                Appointment.doctorId == session.userId,
                Appointment.doctorId == select(DoctorProfile.id).where(DoctorProfile.userId == session.userId).scalar_subquery(),
            ),
        )
    )
    appointment = result.scalar_one_or_none()
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
            await db.execute(
                update(ReminderJob)
                .where(ReminderJob.appointmentId == appointment.id, ReminderJob.status == NotificationStatus.QUEUED)
                .values(status=NotificationStatus.FAILED)
            )
        await db.commit()
        await db.refresh(appointment)
        return {"appointment": AppointmentOut.model_validate(appointment).model_dump(mode="json")}
    except HTTPException:
        await db.rollback()
        raise
    except Exception as error:  # noqa: BLE001
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unable to update appointment.") from error
