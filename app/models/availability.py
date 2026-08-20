from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base
from app.utils.ids import new_id


class AvailabilityRule(Base):
    __tablename__ = "AvailabilityRule"
    __table_args__ = (UniqueConstraint("doctorId", "weekday", name="AvailabilityRule_doctorId_weekday_key"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    doctorId: Mapped[str] = mapped_column(String, ForeignKey("DoctorProfile.id", ondelete="CASCADE"), nullable=False)
    weekday: Mapped[int] = mapped_column(Integer, nullable=False)
    startTime: Mapped[str] = mapped_column(String, nullable=False)
    endTime: Mapped[str] = mapped_column(String, nullable=False)
    breakStart: Mapped[str | None] = mapped_column(String, nullable=True)
    breakEnd: Mapped[str | None] = mapped_column(String, nullable=True)
    slotMinutes: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    doctor: Mapped["DoctorProfile"] = relationship(back_populates="availabilityRules")


class Holiday(Base):
    __tablename__ = "Holiday"
    __table_args__ = (UniqueConstraint("doctorId", "date", name="Holiday_doctorId_date_key"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    doctorId: Mapped[str] = mapped_column(String, ForeignKey("DoctorProfile.id", ondelete="CASCADE"), nullable=False)
    date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    label: Mapped[str | None] = mapped_column(String, nullable=True)

    doctor: Mapped["DoctorProfile"] = relationship(back_populates="holidays")


class BlockedSlot(Base):
    __tablename__ = "BlockedSlot"
    __table_args__ = (UniqueConstraint("doctorId", "date", "time", name="BlockedSlot_doctorId_date_time_key"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    doctorId: Mapped[str] = mapped_column(String, ForeignKey("DoctorProfile.id", ondelete="CASCADE"), nullable=False)
    date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    time: Mapped[str] = mapped_column(String, nullable=False)

    doctor: Mapped["DoctorProfile"] = relationship(back_populates="blockedSlots")
