from sqlalchemy.orm import Session

from backend.models.clinical import Department, Doctor
from backend.services import audit_service
from backend.services.exceptions import NotFoundError
from backend.utils.ids import new_id

DEPARTMENT_KEYWORDS: dict[str, list[str]] = {
    "Cardiology": ["heart", "cardiac", "cardiology", "ecg", "chest"],
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
    """Deterministic keyword-based fallback classifier used by the routing tool.

    The LLM makes the primary routing decision; this gives the agent a
    grounded lookup so it maps free text to a *real* Department row rather
    than hallucinating a department name.
    """
    lowered = request_text.lower()
    for dept_name, keywords in DEPARTMENT_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            return get_department_by_name(db, dept_name)
    return None
