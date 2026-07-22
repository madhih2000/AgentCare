import json
from typing import Optional, TypedDict

from backend.db.session import SessionLocal
from backend.models.workflow import WorkflowStatus
from backend.services import workflow_service


class WorkflowState(TypedDict, total=False):
    workflow_run_id: str
    patient_id: str
    actor_id: Optional[str]
    request_text: str
    trace: list[dict]
    escalated: bool
    escalation_reason: Optional[str]
    department_id: Optional[str]
    department_name: Optional[str]
    appointment_id: Optional[str]
    appointment_start: Optional[str]
    missing_documents: list[str]
    status: str
    final_summary: Optional[str]


def persist_step(
    state: WorkflowState,
    trace: list[dict],
    step: str,
    status: str | None = None,
    **extra_fields,
) -> None:
    """Merges this node's trace + any newly-known fields (department,
    appointment, missing documents, ...) into the WorkflowRun row's persisted
    state, so the staff/patient UI and the SSE stream can read structured
    progress via plain SQL — independent of, and in addition to, the
    LangGraph checkpointer. Merges rather than overwrites so fields set by an
    earlier node in the graph (e.g. department_name from routing) survive
    later nodes' persist calls."""
    db = SessionLocal()
    try:
        run = workflow_service.get_workflow_run(db, state["workflow_run_id"])
        current = json.loads(run.state_json or "{}")
        current.update(extra_fields)
        current["trace"] = trace
        workflow_service.update_workflow_state(
            db,
            workflow_run_id=state["workflow_run_id"],
            current_step=step,
            state=current,
            status=WorkflowStatus(status) if status else None,
        )
    finally:
        db.close()
