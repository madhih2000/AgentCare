from sqlalchemy.orm import Session

from backend.models.user import PatientProfile
from backend.services import audit_service
from backend.services.exceptions import NotFoundError


def get_profile_by_user_id(db: Session, user_id: str) -> PatientProfile:
    profile = db.query(PatientProfile).filter(PatientProfile.user_id == user_id).first()
    if not profile:
        raise NotFoundError(f"No patient profile for user {user_id}")
    return profile


def get_profile_by_id(db: Session, patient_id: str) -> PatientProfile:
    profile = db.query(PatientProfile).filter(PatientProfile.id == patient_id).first()
    if not profile:
        raise NotFoundError(f"No patient profile {patient_id}")
    return profile


def update_profile(
    db: Session, *, user_id: str, actor_id: str, updates: dict
) -> PatientProfile:
    profile = get_profile_by_user_id(db, user_id)
    for field, value in updates.items():
        if value is not None:
            setattr(profile, field, value)
    db.commit()
    db.refresh(profile)
    audit_service.record(
        db, actor_id=actor_id, action="patient.update_profile",
        entity_type="PatientProfile", entity_id=profile.id, metadata=updates,
    )
    return profile
