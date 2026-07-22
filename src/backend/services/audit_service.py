import json

from sqlalchemy.orm import Session

from backend.models.audit import AuditEvent
from backend.utils.ids import new_id


def record(
    db: Session,
    *,
    actor_id: str | None,
    action: str,
    entity_type: str,
    entity_id: str,
    metadata: dict | None = None,
) -> AuditEvent:
    event = AuditEvent(
        id=new_id(),
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        metadata_json=json.dumps(metadata or {}),
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def list_events(db: Session, limit: int = 200) -> list[AuditEvent]:
    return (
        db.query(AuditEvent)
        .order_by(AuditEvent.created_at.desc())
        .limit(limit)
        .all()
    )
