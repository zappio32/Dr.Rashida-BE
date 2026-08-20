from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base
from app.utils.ids import new_id


class MedicalDocument(Base):
    __tablename__ = "MedicalDocument"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    appointmentId: Mapped[str] = mapped_column(String, ForeignKey("Appointment.id", ondelete="CASCADE"), nullable=False)
    patientId: Mapped[str] = mapped_column(String, nullable=False)
    storageKey: Mapped[str] = mapped_column(String, nullable=False)
    originalName: Mapped[str] = mapped_column(String, nullable=False)
    mimeType: Mapped[str] = mapped_column(String, nullable=False)
    sizeBytes: Mapped[int] = mapped_column(Integer, nullable=False)
    createdAt: Mapped[datetime] = mapped_column(DateTime(), server_default=func.now())

    appointment: Mapped["Appointment"] = relationship()


class ConsultationNote(Base):
    __tablename__ = "ConsultationNote"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    appointmentId: Mapped[str] = mapped_column(String, ForeignKey("Appointment.id", ondelete="CASCADE"), unique=True, nullable=False)
    content: Mapped[str] = mapped_column(String, nullable=False)
    followUp: Mapped[str | None] = mapped_column(String, nullable=True)
    createdAt: Mapped[datetime] = mapped_column(DateTime(), server_default=func.now())
    updatedAt: Mapped[datetime] = mapped_column(DateTime(), default=func.now(), onupdate=func.now())

    appointment: Mapped["Appointment"] = relationship()


class Prescription(Base):
    __tablename__ = "Prescription"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    appointmentId: Mapped[str] = mapped_column(String, ForeignKey("Appointment.id", ondelete="CASCADE"), unique=True, nullable=False)
    storageKey: Mapped[str] = mapped_column(String, nullable=False)
    originalName: Mapped[str] = mapped_column(String, nullable=False)
    createdAt: Mapped[datetime] = mapped_column(DateTime(), server_default=func.now())

    appointment: Mapped["Appointment"] = relationship()
