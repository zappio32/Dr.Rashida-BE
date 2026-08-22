from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.payment_out import PaymentOut


class ServiceOut(BaseModel):
    id: str
    name: str
    description: str
    durationMin: int
    fee: int
    active: bool

    model_config = {"from_attributes": True}


class ServiceCreateRequest(BaseModel):
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    durationMin: int = Field(gt=0)
    fee: int = Field(ge=0)
    active: bool = True


class ServiceUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    description: str | None = Field(default=None, min_length=1)
    durationMin: int | None = Field(default=None, gt=0)
    fee: int | None = Field(default=None, ge=0)
    active: bool | None = None


class PatientSummary(BaseModel):
    name: str
    email: str
    phone: str | None = None

    model_config = {"from_attributes": True}


class AppointmentCreateRequest(BaseModel):
    serviceId: str = Field(min_length=1)
    consultationType: Literal["ONLINE", "CLINIC"]
    localDate: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    localTime: str = Field(pattern=r"^\d{2}:\d{2}$")
    concern: str | None = Field(default=None, max_length=3000)
    notes: str | None = Field(default=None, max_length=3000)


class AppointmentUpdateRequest(BaseModel):
    action: Literal["CANCEL", "RESCHEDULE"]
    localDate: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    localTime: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    reason: str | None = Field(default=None, max_length=500)


class DoctorStatusUpdateRequest(BaseModel):
    appointmentId: str
    status: Literal["CONFIRMED", "CHECKED_IN", "IN_CONSULTATION", "COMPLETED", "CANCELLED", "NO_SHOW"]
    reason: str | None = Field(default=None, max_length=500)


class AppointmentOut(BaseModel):
    id: str
    bookingId: str
    doctorId: str
    patientId: str
    serviceId: str
    consultationType: str
    localDate: str
    localTime: str
    startsAt: datetime
    endsAt: datetime
    timezone: str
    status: str
    paymentStatus: str
    concern: str | None = None
    notes: str | None = None
    meetingUrl: str | None = None
    createdAt: datetime
    updatedAt: datetime
    service: ServiceOut | None = None
    patient: PatientSummary | None = None
    payment: PaymentOut | None = None

    model_config = {"from_attributes": True}


class AppointmentCreateResponse(BaseModel):
    bookingId: str


class AvailabilityResponse(BaseModel):
    slots: list[str]
    timezone: str
