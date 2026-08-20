from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.dependencies import require_role
from app.db.session import get_db
from app.models.notification import Notification
from app.schemas.auth import SessionUser
from app.schemas.notification import NotificationOut

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("", response_model=dict)
def list_notifications(
    session: SessionUser = Depends(require_role("ADMIN", "DOCTOR")),
    db: Session = Depends(get_db),
) -> dict:
    query = select(Notification).options(joinedload(Notification.logs)).order_by(Notification.createdAt.desc()).limit(100)
    if session.role == "DOCTOR":
        query = query.where(Notification.userId == session.userId)
    notifications = db.execute(query).unique().scalars().all()
    return {"notifications": [NotificationOut.model_validate(item).model_dump(mode="json") for item in notifications]}
