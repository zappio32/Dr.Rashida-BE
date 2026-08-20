import secrets
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.appointment import Appointment, AppointmentStatusHistory
from app.models.enums import AppointmentStatus, NotificationChannel, PaymentStatus
from app.models.notification import Notification, ReminderJob
from app.models.misc import AuditLog
from app.models.payment import Payment
from app.models.service import Service
from app.models.user import DoctorProfile
from app.services.availability_service import get_available_slots

IST = ZoneInfo("Asia/Kolkata")


class SlotUnavailableError(Exception):
    pass


class DoctorNotConfiguredError(Exception):
    pass


def create_appointment(
    db: Session,
    *,
    patient_id: str,
    service_id: str,
    consultation_type: str,
    local_date: str,
    local_time: str,
    concern: str | None,
    notes: str | None,
) -> Appointment:
    settings = get_settings()
    doctor_profile = db.execute(select(DoctorProfile).limit(1)).scalar_one_or_none()
    if not doctor_profile:
        raise DoctorNotConfiguredError()

    slots = get_available_slots(db, local_date, service_id)
    if local_time not in slots:
        raise SlotUnavailableError()

    service = db.get(Service, service_id)
    if not service:
        raise SlotUnavailableError()

    local_naive = datetime.strptime(f"{local_date}T{local_time}:00", "%Y-%m-%dT%H:%M:%S")
    starts_at_ist = local_naive.replace(tzinfo=IST)
    # Stored as naive UTC wall-clock, matching the existing Prisma-created TIMESTAMP(3) columns.
    starts_at = starts_at_ist.astimezone(timezone.utc).replace(tzinfo=None)
    ends_at = starts_at + timedelta(minutes=service.durationMin)
    booking_id = f"DRA-{local_date.replace('-', '')}-{secrets.token_hex(2).upper()}"

    payment_status = PaymentStatus.PENDING if settings.PAYMENT_REQUIRED else PaymentStatus.NOT_REQUIRED

    try:
        appointment = Appointment(
            bookingId=booking_id,
            doctorId=doctor_profile.userId,
            patientId=patient_id,
            serviceId=service.id,
            consultationType=consultation_type,
            localDate=local_date,
            localTime=local_time,
            startsAt=starts_at,
            endsAt=ends_at,
            timezone=doctor_profile.timezone,
            concern=concern,
            notes=notes,
            status=AppointmentStatus.CONFIRMED,
            paymentStatus=payment_status,
        )
        db.add(appointment)
        db.flush()

        db.add(
            AppointmentStatusHistory(
                appointmentId=appointment.id,
                toStatus=AppointmentStatus.CONFIRMED,
                changedById=patient_id,
            )
        )

        if payment_status != PaymentStatus.NOT_REQUIRED:
            db.add(
                Payment(
                    appointmentId=appointment.id,
                    amount=service.fee,
                    status=PaymentStatus.PENDING,
                    provider=settings.PAYMENT_PROVIDER,
                )
            )

        body = (
            f"New appointment booked\nPatient booking: {appointment.bookingId}\n"
            f"Date: {local_date}\nTime: {local_time}\nService: {service.name}"
        )
        db.add(
            Notification(
                userId=doctor_profile.userId,
                appointmentId=appointment.id,
                channel=NotificationChannel.IN_APP,
                subject="New appointment booked",
                body=body,
            )
        )
        db.add(
            Notification(
                userId=patient_id,
                appointmentId=appointment.id,
                channel=NotificationChannel.EMAIL,
                subject="Appointment confirmation",
                body=body,
            )
        )

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        for hours in (24, 2):
            run_at = starts_at - timedelta(hours=hours)
            if run_at > now:
                db.add(
                    ReminderJob(
                        appointmentId=appointment.id,
                        channel=NotificationChannel.EMAIL,
                        runAt=run_at,
                    )
                )

        db.add(
            AuditLog(
                userId=patient_id,
                action="APPOINTMENT_CREATED",
                entity="Appointment",
                entityId=appointment.id,
            )
        )

        db.commit()
        db.refresh(appointment)
        return appointment
    except IntegrityError as error:
        db.rollback()
        print(f"[appointments] integrity error: {error}")
        raise SlotUnavailableError()
