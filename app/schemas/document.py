from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class DocumentCreateRequest(BaseModel):
    appointmentId: str
    storageKey: str = Field(min_length=1)
    originalName: str = Field(min_length=1, max_length=255)
    mimeType: Literal["application/pdf", "image/jpeg", "image/png"]
    sizeBytes: int = Field(gt=0, le=10_000_000)


class DocumentOut(BaseModel):
    id: str
    appointmentId: str
    patientId: str
    storageKey: str
    originalName: str
    mimeType: str
    sizeBytes: int
    createdAt: datetime

    model_config = {"from_attributes": True}
