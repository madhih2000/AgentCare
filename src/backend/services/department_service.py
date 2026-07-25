from sqlalchemy.orm import Session

from backend.models.clinical import Department, Doctor
from backend.services import audit_service
from backend.services.exceptions import NotFoundError
from backend.utils.ids import new_id

DEPARTMENT_KEYWORDS: dict[str, list[str]] = {
    # "cardio" is the common root — it's a substring of "cardiology",
    # "cardiologist", and "cardiovascular" too, so listing it instead of the
    # longer "cardiology" form covers all of them (matching the pattern
    # already used for e.g. "neuro"/"derma" below).
    "Cardiology": ["heart", "cardiac", "cardio", "ecg", "chest"],
    "Orthopedics": ["bone", "joint", "fracture", "orthopedic", "knee", "back pain"],
    "General Medicine": ["fever", "cold", "flu", "general", "checkup", "cough"],
    "Neurology": ["headache", "migraine", "neuro", "seizure", "nerve"],
    "Dermatology": ["skin", "rash", "acne", "derma"],
    "Pediatrics": ["child", "infant", "pediatric", "baby"],
}


def list_active_departments(db: Session) -> list[Department]:
    return db.query(Department).filter(Department.active.is_(True)).all()


def get_department_by_name(db: Session, name: str) -> Department | None:
    return db.query(Department).filter(Department.name == name).first()


def get_active_department(db: Session, department_id: str) -> Department | None:
    """Non-raising lookup used to validate an LLM-picked department id — the
    Routing Agent calls this (via select_department) to confirm its choice
    is a real, active row rather than trusting its own text output."""
    return (
        db.query(Department)
        .filter(Department.id == department_id, Department.active.is_(True))
        .first()
    )


def get_department(db: Session, department_id: str) -> Department:
    dept = db.query(Department).filter(Department.id == department_id).first()
    if not dept:
        raise NotFoundError(f"Department {department_id} not found")
    return dept


def list_doctors(db: Session, department_id: str) -> list[Doctor]:
    return (
        db.query(Doctor)
        .filter(Doctor.department_id == department_id, Doctor.active.is_(True))
        .all()
    )


def create_doctor(db: Session, *, department_id: str, name: str, actor_id: str) -> Doctor:
    get_department(db, department_id)  # raises NotFoundError if invalid
    doctor = Doctor(id=new_id(), department_id=department_id, name=name, active=True)
    db.add(doctor)
    db.commit()
    db.refresh(doctor)
    audit_service.record(
        db, actor_id=actor_id, action="doctor.create", entity_type="Doctor", entity_id=doctor.id,
        metadata={"department_id": department_id, "name": name},
    )
    return doctor


def classify_department(db: Session, request_text: str) -> Department | None:
    """Deterministic keyword-based classifier. The Routing Agent's primary
    path is now select_department (the LLM picks from list_departments'
    real results, semantically) — this is a fallback for when the LLM
    doesn't make a clear pick, and a narrower net than the LLM's own
    judgment: it will miss synonyms/phrasing the LLM would understand fine.
    """
    lowered = request_text.lower()
    for dept_name, keywords in DEPARTMENT_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            return get_department_by_name(db, dept_name)
    return None
