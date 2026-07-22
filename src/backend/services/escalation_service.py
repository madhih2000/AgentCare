from sqlalchemy.orm import Session

from backend.models.workflow import Escalation, EscalationStatus, WorkflowStatus
from backend.services import audit_service
from backend.services.exceptions import ConflictError, NotFoundError
from backend.utils.ids import new_id


def create_escalation(
    db: Session, *, workflow_run_id: str, reason: str, actor_id: str | None
) -> Escalation:
    escalation = Escalation(
        id=new_id(),
        workflow_run_id=workflow_run_id,
        reason=reason,
        status=EscalationStatus.open,
    )
    db.add(escalation)
    db.commit()
    db.refresh(escalation)
    audit_service.record(
        db, actor_id=actor_id, action="escalation.create", entity_type="Escalation",
        entity_id=escalation.id, metadata={"reason": reason, "workflow_run_id": workflow_run_id},
    )
    return escalation


def list_open_escalations(db: Session) -> list[Escalation]:
    return (
        db.query(Escalation)
        .filter(Escalation.status == EscalationStatus.open)
        .order_by(Escalation.created_at.desc())
        .all()
    )


def get_escalation(db: Session, escalation_id: str) -> Escalation:
    escalation = db.query(Escalation).filter(Escalation.id == escalation_id).first()
    if not escalation:
        raise NotFoundError(f"Escalation {escalation_id} not found")
    return escalation


def resolve_escalation(
    db: Session, *, escalation_id: str, decision: str, reviewer_id: str
) -> Escalation:
    """Only a staff/admin reviewer_id (enforced by the route's RBAC dependency,
    never trusted from client input) may resolve an escalation."""
    escalation = get_escalation(db, escalation_id)
    if escalation.status != EscalationStatus.open:
        raise ConflictError("Escalation already resolved")
    if decision not in ("approved", "rejected"):
        raise ConflictError("decision must be 'approved' or 'rejected'")

    escalation.status = EscalationStatus(decision)
    escalation.reviewed_by = reviewer_id
    db.commit()
    db.refresh(escalation)
    audit_service.record(
        db, actor_id=reviewer_id, action=f"escalation.{decision}", entity_type="Escalation",
        entity_id=escalation.id,
    )
    return escalation
