from datetime import datetime

from pydantic import BaseModel


class NotificationLogOut(BaseModel):
    id: str
    status: str
    providerRef: str | None = None
    error: str | None = None
    createdAt: datetime

    model_config = {"from_attributes": True}


class NotificationOut(BaseModel):
    id: str
    userId: str
    appointmentId: str | None = None
    channel: str
    status: str
    subject: str
    body: str
    attempts: int
    lastError: str | None = None
    createdAt: datetime
    logs: list[NotificationLogOut] = []

    model_config = {"from_attributes": True}
