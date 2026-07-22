from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.routes.deps import require_any
from backend.schemas.appointment import SlotOut
from backend.schemas.clinical import DepartmentOut, DoctorOut
from backend.services import appointment_service, department_service

router = APIRouter(prefix="/clinical", tags=["clinical"])


@router.get("/departments", response_model=list[DepartmentOut])
def list_departments(db: Session = Depends(get_db), _=Depends(require_any)):
    return department_service.list_active_departments(db)


@router.get("/departments/{department_id}/doctors", response_model=list[DoctorOut])
def list_doctors(department_id: str, db: Session = Depends(get_db), _=Depends(require_any)):
    return department_service.list_doctors(db, department_id)


@router.get("/doctors/{doctor_id}/slots", response_model=list[SlotOut])
def list_slots(doctor_id: str, db: Session = Depends(get_db), _=Depends(require_any)):
    return appointment_service.list_open_slots(db, doctor_id)
