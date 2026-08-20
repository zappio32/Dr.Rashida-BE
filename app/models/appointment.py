from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base
from app.models.enums import AppointmentStatus, PaymentStatus
from app.utils.ids import new_id

AppointmentStatusEnum = Enum(
    AppointmentStatus, name="AppointmentStatus", create_type=False, values_callable=lambda e: [m.value for m in e]
)
PaymentStatusEnum = Enum(
    PaymentStatus, name="PaymentStatus", create_type=False, values_callable=lambda e: [m.value for m in e]
)


class Appointment(Base):
    __tablename__ = "Appointment"
    __table_args__ = (
        UniqueConstraint("doctorId", "localDate", "localTime", name="Appointment_doctorId_localDate_localTime_key"),
        Index("Appointment_patientId_startsAt_idx", "patientId", "startsAt"),
        Index("Appointment_doctorId_startsAt_idx", "doctorId", "startsAt"),
        Index("Appointment_status_startsAt_idx", "status", "startsAt"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    bookingId: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    doctorId: Mapped[str] = mapped_column(String, ForeignKey("User.id"), nullable=False)
    patientId: Mapped[str] = mapped_column(String, ForeignKey("User.id"), nullable=False)
    serviceId: Mapped[str] = mapped_column(String, ForeignKey("Service.id"), nullable=False)
    consultationType: Mapped[str] = mapped_column(String, nullable=False)
    localDate: Mapped[str] = mapped_column(String, nullable=False)
    localTime: Mapped[str] = mapped_column(String, nullable=False)
    startsAt: Mapped[datetime] = mapped_column(DateTime(), nullable=False)
    endsAt: Mapped[datetime] = mapped_column(DateTime(), nullable=False)
    timezone: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[AppointmentStatus] = mapped_column(AppointmentStatusEnum, nullable=False, default=AppointmentStatus.PENDING)
    paymentStatus: Mapped[PaymentStatus] = mapped_column(PaymentStatusEnum, nullable=False, default=PaymentStatus.NOT_REQUIRED)
    concern: Mapped[str | None] = mapped_column(String, nullable=True)
    notes: Mapped[str | None] = mapped_column(String, nullable=True)
    meetingUrl: Mapped[str | None] = mapped_column(String, nullable=True)
    createdAt: Mapped[datetime] = mapped_column(DateTime(), server_default=func.now())
    updatedAt: Mapped[datetime] = mapped_column(DateTime(), default=func.now(), onupdate=func.now())

    doctor: Mapped["User"] = relationship(foreign_keys=[doctorId])
    patient: Mapped["User"] = relationship(foreign_keys=[patientId])
    service: Mapped["Service"] = relationship()
    statusHistory: Mapped[list["AppointmentStatusHistory"]] = relationship(back_populates="appointment")
    payment: Mapped["Payment | None"] = relationship(back_populates="appointment", uselist=False)


class AppointmentStatusHistory(Base):
    __tablename__ = "AppointmentStatusHistory"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    appointmentId: Mapped[str] = mapped_column(String, ForeignKey("Appointment.id", ondelete="CASCADE"), nullable=False)
    fromStatus: Mapped[AppointmentStatus | None] = mapped_column(AppointmentStatusEnum, nullable=True)
    toStatus: Mapped[AppointmentStatus] = mapped_column(AppointmentStatusEnum, nullable=False)
    reason: Mapped[str | None] = mapped_column(String, nullable=True)
    changedById: Mapped[str | None] = mapped_column(String, nullable=True)
    createdAt: Mapped[datetime] = mapped_column(DateTime(), server_default=func.now())

    appointment: Mapped["Appointment"] = relationship(back_populates="statusHistory")
