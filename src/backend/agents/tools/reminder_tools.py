from datetime import datetime

from langchain_core.tools import tool

from backend.db.session import SessionLocal
from backend.services import reminder_service


@tool
def create_appointment_reminder(
    patient_id: str, appointment_id: str, appointment_start: str, actor_id: str
) -> dict:
    """Create a reminder scheduled 24 hours before a booked appointment.
    appointment_start must be an ISO-8601 datetime string."""
    db = SessionLocal()
    try:
        start = datetime.fromisoformat(appointment_start)
        reminder = reminder_service.create_appointment_reminder(
            db, patient_id=patient_id, appointment_id=appointment_id,
            appointment_start=start, actor_id=actor_id,
        )
        return {
            "id": reminder.id,
            "reminder_type": reminder.reminder_type,
            "scheduled_at": reminder.scheduled_at.isoformat(),
        }
    finally:
        db.close()


@tool
def create_document_followup_reminder(patient_id: str, actor_id: str) -> dict:
    """Create a follow-up reminder for a patient who still has missing
    required documents, scheduled a few days out."""
    db = SessionLocal()
    try:
        reminder = reminder_service.create_document_followup_reminder(
            db, patient_id=patient_id, actor_id=actor_id
        )
        return {
            "id": reminder.id,
            "reminder_type": reminder.reminder_type,
            "scheduled_at": reminder.scheduled_at.isoformat(),
        }
    finally:
        db.close()
