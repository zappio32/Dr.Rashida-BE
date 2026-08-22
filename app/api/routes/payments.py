from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.config import get_settings
from app.db.session import get_db
from app.models.appointment import Appointment
from app.models.enums import PaymentStatus
from app.models.payment import PaymentTransaction
from app.schemas.payment import PaymentWebhookPayload, WebhookAck

router = APIRouter(prefix="/api/payments", tags=["payments"])


@router.post("/webhook", response_model=WebhookAck)
async def payment_webhook(
    payload: PaymentWebhookPayload,
    x_payment_signature: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> WebhookAck:
    settings = get_settings()
    if not settings.PAYMENT_WEBHOOK_SECRET or not x_payment_signature or x_payment_signature != settings.PAYMENT_WEBHOOK_SECRET:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook signature.")

    try:
        result = await db.execute(
            select(Appointment)
            .where(Appointment.bookingId == payload.bookingId)
            .options(joinedload(Appointment.payment))
        )
        appointment = result.scalar_one_or_none()
        if not appointment or not appointment.payment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found.")

        payment = appointment.payment
        payment.status = PaymentStatus(payload.status)
        db.add(
            PaymentTransaction(
                paymentId=payment.id,
                event="WEBHOOK",
                providerRef=payload.providerRef,
                payload=payload.model_dump(),
            )
        )
        appointment.paymentStatus = PaymentStatus(payload.status)
        await db.commit()
        return WebhookAck(ok=True)
    except HTTPException:
        await db.rollback()
        raise
    except Exception as error:  # noqa: BLE001
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payment webhook could not be processed.") from error
