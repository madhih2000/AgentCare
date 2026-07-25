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
def select_department(department_id: str) -> dict:
    """Confirm the department you've chosen after reviewing list_departments'
    results. This is what actually sets the routing decision — your written
    reasoning alone does not; you must call this with the id of one of the
    real departments list_departments returned. Validates the id against
    real records and returns an error if it doesn't match an active
    department (never invent an id)."""
    db = SessionLocal()
    try:
        dept = department_service.get_active_department(db, department_id)
        if dept is None:
            return {"error": f"No active department with id {department_id}"}
        return {"id": dept.id, "name": dept.name}
    finally:
        db.close()


@tool
def classify_department(request_text: str) -> dict:
    """Fallback only: suggest a department by matching the given free-text
    request against real department records via a fixed keyword list. Use
    select_department for your actual routing decision — this exists for
    cases where you're unsure and want a second, deterministic opinion, not
    as the primary way to route. Returns an empty dict if nothing matched."""
    db = SessionLocal()
    try:
        dept = department_service.classify_department(db, request_text)
        if dept is None:
            return {}
        return {"id": dept.id, "name": dept.name}
    finally:
        db.close()
