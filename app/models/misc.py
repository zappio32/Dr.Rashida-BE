from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base
from app.utils.ids import new_id


class ContactEnquiry(Base):
    __tablename__ = "ContactEnquiry"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False)
    phone: Mapped[str | None] = mapped_column(String, nullable=True)
    subject: Mapped[str] = mapped_column(String, nullable=False)
    message: Mapped[str] = mapped_column(String, nullable=False)
    createdAt: Mapped[datetime] = mapped_column(DateTime(), server_default=func.now())


class AuditLog(Base):
    __tablename__ = "AuditLog"
    __table_args__ = (Index("AuditLog_entity_entityId_idx", "entity", "entityId"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    userId: Mapped[str | None] = mapped_column(String, ForeignKey("User.id", ondelete="SET NULL"), nullable=True)
    action: Mapped[str] = mapped_column(String, nullable=False)
    entity: Mapped[str] = mapped_column(String, nullable=False)
    entityId: Mapped[str | None] = mapped_column(String, nullable=True)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB, nullable=True)
    createdAt: Mapped[datetime] = mapped_column(DateTime(), server_default=func.now())

    user: Mapped["User | None"] = relationship()


class SystemSetting(Base):
    __tablename__ = "SystemSetting"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    key: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    value: Mapped[Any] = mapped_column(JSONB, nullable=False)
    updatedAt: Mapped[datetime] = mapped_column(DateTime(), default=func.now(), onupdate=func.now())
