from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.dependencies import require_role
from app.db.session import get_db
from app.models.notification import Notification
from app.schemas.auth import SessionUser
from app.schemas.notification import NotificationOut

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("", response_model=dict)
async def list_notifications(
    session: SessionUser = Depends(require_role("ADMIN", "DOCTOR")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    query = select(Notification).options(joinedload(Notification.logs)).order_by(Notification.createdAt.desc()).limit(100)
    if session.role == "DOCTOR":
        query = query.where(Notification.userId == session.userId)
    result = await db.execute(query)
    notifications = result.unique().scalars().all()
    return {"notifications": [NotificationOut.model_validate(item).model_dump(mode="json") for item in notifications]}
