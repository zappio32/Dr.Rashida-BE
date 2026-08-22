from pydantic import AliasChoices, BaseModel, EmailStr, Field, field_validator


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


def _coerce_active_status(value: object) -> object:
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in ("active", "true", "yes", "1"):
            return True
        if normalized in ("inactive", "false", "no", "0"):
            return False
    return value


class DoctorCreateRequest(BaseModel):
    model_config = {"populate_by_name": True}

    name: str = Field(min_length=2, max_length=120)
    # Admin "Add Doctor" form does not collect login credentials — account is
    # auto-provisioned server-side when these are omitted (see create_doctor).
    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=10)
    departmentId: str | None = Field(default=None, validation_alias=AliasChoices("departmentId", "department"))
    qualification: str | None = None
    specialization: str | None = None
    experience: str | None = None
    bio: str | None = None
    languages: list[str] = []
    clinicAddress: str | None = None
    timezone: str = "Asia/Kolkata"
    onlineFee: int = Field(default=0, ge=0)
    clinicFee: int = Field(default=0, ge=0)
    durationMinutes: int = Field(
        default=30, gt=0, validation_alias=AliasChoices("durationMinutes", "duration", "appointmentDuration")
    )
    isActive: bool = Field(default=True, validation_alias=AliasChoices("isActive", "active", "status"))

    @field_validator("isActive", mode="before")
    @classmethod
    def _validate_is_active(cls, value: object) -> object:
        return _coerce_active_status(value)


class DoctorUpdateRequest(BaseModel):
    model_config = {"populate_by_name": True}

    name: str | None = Field(default=None, min_length=2, max_length=120)
    departmentId: str | None = Field(default=None, validation_alias=AliasChoices("departmentId", "department"))
    qualification: str | None = None
    specialization: str | None = None
    experience: str | None = None
    bio: str | None = None
    languages: list[str] | None = None
    clinicAddress: str | None = None
    timezone: str | None = None
    onlineFee: int | None = Field(default=None, ge=0)
    clinicFee: int | None = Field(default=None, ge=0)
    durationMinutes: int | None = Field(
        default=None, gt=0, validation_alias=AliasChoices("durationMinutes", "duration", "appointmentDuration")
    )
    isActive: bool | None = Field(default=None, validation_alias=AliasChoices("isActive", "active", "status"))

    @field_validator("isActive", mode="before")
    @classmethod
    def _validate_is_active(cls, value: object) -> object:
        return _coerce_active_status(value)
