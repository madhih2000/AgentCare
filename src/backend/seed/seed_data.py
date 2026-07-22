"""Synthetic demo data — no real patient information. Safe to run repeatedly
(idempotent: skips seeding if departments already exist)."""

import logging
from datetime import timedelta

from backend.db.base import Base
from backend.db.session import SessionLocal, engine
from backend.models.clinical import AppointmentSlot, Department, Doctor, SlotStatus
from backend.models.user import PatientProfile, User, UserRole
from backend.utils.ids import new_id
from backend.utils.security import hash_password
from backend.utils.time import utcnow

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("agentcare.seed")

DEPARTMENTS = [
    ("Cardiology", "Heart and cardiovascular care"),
    ("Orthopedics", "Bones, joints, and musculoskeletal care"),
    ("General Medicine", "General checkups and non-specialist care"),
    ("Neurology", "Brain and nervous system care"),
    ("Dermatology", "Skin conditions"),
    ("Pediatrics", "Care for infants and children"),
]

DOCTORS = {
    "Cardiology": ["Dr. Asha Verma", "Dr. Rohan Mehta"],
    "Orthopedics": ["Dr. Kavita Nair"],
    "General Medicine": ["Dr. Sameer Iyer", "Dr. Priya Das"],
    "Neurology": ["Dr. Arjun Rao"],
    "Dermatology": ["Dr. Neha Kulkarni"],
    "Pediatrics": ["Dr. Meera Joshi"],
}

DEMO_USERS = [
    {
        "name": "Demo Patient",
        "email": "patient@agentcare.demo",
        "password": "Patient123!",
        "role": UserRole.patient,
        "phone": "+91-9000000001",
        "preferred_language": "en",
        "emergency_contact": "+91-9000000099 (spouse)",
    },
    {
        "name": "Demo Staff",
        "email": "staff@agentcare.demo",
        "password": "Staff123!",
        "role": UserRole.staff,
    },
    {
        "name": "Demo Admin",
        "email": "admin@agentcare.demo",
        "password": "Admin123!",
        "role": UserRole.admin,
    },
]


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(Department).first():
            logger.info("Seed data already present, skipping.")
            return

        dept_rows: dict[str, Department] = {}
        for name, description in DEPARTMENTS:
            dept = Department(id=new_id(), name=name, description=description, active=True)
            db.add(dept)
            dept_rows[name] = dept
        db.flush()

        doctor_rows: list[Doctor] = []
        for dept_name, doctor_names in DOCTORS.items():
            for doc_name in doctor_names:
                doctor = Doctor(id=new_id(), department_id=dept_rows[dept_name].id, name=doc_name, active=True)
                db.add(doctor)
                doctor_rows.append(doctor)
        db.flush()

        base = utcnow().replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=1)
        for doctor in doctor_rows:
            for day_offset in range(5):
                for slot_hour in (0, 1, 2):
                    start = base + timedelta(days=day_offset, hours=slot_hour)
                    end = start + timedelta(minutes=30)
                    db.add(
                        AppointmentSlot(
                            id=new_id(), doctor_id=doctor.id, start_time=start, end_time=end,
                            status=SlotStatus.open,
                        )
                    )

        for demo_user in DEMO_USERS:
            user = User(
                id=new_id(),
                name=demo_user["name"],
                email=demo_user["email"],
                password_hash=hash_password(demo_user["password"]),
                role=demo_user["role"],
            )
            db.add(user)
            db.flush()
            if demo_user["role"] == UserRole.patient:
                db.add(
                    PatientProfile(
                        id=new_id(),
                        user_id=user.id,
                        phone=demo_user.get("phone"),
                        preferred_language=demo_user.get("preferred_language", "en"),
                        emergency_contact=demo_user.get("emergency_contact"),
                    )
                )

        db.commit()
        logger.info("Seeded %d departments, %d doctors, demo users.", len(dept_rows), len(doctor_rows))
    finally:
        db.close()


if __name__ == "__main__":
    seed()
