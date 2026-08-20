from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_session
from app.db.session import get_db
from app.models.appointment import Appointment
from app.models.document import MedicalDocument
from app.schemas.auth import SessionUser
from app.schemas.document import DocumentCreateRequest, DocumentOut
from app.utils.ids import new_id

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
def upload_document(
    payload: DocumentCreateRequest,
    session: SessionUser = Depends(get_current_session),
    db: Session = Depends(get_db),
) -> dict:
    appointment = db.get(Appointment, payload.appointmentId)
    if not appointment or appointment.patientId != session.userId:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to access this information.")
    try:
        document = MedicalDocument(id=new_id(), patientId=session.userId, **payload.model_dump())
        db.add(document)
        db.commit()
        db.refresh(document)
        return {"document": DocumentOut.model_validate(document).model_dump(mode="json")}
    except Exception as error:  # noqa: BLE001
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid document metadata.") from error
