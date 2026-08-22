from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base
from app.utils.ids import new_id


class Department(Base):
    __tablename__ = "Department"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    createdAt: Mapped[datetime] = mapped_column(DateTime(), server_default=func.now())
    updatedAt: Mapped[datetime] = mapped_column(DateTime(), default=func.now(), onupdate=func.now())

    doctors: Mapped[list["DoctorProfile"]] = relationship(back_populates="department")
