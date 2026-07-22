from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.models.user import User
from backend.routes.deps import require_patient
from backend.schemas.patient import PatientProfileOut, PatientProfileUpdate
from backend.services import patient_service
from backend.services.exceptions import NotFoundError

router = APIRouter(prefix="/patients", tags=["patients"])


@router.get("/me", response_model=PatientProfileOut)
def get_my_profile(user: User = Depends(require_patient), db: Session = Depends(get_db)):
    try:
        return patient_service.get_profile_by_user_id(db, user.id)
    except NotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.patch("/me", response_model=PatientProfileOut)
def update_my_profile(
    payload: PatientProfileUpdate,
    user: User = Depends(require_patient),
    db: Session = Depends(get_db),
):
    return patient_service.update_profile(
        db, user_id=user.id, actor_id=user.id, updates=payload.model_dump(exclude_unset=True)
    )
