from fastapi import APIRouter, Query
from sqlalchemy.orm import Session
from fastapi import Depends

from app.core.config import get_settings
from app.db.session import get_db
from app.schemas.appointment import AvailabilityResponse
from app.services.availability_service import get_available_slots

router = APIRouter(prefix="/api/availability", tags=["availability"])


@router.get("", response_model=AvailabilityResponse)
def read_availability(
    date: str = Query(...),
    serviceId: str = Query(...),
    db: Session = Depends(get_db),
) -> AvailabilityResponse:
    settings = get_settings()
    slots = get_available_slots(db, date, serviceId)
    return AvailabilityResponse(slots=slots, timezone=settings.CLINIC_TIMEZONE)
