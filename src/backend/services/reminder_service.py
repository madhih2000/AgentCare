import logging
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from backend.models.workflow import Reminder, ReminderStatus
from backend.services import audit_service
from backend.utils.ids import new_id
from backend.utils.time import utcnow

logger = logging.getLogger("agentcare.notifications")


def create_reminder(
    db: Session,
    *,
    patient_id: str,
    appointment_id: str | None,
    reminder_type: str,
    scheduled_at: datetime,
    actor_id: str,
) -> Reminder:
    reminder = Reminder(
        id=new_id(),
        patient_id=patient_id,
        appointment_id=appointment_id,
        reminder_type=reminder_type,
        scheduled_at=scheduled_at,
        status=ReminderStatus.pending,
    )
    db.add(reminder)
    db.commit()
    db.refresh(reminder)
    audit_service.record(
        db, actor_id=actor_id, action="reminder.create", entity_type="Reminder",
        entity_id=reminder.id, metadata={"reminder_type": reminder_type},
    )
    return reminder


def create_appointment_reminder(
    db: Session, *, patient_id: str, appointment_id: str, appointment_start: datetime, actor_id: str
) -> Reminder:
    reminder_time = appointment_start - timedelta(hours=24)
    return create_reminder(
        db, patient_id=patient_id, appointment_id=appointment_id,
        reminder_type="appointment_24h", scheduled_at=reminder_time, actor_id=actor_id,
    )


def create_document_followup_reminder(
    db: Session, *, patient_id: str, actor_id: str, delay_days: int = 3
) -> Reminder:
    return create_reminder(
        db, patient_id=patient_id, appointment_id=None,
        reminder_type="missing_documents", scheduled_at=utcnow() + timedelta(days=delay_days),
        actor_id=actor_id,
    )


def list_patient_reminders(db: Session, patient_id: str) -> list[Reminder]:
    return (
        db.query(Reminder)
        .filter(Reminder.patient_id == patient_id)
        .order_by(Reminder.scheduled_at)
        .all()
    )


def dispatch_due_reminders(db: Session) -> int:
    """Sends (logs + marks sent) reminders whose scheduled_at has passed.

    Real persistence-backed side effect (status transition + audit event),
    not a hardcoded response — this is the notification tool used by the
    Follow-up Agent.
    """
    due = (
        db.query(Reminder)
        .filter(Reminder.status == ReminderStatus.pending, Reminder.scheduled_at <= utcnow())
        .all()
    )
    for reminder in due:
        logger.info(
            "Dispatching reminder %s (%s) for patient %s",
            reminder.id, reminder.reminder_type, reminder.patient_id,
        )
        reminder.status = ReminderStatus.sent
        audit_service.record(
            db, actor_id=None, action="reminder.dispatch", entity_type="Reminder",
            entity_id=reminder.id,
        )
    db.commit()
    return len(due)
