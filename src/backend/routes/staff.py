from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.models.user import User
from backend.routes.deps import require_staff
from backend.schemas.appointment import SlotOut
from backend.schemas.clinical import DoctorCreate, DoctorOut, SlotCreate
from backend.schemas.workflow import EscalationDecision, EscalationOut, WorkflowRunOut
from backend.services import appointment_service, department_service, escalation_service, workflow_service
from backend.services.exceptions import ConflictError, NotFoundError

router = APIRouter(prefix="/staff", tags=["staff"])


@router.get("/workflows", response_model=list[WorkflowRunOut])
def list_workflows(user: User = Depends(require_staff), db: Session = Depends(get_db)):
    return workflow_service.list_all_workflow_runs(db)


@router.get("/escalations", response_model=list[EscalationOut])
def list_escalations(user: User = Depends(require_staff), db: Session = Depends(get_db)):
    return escalation_service.list_open_escalations(db)


@router.post("/escalations/{escalation_id}/decision", response_model=EscalationOut)
def decide_escalation(
    escalation_id: str,
    payload: EscalationDecision,
    user: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    try:
        return escalation_service.resolve_escalation(
            db, escalation_id=escalation_id, decision=payload.decision, reviewer_id=user.id
        )
    except ConflictError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except NotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/doctors", response_model=DoctorOut)
def create_doctor(payload: DoctorCreate, user: User = Depends(require_staff), db: Session = Depends(get_db)):
    try:
        return department_service.create_doctor(
            db, department_id=payload.department_id, name=payload.name, actor_id=user.id
        )
    except NotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/slots", response_model=SlotOut)
def create_slot(payload: SlotCreate, user: User = Depends(require_staff), db: Session = Depends(get_db)):
    return appointment_service.create_slot(
        db,
        doctor_id=payload.doctor_id,
        start_time=payload.start_time,
        end_time=payload.end_time,
        actor_id=user.id,
    )
