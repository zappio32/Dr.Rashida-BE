"""Standalone worker: processes due ReminderJob rows and creates reminder notifications.

Run via: python -m app.workers.reminders_worker
Mirrors the original worker/reminders.ts script.
"""
from datetime import datetime, timezone

from app.db.database import SessionLocal
from app.models.appointment import Appointment
from app.models.enums import NotificationStatus
from app.models.notification import Notification, ReminderJob


def process_reminders() -> None:
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        jobs = (
            db.query(ReminderJob)
            .filter(ReminderJob.status == NotificationStatus.QUEUED, ReminderJob.runAt <= now)
            .limit(50)
            .all()
        )
        for job in jobs:
            appointment = db.get(Appointment, job.appointmentId)
            if not appointment:
                continue
            job.status = NotificationStatus.SENT
            job.attempts += 1
            db.add(
                Notification(
                    userId=appointment.patientId,
                    appointmentId=job.appointmentId,
                    channel=job.channel,
                    status=NotificationStatus.SENT,
                    subject="Appointment reminder",
                    body=(
                        f"Reminder for {appointment.bookingId} at "
                        f"{appointment.localDate} {appointment.localTime} {appointment.timezone}"
                    ),
                )
            )
            db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    process_reminders()
