from langchain_core.tools import tool

from backend.db.session import SessionLocal
from backend.services import department_service


@tool
def list_departments() -> list[dict]:
    """List all active hospital departments a request could be routed to."""
    db = SessionLocal()
    try:
        return [
            {"id": d.id, "name": d.name, "description": d.description}
            for d in department_service.list_active_departments(db)
        ]
    finally:
        db.close()


@tool
def classify_department(request_text: str) -> dict:
    """Suggest a department for the given free-text patient request by matching
    it against real department records via keyword rules. Returns the matched
    department's id/name, or an empty dict if nothing matched."""
    db = SessionLocal()
    try:
        dept = department_service.classify_department(db, request_text)
        if dept is None:
            return {}
        return {"id": dept.id, "name": dept.name}
    finally:
        db.close()
