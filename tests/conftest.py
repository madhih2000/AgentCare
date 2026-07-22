import os

os.environ.setdefault("GROQ_API_KEY", "test-key")

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.db.base import Base
import backend.models  # noqa: F401 -- registers all models on Base.metadata

TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture()
def engine():
    eng = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=eng)
    yield eng
    Base.metadata.drop_all(bind=eng)
    eng.dispose()


@pytest.fixture()
def session_factory(engine):
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture()
def db(session_factory):
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(engine, session_factory):
    from fastapi.testclient import TestClient

    from backend.db.session import get_db
    from backend.main import app

    def override_get_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def seeded_clinical(db):
    """A department with one doctor and one open slot — the minimum fixture
    most appointment/document tests need."""
    from datetime import timedelta

    from backend.models.clinical import AppointmentSlot, Department, Doctor, SlotStatus
    from backend.utils.ids import new_id
    from backend.utils.time import utcnow

    department = Department(id=new_id(), name="Cardiology", description="Heart care", active=True)
    doctor = Doctor(id=new_id(), department_id=department.id, name="Dr. Test", active=True)
    slot = AppointmentSlot(
        id=new_id(),
        doctor_id=doctor.id,
        start_time=utcnow() + timedelta(days=1),
        end_time=utcnow() + timedelta(days=1, minutes=30),
        status=SlotStatus.open,
    )
    db.add_all([department, doctor, slot])
    db.commit()
    return {"department": department, "doctor": doctor, "slot": slot}


@pytest.fixture()
def patient_user(db):
    from backend.services import auth_service

    user = auth_service.register_user(
        db, name="Test Patient", email="patient@example.com", password="Password123!", role="patient"
    )
    return user


@pytest.fixture()
def patient_profile(db, patient_user):
    from backend.services import patient_service

    return patient_service.get_profile_by_user_id(db, patient_user.id)
