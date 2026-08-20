from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base
from app.models.enums import Role
from app.utils.ids import new_id

RoleEnum = Enum(Role, name="Role", create_type=False, values_callable=lambda e: [m.value for m in e])


class User(Base):
    __tablename__ = "User"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    passwordHash: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[Role] = mapped_column(RoleEnum, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    phone: Mapped[str | None] = mapped_column(String, nullable=True)
    isActive: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    forcePasswordChange: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    createdAt: Mapped[datetime] = mapped_column(DateTime(), server_default=func.now())
    updatedAt: Mapped[datetime] = mapped_column(DateTime(), default=func.now(), onupdate=func.now())

    patientProfile: Mapped["PatientProfile | None"] = relationship(back_populates="user", uselist=False)
    doctorProfile: Mapped["DoctorProfile | None"] = relationship(back_populates="user", uselist=False)


class PatientProfile(Base):
    __tablename__ = "PatientProfile"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    userId: Mapped[str] = mapped_column(String, ForeignKey("User.id", ondelete="CASCADE"), unique=True, nullable=False)
    dateOfBirth: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    age: Mapped[int | None] = mapped_column(nullable=True)
    gender: Mapped[str | None] = mapped_column(String, nullable=True)
    city: Mapped[str | None] = mapped_column(String, nullable=True)
    consentAt: Mapped[datetime | None] = mapped_column(DateTime(), nullable=True)

    user: Mapped["User"] = relationship(back_populates="patientProfile")


class DoctorProfile(Base):
    __tablename__ = "DoctorProfile"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    userId: Mapped[str] = mapped_column(String, ForeignKey("User.id", ondelete="CASCADE"), unique=True, nullable=False)
    displayName: Mapped[str] = mapped_column(String, nullable=False)
    qualification: Mapped[str | None] = mapped_column(String, nullable=True)
    specialization: Mapped[str | None] = mapped_column(String, nullable=True)
    experience: Mapped[str | None] = mapped_column(String, nullable=True)
    bio: Mapped[str | None] = mapped_column(String, nullable=True)
    languages: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    clinicAddress: Mapped[str | None] = mapped_column(String, nullable=True)
    timezone: Mapped[str] = mapped_column(String, nullable=False, default="Asia/Kolkata")
    onlineFee: Mapped[int] = mapped_column(nullable=False, default=0)
    clinicFee: Mapped[int] = mapped_column(nullable=False, default=0)
    durationMinutes: Mapped[int] = mapped_column(nullable=False, default=30)
    updatedAt: Mapped[datetime] = mapped_column(DateTime(), default=func.now(), onupdate=func.now())

    user: Mapped["User"] = relationship(back_populates="doctorProfile")
    availabilityRules: Mapped[list["AvailabilityRule"]] = relationship(back_populates="doctor")
    holidays: Mapped[list["Holiday"]] = relationship(back_populates="doctor")
    blockedSlots: Mapped[list["BlockedSlot"]] = relationship(back_populates="doctor")
