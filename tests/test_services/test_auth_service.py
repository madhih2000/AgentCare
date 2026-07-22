import pytest

from backend.services import auth_service
from backend.services.exceptions import ConflictError, UnauthorizedError


def test_register_user_creates_patient_profile(db):
    user = auth_service.register_user(
        db, name="Ada Lovelace", email="ada@example.com", password="Password123!", role="patient"
    )
    assert user.id
    assert user.email == "ada@example.com"
    assert user.password_hash != "Password123!"

    from backend.services import patient_service

    profile = patient_service.get_profile_by_user_id(db, user.id)
    assert profile.user_id == user.id


def test_register_duplicate_email_raises_conflict(db):
    auth_service.register_user(db, name="A", email="dup@example.com", password="Password123!", role="patient")
    with pytest.raises(ConflictError):
        auth_service.register_user(db, name="B", email="dup@example.com", password="Password123!", role="patient")


def test_authenticate_success_and_failure(db):
    auth_service.register_user(
        db, name="Bob", email="bob@example.com", password="CorrectHorse1!", role="patient"
    )

    user, token = auth_service.authenticate(db, email="bob@example.com", password="CorrectHorse1!")
    assert user.email == "bob@example.com"
    assert token

    with pytest.raises(UnauthorizedError):
        auth_service.authenticate(db, email="bob@example.com", password="wrong-password")

    with pytest.raises(UnauthorizedError):
        auth_service.authenticate(db, email="nobody@example.com", password="whatever")
