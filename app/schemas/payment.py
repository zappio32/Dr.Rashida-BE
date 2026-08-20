from typing import Any, Literal

from pydantic import BaseModel


class PaymentWebhookPayload(BaseModel):
    bookingId: str
    status: Literal["PAID", "FAILED"]
    providerRef: str | None = None


class WebhookAck(BaseModel):
    ok: bool = True
