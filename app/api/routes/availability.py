from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_db
from app.schemas.appointment import AvailabilityResponse
from app.services.availability_service import get_available_slots

router = APIRouter(prefix="/api/availability", tags=["availability"])


@router.get("", response_model=AvailabilityResponse)
async def read_availability(
    date: str = Query(...),
    serviceId: str = Query(...),
    doctorId: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> AvailabilityResponse:
    settings = get_settings()
    slots = await get_available_slots(db, date, serviceId, doctorId)
    return AvailabilityResponse(slots=slots, timezone=settings.CLINIC_TIMEZONE)
