from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.models.user import User
from backend.routes.deps import require_patient
from backend.schemas.appointment import AppointmentOut, BookAppointmentRequest, RescheduleRequest
from backend.services import appointment_service, patient_service
from backend.services.exceptions import ConflictError, NotFoundError, SlotUnavailableError

router = APIRouter(prefix="/appointments", tags=["appointments"])


@router.get("", response_model=list[AppointmentOut])
def list_my_appointments(user: User = Depends(require_patient), db: Session = Depends(get_db)):
    profile = patient_service.get_profile_by_user_id(db, user.id)
    return appointment_service.list_patient_appointments(db, profile.id)


@router.post("", response_model=AppointmentOut)
def book_appointment(
    payload: BookAppointmentRequest,
    user: User = Depends(require_patient),
    db: Session = Depends(get_db),
):
    profile = patient_service.get_profile_by_user_id(db, user.id)
    try:
        return appointment_service.book_appointment(
            db,
            patient_id=profile.id,
            doctor_id=payload.doctor_id,
            slot_id=payload.slot_id,
            reason=payload.reason,
            actor_id=user.id,
        )
    except (ConflictError, SlotUnavailableError) as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except NotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/{appointment_id}/reschedule", response_model=AppointmentOut)
def reschedule(
    appointment_id: str,
    payload: RescheduleRequest,
    user: User = Depends(require_patient),
    db: Session = Depends(get_db),
):
    try:
        return appointment_service.reschedule_appointment(
            db, appointment_id=appointment_id, new_slot_id=payload.new_slot_id, actor_id=user.id
        )
    except (ConflictError, SlotUnavailableError) as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except NotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/{appointment_id}/cancel", response_model=AppointmentOut)
def cancel(appointment_id: str, user: User = Depends(require_patient), db: Session = Depends(get_db)):
    try:
        return appointment_service.cancel_appointment(db, appointment_id=appointment_id, actor_id=user.id)
    except ConflictError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except NotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
