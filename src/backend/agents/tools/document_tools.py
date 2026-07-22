from langchain_core.tools import tool

from backend.db.session import SessionLocal
from backend.services import document_service


@tool
def list_patient_documents(patient_id: str) -> list[dict]:
    """List documents already on file for a patient, including whether each
    one is a duplicate of an earlier upload."""
    db = SessionLocal()
    try:
        return [
            {
                "id": doc.id,
                "document_type": doc.document_type,
                "is_duplicate": doc.is_duplicate_of is not None,
                "created_at": doc.created_at.isoformat(),
            }
            for doc in document_service.list_patient_documents(db, patient_id)
        ]
    finally:
        db.close()


@tool
def missing_documents(patient_id: str, department_name: str) -> list[str]:
    """Return the list of required document types still missing for a patient
    given the routed department name (e.g. 'Cardiology')."""
    db = SessionLocal()
    try:
        return document_service.missing_documents_for_department(
            db, patient_id=patient_id, department_name=department_name
        )
    finally:
        db.close()
