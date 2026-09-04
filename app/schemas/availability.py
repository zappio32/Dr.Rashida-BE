from datetime import date as date_cls

from pydantic import BaseModel, Field, model_validator


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

    @model_validator(mode="after")
    def validate_schedule(self) -> "AvailabilityRuleUpsertRequest":
        def to_minutes(value: str) -> int:
            hours, minutes = (int(part) for part in value.split(":"))
            if hours > 23 or minutes > 59:
                raise ValueError("Time must be a valid 24-hour clock value.")
            return hours * 60 + minutes

        start = to_minutes(self.startTime)
        end = to_minutes(self.endTime)
        if start >= end:
            raise ValueError("Start time must be before end time.")
        if (self.breakStart is None) != (self.breakEnd is None):
            raise ValueError("Break start and break end must be provided together.")
        if self.breakStart is not None and self.breakEnd is not None:
            break_start = to_minutes(self.breakStart)
            break_end = to_minutes(self.breakEnd)
            if break_start < start or break_end > end or break_start >= break_end:
                raise ValueError("Break must be within working hours and start before it ends.")
        return self


class HolidayOut(BaseModel):
    id: str
    doctorId: str
    date: date_cls
    label: str | None = None

    model_config = {"from_attributes": True}


class HolidayCreateRequest(BaseModel):
    date: date_cls
    label: str | None = Field(default=None, max_length=200)


class BlockedSlotOut(BaseModel):
    id: str
    doctorId: str
    date: date_cls
    time: str

    model_config = {"from_attributes": True}


class BlockedSlotCreateRequest(BaseModel):
    date: date_cls
    time: str = Field(pattern=r"^\d{2}:\d{2}$")

