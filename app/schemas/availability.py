from pydantic import BaseModel, Field


class AvailabilityRuleOut(BaseModel):
    id: str
    doctorId: str
    weekday: int
    startTime: str
    endTime: str
    breakStart: str | None = None
    breakEnd: str | None = None
    slotMinutes: int
    active: bool

    model_config = {"from_attributes": True}


class AvailabilityRuleUpsertRequest(BaseModel):
    weekday: int = Field(ge=0, le=6)
    startTime: str = Field(pattern=r"^\d{2}:\d{2}$")
    endTime: str = Field(pattern=r"^\d{2}:\d{2}$")
    breakStart: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    breakEnd: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    slotMinutes: int = Field(gt=0, le=240)
    active: bool = True
