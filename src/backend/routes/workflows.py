import asyncio
import json
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.agents.graph import run_workflow
from backend.db.session import SessionLocal, get_db
from backend.models.user import User
from backend.routes.deps import require_patient
from backend.schemas.workflow import WorkflowRequestIn, WorkflowRunOut, WorkflowStatusOut
from backend.services import patient_service, workflow_service
from backend.services.exceptions import NotFoundError

router = APIRouter(prefix="/workflows", tags=["workflows"])
logger = logging.getLogger("agentcare.routes.workflows")

TERMINAL_STATUSES = {"completed", "failed", "escalated"}


def _execute_workflow(workflow_run_id: str, patient_id: str, actor_id: str, request_text: str) -> None:
    try:
        run_workflow(
            workflow_run_id=workflow_run_id,
            patient_id=patient_id,
            actor_id=actor_id,
            request_text=request_text,
        )
    except Exception:
        logger.exception("Background workflow %s failed", workflow_run_id)


def _to_status_out(run) -> WorkflowStatusOut:
    state = json.loads(run.state_json or "{}")
    trace = state.get("trace", [])
    return WorkflowStatusOut(
        id=run.id,
        patient_id=run.patient_id,
        current_step=run.current_step,
        status=run.status.value,
        created_at=run.created_at,
        updated_at=run.updated_at,
        trace=trace,
        summary=trace[-1]["output"] if trace else None,
        escalated=state.get("escalated", False),
        escalation_reason=state.get("escalation_reason"),
        department_id=state.get("department_id"),
        department_name=state.get("department_name"),
        appointment_id=state.get("appointment_id"),
        appointment_start=state.get("appointment_start"),
        missing_documents=state.get("missing_documents", []),
        final_summary=state.get("final_summary"),
    )


@router.post("", response_model=WorkflowRunOut)
def submit_request(
    payload: WorkflowRequestIn,
    background_tasks: BackgroundTasks,
    user: User = Depends(require_patient),
    db: Session = Depends(get_db),
):
    profile = patient_service.get_profile_by_user_id(db, user.id)
    run = workflow_service.create_workflow_run(db, patient_id=profile.id, actor_id=user.id)

    background_tasks.add_task(_execute_workflow, run.id, profile.id, user.id, payload.message)
    return run


@router.get("/{workflow_run_id}/stream")
async def stream_workflow_status(
    workflow_run_id: str, user: User = Depends(require_patient), db: Session = Depends(get_db)
):
    """Server-Sent Events endpoint: pushes a 'stage' event each time a new
    agent trace entry is persisted (i.e. each time an agent finishes its
    step), and a final 'done' event once the workflow reaches a terminal
    status. The workflow itself still executes in the background task kicked
    off by POST /workflows — this endpoint watches the persisted state and
    streams it, so the frontend gets push-like updates without polling."""
    profile = patient_service.get_profile_by_user_id(db, user.id)
    try:
        run = workflow_service.get_workflow_run(db, workflow_run_id)
    except NotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if run.patient_id != profile.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Not your workflow")

    async def event_stream():
        seen_steps = 0
        while True:
            await asyncio.sleep(0.4)
            check_db = SessionLocal()
            try:
                current_run = workflow_service.get_workflow_run(check_db, workflow_run_id)
            finally:
                check_db.close()

            state = json.loads(current_run.state_json or "{}")
            trace = state.get("trace", [])
            for step in trace[seen_steps:]:
                yield f"event: stage\ndata: {json.dumps(step)}\n\n"
            seen_steps = len(trace)

            if current_run.status.value in TERMINAL_STATUSES:
                payload = _to_status_out(current_run).model_dump(mode="json")
                yield f"event: done\ndata: {json.dumps(payload)}\n\n"
                break

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/{workflow_run_id}", response_model=WorkflowStatusOut)
def get_workflow_status(
    workflow_run_id: str, user: User = Depends(require_patient), db: Session = Depends(get_db)
):
    try:
        run = workflow_service.get_workflow_run(db, workflow_run_id)
    except NotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _to_status_out(run)


@router.get("", response_model=list[WorkflowRunOut])
def list_my_workflows(user: User = Depends(require_patient), db: Session = Depends(get_db)):
    profile = patient_service.get_profile_by_user_id(db, user.id)
    return workflow_service.list_patient_workflow_runs(db, profile.id)
