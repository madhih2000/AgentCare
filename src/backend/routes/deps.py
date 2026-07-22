from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.models.user import User
from backend.services.auth_service import get_user_by_id
from backend.utils.security import decode_access_token


def get_current_user(
    access_token: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
) -> User:
    if not access_token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    payload = decode_access_token(access_token)
    if not payload:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session")

    user = get_user_by_id(db, payload["sub"])
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="User no longer exists")
    return user


def get_optional_user(
    access_token: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
) -> User | None:
    if not access_token:
        return None
    payload = decode_access_token(access_token)
    if not payload:
        return None
    return get_user_by_id(db, payload["sub"])


def require_roles(*roles: str):
    """FastAPI dependency factory enforcing role membership server-side.
    Frontend hiding of buttons is not sufficient — every mutating/staff route
    depends on this."""

    def _dependency(user: User = Depends(get_current_user)) -> User:
        if user.role.value not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Not authorized for this action")
        return user

    return _dependency


require_patient = require_roles("patient")
require_staff = require_roles("staff", "admin")
require_admin = require_roles("admin")
require_any = require_roles("patient", "staff", "admin")
