from pydantic import BaseModel, Field


class DepartmentOut(BaseModel):
    id: str
    name: str
    description: str | None = None
    active: bool

    model_config = {"from_attributes": True}


class DepartmentCreateRequest(BaseModel):
    name: str = Field(min_length=1)
    description: str | None = None
    active: bool = True


class DepartmentUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    description: str | None = None
    active: bool | None = None
