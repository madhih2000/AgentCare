from datetime import date
from pathlib import Path

from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.models.documents import PatientDocument
from backend.services import audit_service
from backend.services.exceptions import NotFoundError
from backend.utils.checksums import checksum_bytes
from backend.utils.ids import new_id
from backend.utils.validators import REQUIRED_DOCUMENTS_BY_DEPARTMENT, infer_document_type

settings = get_settings()


def save_document(
    db: Session,
    *,
    patient_id: str,
    filename: str,
    content: bytes,
    document_date: date | None,
    actor_id: str,
) -> PatientDocument:
    checksum = checksum_bytes(content)
    document_type = infer_document_type(filename)

    duplicate = (
        db.query(PatientDocument)
        .filter(PatientDocument.patient_id == patient_id, PatientDocument.checksum == checksum)
        .first()
    )

    upload_dir = Path(settings.upload_dir) / patient_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    doc_id = new_id()
    file_path = upload_dir / f"{doc_id}_{filename}"
    file_path.write_bytes(content)

    document = PatientDocument(
        id=doc_id,
        patient_id=patient_id,
        document_type=document_type,
        file_path=str(file_path),
        document_date=document_date,
        checksum=checksum,
        is_duplicate_of=duplicate.id if duplicate else None,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    audit_service.record(
        db, actor_id=actor_id, action="document.upload", entity_type="PatientDocument",
        entity_id=document.id,
        metadata={"document_type": document_type, "duplicate": bool(duplicate)},
    )
    return document


def list_patient_documents(db: Session, patient_id: str) -> list[PatientDocument]:
    return (
        db.query(PatientDocument)
        .filter(PatientDocument.patient_id == patient_id)
        .order_by(PatientDocument.created_at.desc())
        .all()
    )


def missing_documents_for_department(
    db: Session, *, patient_id: str, department_name: str
) -> list[str]:
    required = REQUIRED_DOCUMENTS_BY_DEPARTMENT.get(department_name, [])
    if not required:
        return []
    existing_types = {
        doc.document_type
        for doc in list_patient_documents(db, patient_id)
        if doc.is_duplicate_of is None
    }
    return [doc_type for doc_type in required if doc_type not in existing_types]


def get_document(db: Session, document_id: str) -> PatientDocument:
    document = db.query(PatientDocument).filter(PatientDocument.id == document_id).first()
    if not document:
        raise NotFoundError(f"Document {document_id} not found")
    return document
