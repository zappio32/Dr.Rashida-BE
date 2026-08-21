from pydantic import BaseModel

from app.schemas.appointment import ServiceOut


class DoctorPublicOut(BaseModel):
    displayName: str
    specialization: str | None = None
    bio: str | None = None
    qualification: str | None = None
    experience: str | None = None

    model_config = {"from_attributes": True}


class HomeResponse(BaseModel):
    doctor: DoctorPublicOut | None
    services: list[ServiceOut]
    demoMode: bool
