from datetime import datetime

from pydantic import BaseModel


class PaymentOut(BaseModel):
    id: str
    appointmentId: str
    amount: int
    status: str
    provider: str | None = None
    providerRef: str | None = None
    createdAt: datetime
    updatedAt: datetime

    model_config = {"from_attributes": True}
