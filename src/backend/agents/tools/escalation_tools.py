from langchain_core.tools import tool

from backend.db.session import SessionLocal
from backend.services import escalation_service


@tool
def create_escalation(workflow_run_id: str, reason: str, actor_id: str) -> dict:
    """Persist a human-review escalation for this workflow run and the given
    reason (emergency, diagnosis/prescription request, or ambiguous/unsafe
    administrative request). This halts automated processing until a staff
    member reviews it."""
    db = SessionLocal()
    try:
        escalation = escalation_service.create_escalation(
            db, workflow_run_id=workflow_run_id, reason=reason, actor_id=actor_id or None
        )
        return {"id": escalation.id, "status": escalation.status.value, "reason": escalation.reason}
    finally:
        db.close()
