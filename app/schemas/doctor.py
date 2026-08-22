from pydantic import BaseModel, EmailStr, Field


class DoctorOut(BaseModel):
    """Public-facing doctor info used for patient booking (no email/credentials)."""

    id: str  # User.id — used as doctorId across appointment/availability APIs
    displayName: str
    qualification: str | None = None
    specialization: str | None = None
    experience: str | None = None
    bio: str | None = None
    languages: list[str] = []
    clinicAddress: str | None = None
    timezone: str
    departmentId: str | None = None
    departmentName: str | None = None


class DoctorAdminOut(DoctorOut):
    email: str
    phone: str | None = None
    isActive: bool
    onlineFee: int
    clinicFee: int
    durationMinutes: int


class DoctorCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=10)
    departmentId: str | None = None
    qualification: str | None = None
    specialization: str | None = None
    experience: str | None = None
    bio: str | None = None
    languages: list[str] = []
    clinicAddress: str | None = None
    timezone: str = "Asia/Kolkata"
    onlineFee: int = Field(default=0, ge=0)
    clinicFee: int = Field(default=0, ge=0)
    durationMinutes: int = Field(default=30, gt=0)


class DoctorUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    departmentId: str | None = None
    qualification: str | None = None
    specialization: str | None = None
    experience: str | None = None
    bio: str | None = None
    languages: list[str] | None = None
    clinicAddress: str | None = None
    timezone: str | None = None
    onlineFee: int | None = Field(default=None, ge=0)
    clinicFee: int | None = Field(default=None, ge=0)
    durationMinutes: int | None = Field(default=None, gt=0)
    isActive: bool | None = None
