from datetime import date

from sqlalchemy.orm import Session

from backend.models.user import PatientProfile, User, UserRole
from backend.services import audit_service
from backend.services.exceptions import ConflictError, UnauthorizedError
from backend.utils.ids import new_id
from backend.utils.security import create_access_token, hash_password, verify_password


def register_user(
    db: Session,
    *,
    name: str,
    email: str,
    password: str,
    role: str = "patient",
    date_of_birth: date | None = None,
    phone: str | None = None,
    preferred_language: str = "en",
    emergency_contact: str | None = None,
) -> User:
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise ConflictError(f"A user with email {email} already exists")

    user = User(
        id=new_id(),
        name=name,
        email=email,
        password_hash=hash_password(password),
        role=UserRole(role),
    )
    db.add(user)
    db.flush()

    if user.role == UserRole.patient:
        profile = PatientProfile(
            id=new_id(),
            user_id=user.id,
            date_of_birth=date_of_birth,
            phone=phone,
            preferred_language=preferred_language,
            emergency_contact=emergency_contact,
        )
        db.add(profile)

    db.commit()
    db.refresh(user)
    audit_service.record(
        db, actor_id=user.id, action="user.register", entity_type="User", entity_id=user.id,
        metadata={"role": user.role.value},
    )
    return user


def authenticate(db: Session, *, email: str, password: str) -> tuple[User, str]:
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.password_hash):
        raise UnauthorizedError("Invalid email or password")

    token = create_access_token(subject=user.id, role=user.role.value)
    audit_service.record(
        db, actor_id=user.id, action="user.login", entity_type="User", entity_id=user.id
    )
    return user, token


def get_user_by_id(db: Session, user_id: str) -> User | None:
    return db.query(User).filter(User.id == user_id).first()
