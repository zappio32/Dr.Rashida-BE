from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base
from app.models.enums import PaymentStatus
from app.utils.ids import new_id

PaymentStatusEnum = Enum(
    PaymentStatus, name="PaymentStatus", create_type=False, values_callable=lambda e: [m.value for m in e]
)


class Payment(Base):
    __tablename__ = "Payment"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    appointmentId: Mapped[str] = mapped_column(String, ForeignKey("Appointment.id", ondelete="CASCADE"), unique=True, nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(PaymentStatusEnum, nullable=False, default=PaymentStatus.PENDING)
    provider: Mapped[str | None] = mapped_column(String, nullable=True)
    providerRef: Mapped[str | None] = mapped_column(String, nullable=True)
    createdAt: Mapped[datetime] = mapped_column(DateTime(), server_default=func.now())
    updatedAt: Mapped[datetime] = mapped_column(DateTime(), default=func.now(), onupdate=func.now())

    appointment: Mapped["Appointment"] = relationship(back_populates="payment")
    transactions: Mapped[list["PaymentTransaction"]] = relationship(back_populates="payment")


class PaymentTransaction(Base):
    __tablename__ = "PaymentTransaction"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    paymentId: Mapped[str] = mapped_column(String, ForeignKey("Payment.id", ondelete="CASCADE"), nullable=False)
    event: Mapped[str] = mapped_column(String, nullable=False)
    providerRef: Mapped[str | None] = mapped_column(String, nullable=True)
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    createdAt: Mapped[datetime] = mapped_column(DateTime(), server_default=func.now())

    payment: Mapped["Payment"] = relationship(back_populates="transactions")
