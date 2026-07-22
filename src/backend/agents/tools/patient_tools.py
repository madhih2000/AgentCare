from langchain_core.tools import tool

from backend.db.session import SessionLocal
from backend.services import patient_service
from backend.services.exceptions import NotFoundError


@tool
def get_patient_profile(patient_id: str) -> dict:
    """Look up a patient's profile by patient_id to confirm the record exists
    before doing any administrative work for them. Returns profile fields or
    an error if no such patient exists."""
    db = SessionLocal()
    try:
        profile = patient_service.get_profile_by_id(db, patient_id)
        return {
            "id": profile.id,
            "user_id": profile.user_id,
            "phone": profile.phone,
            "preferred_language": profile.preferred_language,
            "emergency_contact": profile.emergency_contact,
        }
    except NotFoundError as exc:
        return {"error": str(exc)}
    finally:
        db.close()
