"""Standalone worker: processes QUEUED notifications and sends them via the notification provider.

Run via: python -m app.workers.notifications_worker
Intended to be invoked on a schedule (e.g. Railway cron / scheduled job), mirroring the
original worker/notifications.ts script.
"""
from app.db.database import SessionLocal
from app.models.enums import NotificationStatus
from app.models.notification import Notification, NotificationLog
from app.models.user import User
from app.services.notification_provider import SandboxNotificationProvider


def process_notifications() -> None:
    provider = SandboxNotificationProvider()
    db = SessionLocal()
    try:
        items = (
            db.query(Notification)
            .filter(Notification.status == NotificationStatus.QUEUED)
            .limit(50)
            .all()
        )
        for item in items:
            user = db.get(User, item.userId)
            try:
                result = provider.send(to=user.email, subject=item.subject, body=item.body)
                item.status = NotificationStatus.SENT
                item.attempts += 1
                db.add(NotificationLog(notificationId=item.id, status=NotificationStatus.SENT, providerRef=result.get("providerRef")))
                db.commit()
            except Exception as error:  # noqa: BLE001
                db.rollback()
                item.status = NotificationStatus.FAILED
                item.attempts += 1
                item.lastError = str(error)
                db.add(NotificationLog(notificationId=item.id, status=NotificationStatus.FAILED, error=str(error)))
                db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    process_notifications()
