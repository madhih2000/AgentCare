from datetime import date

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.models.user import User
from backend.routes.deps import require_patient
from backend.schemas.document import DocumentOut
from backend.services import document_service, patient_service

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("", response_model=list[DocumentOut])
def list_my_documents(user: User = Depends(require_patient), db: Session = Depends(get_db)):
    profile = patient_service.get_profile_by_user_id(db, user.id)
    return document_service.list_patient_documents(db, profile.id)


@router.post("/upload", response_model=DocumentOut)
async def upload_document(
    file: UploadFile = File(...),
    document_date: date | None = Form(default=None),
    user: User = Depends(require_patient),
    db: Session = Depends(get_db),
):
    profile = patient_service.get_profile_by_user_id(db, user.id)
    content = await file.read()
    return document_service.save_document(
        db,
        patient_id=profile.id,
        filename=file.filename,
        content=content,
        document_date=document_date,
        actor_id=user.id,
    )
