from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.db.session import get_db
from backend.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserOut
from backend.services import auth_service
from backend.services.exceptions import ConflictError, UnauthorizedError

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()

COOKIE_MAX_AGE = settings.jwt_expire_minutes * 60


@router.post("/register", response_model=TokenResponse)
def register(payload: RegisterRequest, response: Response, db: Session = Depends(get_db)):
    try:
        user = auth_service.register_user(
            db,
            name=payload.name,
            email=payload.email,
            password=payload.password,
            role=payload.role,
            date_of_birth=payload.date_of_birth,
            phone=payload.phone,
            preferred_language=payload.preferred_language,
            emergency_contact=payload.emergency_contact,
        )
    except ConflictError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    _, token = auth_service.authenticate(db, email=payload.email, password=payload.password)
    response.set_cookie("access_token", token, httponly=True, max_age=COOKIE_MAX_AGE, samesite="lax")
    return TokenResponse(access_token=token, role=user.role.value, user_id=user.id)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
    try:
        user, token = auth_service.authenticate(db, email=payload.email, password=payload.password)
    except UnauthorizedError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    response.set_cookie("access_token", token, httponly=True, max_age=COOKIE_MAX_AGE, samesite="lax")
    return TokenResponse(access_token=token, role=user.role.value, user_id=user.id)


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie("access_token")
    return {"ok": True}
