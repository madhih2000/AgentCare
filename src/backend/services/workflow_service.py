import json

from sqlalchemy.orm import Session

from backend.models.workflow import WorkflowRun, WorkflowStatus
from backend.services import audit_service
from backend.services.exceptions import NotFoundError
from backend.utils.ids import new_id


def create_workflow_run(db: Session, *, patient_id: str, actor_id: str) -> WorkflowRun:
    run = WorkflowRun(
        id=new_id(),
        patient_id=patient_id,
        current_step="coordinator",
        state_json="{}",
        status=WorkflowStatus.in_progress,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    audit_service.record(
        db, actor_id=actor_id, action="workflow.create", entity_type="WorkflowRun",
        entity_id=run.id,
    )
    return run


def update_workflow_state(
    db: Session,
    *,
    workflow_run_id: str,
    current_step: str,
    state: dict,
    status: WorkflowStatus | None = None,
) -> WorkflowRun:
    run = get_workflow_run(db, workflow_run_id)
    run.current_step = current_step
    run.state_json = json.dumps(state, default=str)
    if status is not None:
        run.status = status
    db.commit()
    db.refresh(run)
    return run


def get_workflow_run(db: Session, workflow_run_id: str) -> WorkflowRun:
    run = db.query(WorkflowRun).filter(WorkflowRun.id == workflow_run_id).first()
    if not run:
        raise NotFoundError(f"WorkflowRun {workflow_run_id} not found")
    return run


def list_patient_workflow_runs(db: Session, patient_id: str) -> list[WorkflowRun]:
    return (
        db.query(WorkflowRun)
        .filter(WorkflowRun.patient_id == patient_id)
        .order_by(WorkflowRun.created_at.desc())
        .all()
    )


def list_all_workflow_runs(db: Session, limit: int = 100) -> list[WorkflowRun]:
    return (
        db.query(WorkflowRun)
        .order_by(WorkflowRun.created_at.desc())
        .limit(limit)
        .all()
    )
