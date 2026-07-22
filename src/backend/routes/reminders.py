from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.models.user import User
from backend.routes.deps import require_patient
from backend.schemas.workflow import ReminderOut
from backend.services import patient_service, reminder_service

router = APIRouter(prefix="/reminders", tags=["reminders"])


@router.get("", response_model=list[ReminderOut])
def list_my_reminders(user: User = Depends(require_patient), db: Session = Depends(get_db)):
    profile = patient_service.get_profile_by_user_id(db, user.id)
    return reminder_service.list_patient_reminders(db, profile.id)
