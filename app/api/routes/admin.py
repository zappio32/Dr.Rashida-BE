from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.dependencies import require_role
from app.db.session import get_db
from app.models.appointment import Appointment
from app.models.enums import Role
from app.models.misc import AuditLog
from app.models.notification import Notification
from app.models.service import Service
from app.models.user import User
from app.schemas.appointment import AppointmentOut, ServiceCreateRequest, ServiceOut
from app.schemas.auth import SessionUser
from app.utils.ids import new_id

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/dashboard-summary", response_model=dict)
def read_dashboard_summary(
    session: SessionUser = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
) -> dict:
    patients_count = db.execute(select(func.count()).select_from(User).where(User.role == Role.PATIENT)).scalar_one()
    services_count = db.execute(select(func.count()).select_from(Service).where(Service.active.is_(True))).scalar_one()
    notifications_count = db.execute(select(func.count()).select_from(Notification)).scalar_one()
    return {"patientsCount": patients_count, "servicesCount": services_count, "notificationsCount": notifications_count}


@router.get("/appointments", response_model=dict)
def list_all_appointments(
    session: SessionUser = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
) -> dict:
    query = (
        select(Appointment)
        .options(joinedload(Appointment.patient), joinedload(Appointment.service), joinedload(Appointment.payment))
        .order_by(Appointment.startsAt.desc())
    )
    appointments = db.execute(query).unique().scalars().all()
    return {"appointments": [AppointmentOut.model_validate(item).model_dump(mode="json") for item in appointments]}


@router.get("/services", response_model=dict)
def list_services(
    session: SessionUser = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
) -> dict:
    services = db.execute(select(Service).order_by(Service.createdAt.asc())).scalars().all()
    return {"services": [ServiceOut.model_validate(item).model_dump(mode="json") for item in services]}


@router.post("/services", response_model=dict, status_code=201)
def create_service(
    payload: ServiceCreateRequest,
    session: SessionUser = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
) -> dict:
    service = Service(id=new_id(), **payload.model_dump())
    db.add(service)
    db.flush()
    db.add(AuditLog(id=new_id(), userId=session.userId, action="SERVICE_CREATED", entity="Service", entityId=service.id))
    db.commit()
    db.refresh(service)
    return {"service": ServiceOut.model_validate(service).model_dump(mode="json")}
