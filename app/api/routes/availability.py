from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_db
from app.models.availability import AvailabilityRule
from app.models.user import DoctorProfile, User
from app.schemas.appointment import AvailabilityResponse
from app.schemas.availability import AvailabilityRuleOut
from app.services.availability_service import get_available_slots

router = APIRouter(prefix="/api/availability", tags=["availability"])


@router.get("", response_model=AvailabilityResponse)
async def read_availability(
    date: str = Query(...),
    serviceId: str | None = Query(default=None),
    doctorId: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> AvailabilityResponse:
    settings = get_settings()
    slots = await get_available_slots(db, date, serviceId, doctorId)
    schedule = None
    try:
        parsed_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        parsed_date = None
    if parsed_date is not None and doctorId:
        result = await db.execute(
            select(AvailabilityRule)
            .join(DoctorProfile, DoctorProfile.id == AvailabilityRule.doctorId)
            .join(User, User.id == DoctorProfile.userId)
            .where(
                DoctorProfile.userId == doctorId,
                User.isActive.is_(True),
                AvailabilityRule.weekday == (parsed_date.weekday() + 1) % 7,
            )
        )
        rule = result.scalar_one_or_none()
        if rule:
            schedule = AvailabilityRuleOut.model_validate(rule)
    return AvailabilityResponse(slots=slots, timezone=settings.CLINIC_TIMEZONE, schedule=schedule)
