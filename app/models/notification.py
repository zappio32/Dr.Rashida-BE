from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base
from app.models.enums import NotificationChannel, NotificationStatus
from app.utils.ids import new_id

NotificationChannelEnum = Enum(
    NotificationChannel, name="NotificationChannel", create_type=False, values_callable=lambda e: [m.value for m in e]
)
NotificationStatusEnum = Enum(
    NotificationStatus, name="NotificationStatus", create_type=False, values_callable=lambda e: [m.value for m in e]
)


class Notification(Base):
    __tablename__ = "Notification"
    __table_args__ = (Index("Notification_status_createdAt_idx", "status", "createdAt"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    userId: Mapped[str] = mapped_column(String, ForeignKey("User.id", ondelete="CASCADE"), nullable=False)
    appointmentId: Mapped[str | None] = mapped_column(String, ForeignKey("Appointment.id", ondelete="SET NULL"), nullable=True)
    channel: Mapped[NotificationChannel] = mapped_column(NotificationChannelEnum, nullable=False)
    status: Mapped[NotificationStatus] = mapped_column(NotificationStatusEnum, nullable=False, default=NotificationStatus.QUEUED)
    subject: Mapped[str] = mapped_column(String, nullable=False)
    body: Mapped[str] = mapped_column(String, nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    lastError: Mapped[str | None] = mapped_column(String, nullable=True)
    createdAt: Mapped[datetime] = mapped_column(DateTime(), server_default=func.now())
    updatedAt: Mapped[datetime] = mapped_column(DateTime(), default=func.now(), onupdate=func.now())

    user: Mapped["User"] = relationship()
    logs: Mapped[list["NotificationLog"]] = relationship(back_populates="notification")


class NotificationLog(Base):
    __tablename__ = "NotificationLog"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    notificationId: Mapped[str] = mapped_column(String, ForeignKey("Notification.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[NotificationStatus] = mapped_column(NotificationStatusEnum, nullable=False)
    providerRef: Mapped[str | None] = mapped_column(String, nullable=True)
    error: Mapped[str | None] = mapped_column(String, nullable=True)
    createdAt: Mapped[datetime] = mapped_column(DateTime(), server_default=func.now())

    notification: Mapped["Notification"] = relationship(back_populates="logs")


class ReminderJob(Base):
    __tablename__ = "ReminderJob"
    __table_args__ = (
        UniqueConstraint("appointmentId", "channel", "runAt", name="ReminderJob_appointmentId_channel_runAt_key"),
        Index("ReminderJob_status_runAt_idx", "status", "runAt"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    appointmentId: Mapped[str] = mapped_column(String, ForeignKey("Appointment.id", ondelete="CASCADE"), nullable=False)
    channel: Mapped[NotificationChannel] = mapped_column(NotificationChannelEnum, nullable=False)
    runAt: Mapped[datetime] = mapped_column(DateTime(), nullable=False)
    status: Mapped[NotificationStatus] = mapped_column(NotificationStatusEnum, nullable=False, default=NotificationStatus.QUEUED)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    appointment: Mapped["Appointment"] = relationship()
