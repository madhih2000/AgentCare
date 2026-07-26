from langchain_core.tools import tool

from backend.db.session import SessionLocal
from backend.services import appointment_service, department_service
from backend.services.exceptions import ServiceError


@tool
def list_doctors(department_id: str) -> list[dict]:
    """List active doctors within a given department id."""
    db = SessionLocal()
    try:
        return [
            {"id": doc.id, "name": doc.name, "department_id": doc.department_id}
            for doc in department_service.list_doctors(db, department_id)
        ]
    finally:
        db.close()


@tool
def list_open_slots(doctor_id: str) -> list[dict]:
    """List open, bookable appointment slots for a given doctor id, soonest first."""
    db = SessionLocal()
    try:
        return [
            {
                "id": slot.id,
                "doctor_id": slot.doctor_id,
                "start_time": slot.start_time.isoformat(),
                "end_time": slot.end_time.isoformat(),
            }
            for slot in appointment_service.list_open_slots(db, doctor_id)
        ]
    finally:
        db.close()


@tool
def list_patient_appointment_history(patient_id: str) -> list[dict]:
    """List this patient's past and current appointments — doctor, department,
    status, and slot time — most recent first. Check this before asking the
    patient to choose between multiple available doctors: if they've already
    seen one of them, prefer that doctor for continuity of care instead of
    asking. Only ask if history doesn't clearly point to one."""
    db = SessionLocal()
    try:
        return [
            {
                "doctor_id": appt.doctor_id,
                "doctor_name": appt.doctor_name,
                "department_name": appt.department_name,
                "status": appt.status.value,
                "slot_start": appt.slot_start.isoformat() if appt.slot_start else None,
            }
            for appt in appointment_service.list_patient_appointments(db, patient_id)
        ]
    finally:
        db.close()


@tool
def book_appointment(patient_id: str, doctor_id: str, slot_id: str, reason: str, actor_id: str) -> dict:
    """Book an appointment for a patient with a doctor for a specific open slot.
    reason is the patient's stated reason for the visit. actor_id is the acting
    user id for audit purposes. Returns the created appointment including
    slot_start, or an error if the slot is unavailable/conflicting."""
    db = SessionLocal()
    try:
        appt = appointment_service.book_appointment(
            db, patient_id=patient_id, doctor_id=doctor_id, slot_id=slot_id,
            reason=reason or None, actor_id=actor_id,
        )
        return {
            "id": appt.id,
            "status": appt.status.value,
            "doctor_id": appt.doctor_id,
            "slot_id": appt.slot_id,
            "slot_start": appt.slot.start_time.isoformat(),
        }
    except ServiceError as exc:
        return {"error": str(exc)}
    finally:
        db.close()


@tool
def reschedule_appointment(appointment_id: str, new_slot_id: str, actor_id: str) -> dict:
    """Reschedule an existing appointment to a new open slot id."""
    db = SessionLocal()
    try:
        appt = appointment_service.reschedule_appointment(
            db, appointment_id=appointment_id, new_slot_id=new_slot_id, actor_id=actor_id
        )
        return {
            "id": appt.id,
            "status": appt.status.value,
            "slot_id": appt.slot_id,
            "slot_start": appt.slot.start_time.isoformat(),
        }
    except ServiceError as exc:
        return {"error": str(exc)}
    finally:
        db.close()


@tool
def cancel_appointment(appointment_id: str, actor_id: str) -> dict:
    """Cancel an existing appointment by id, freeing its slot."""
    db = SessionLocal()
    try:
        appt = appointment_service.cancel_appointment(db, appointment_id=appointment_id, actor_id=actor_id)
        return {"id": appt.id, "status": appt.status.value}
    except ServiceError as exc:
        return {"error": str(exc)}
    finally:
        db.close()
