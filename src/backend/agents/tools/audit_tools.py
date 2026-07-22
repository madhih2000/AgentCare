from langchain_core.tools import tool

from backend.db.session import SessionLocal
from backend.services import audit_service


@tool
def log_agent_decision(actor_id: str, action: str, entity_type: str, entity_id: str, note: str) -> dict:
    """Record an explicit agent decision/reasoning note to the audit log for
    traceability, separate from the automatic audit events services already
    write on data mutations."""
    db = SessionLocal()
    try:
        event = audit_service.record(
            db, actor_id=actor_id or None, action=action, entity_type=entity_type,
            entity_id=entity_id, metadata={"note": note},
        )
        return {"id": event.id, "action": event.action}
    finally:
        db.close()
