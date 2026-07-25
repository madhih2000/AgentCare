from datetime import datetime

from sqlalchemy.orm import Session

from backend.models.clinical import (
    Appointment,
    AppointmentSlot,
    AppointmentStatus,
    SlotStatus,
)
from backend.models.user import PatientProfile, User
from backend.services import audit_service
from backend.services.exceptions import ConflictError, NotFoundError, SlotUnavailableError
from backend.utils.ids import new_id


def create_slot(
    db: Session, *, doctor_id: str, start_time: datetime, end_time: datetime, actor_id: str
) -> AppointmentSlot:
    slot = AppointmentSlot(
        id=new_id(), doctor_id=doctor_id, start_time=start_time, end_time=end_time, status=SlotStatus.open
    )
    db.add(slot)
    db.commit()
    db.refresh(slot)
    audit_service.record(
        db, actor_id=actor_id, action="slot.create", entity_type="AppointmentSlot", entity_id=slot.id,
        metadata={"doctor_id": doctor_id},
    )
    return slot


def list_open_slots(db: Session, doctor_id: str) -> list[AppointmentSlot]:
    return (
        db.query(AppointmentSlot)
        .filter(AppointmentSlot.doctor_id == doctor_id, AppointmentSlot.status == SlotStatus.open)
        .order_by(AppointmentSlot.start_time)
        .all()
    )


def list_doctor_calendar(db: Session, doctor_id: str) -> list[dict]:
    """Every slot for a doctor (open, held, booked) plus who's booked into it
    — the staff timetable/calendar view. Looks up the live booked Appointment
    with an explicit query rather than AppointmentSlot.appointment's
    one-to-one backref, which can point at a stale cancelled row once a slot
    has been cancelled and later rebooked."""
    slots = (
        db.query(AppointmentSlot)
        .filter(AppointmentSlot.doctor_id == doctor_id)
        .order_by(AppointmentSlot.start_time)
        .all()
    )
    entries = []
    for slot in slots:
        appointment_id = None
        patient_name = None
        reason = None
        if slot.status == SlotStatus.booked:
            row = (
                db.query(Appointment.id, Appointment.reason, User.name)
                .join(PatientProfile, PatientProfile.id == Appointment.patient_id)
                .join(User, User.id == PatientProfile.user_id)
                .filter(
                    Appointment.slot_id == slot.id,
                    Appointment.status.in_([AppointmentStatus.booked, AppointmentStatus.rescheduled]),
                )
                .first()
            )
            if row:
                appointment_id, reason, patient_name = row
        entries.append(
            {
                "id": slot.id,
                "doctor_id": slot.doctor_id,
                "start_time": slot.start_time,
                "end_time": slot.end_time,
                "status": slot.status.value,
                "appointment_id": appointment_id,
                "patient_name": patient_name,
                "reason": reason,
            }
        )
    return entries


def get_slot(db: Session, slot_id: str) -> AppointmentSlot:
    slot = db.query(AppointmentSlot).filter(AppointmentSlot.id == slot_id).first()
    if not slot:
        raise NotFoundError(f"Slot {slot_id} not found")
    return slot


def book_appointment(
    db: Session, *, patient_id: str, doctor_id: str, slot_id: str, reason: str | None, actor_id: str
) -> Appointment:
    slot = get_slot(db, slot_id)
    if slot.doctor_id != doctor_id:
        raise ConflictError("Slot does not belong to the requested doctor")
    if slot.status != SlotStatus.open:
        raise SlotUnavailableError(f"Slot {slot_id} is not available")

    existing = (
        db.query(Appointment)
        .filter(
            Appointment.patient_id == patient_id,
            Appointment.slot_id == slot_id,
            Appointment.status == AppointmentStatus.booked,
        )
        .first()
    )
    if existing:
        raise ConflictError("Patient already has this appointment booked")

    slot.status = SlotStatus.booked
    appointment = Appointment(
        id=new_id(),
        patient_id=patient_id,
        doctor_id=doctor_id,
        slot_id=slot_id,
        status=AppointmentStatus.booked,
        reason=reason,
    )
    db.add(appointment)
    db.commit()
    db.refresh(appointment)
    audit_service.record(
        db, actor_id=actor_id, action="appointment.book", entity_type="Appointment",
        entity_id=appointment.id, metadata={"slot_id": slot_id, "doctor_id": doctor_id},
    )
    return appointment


def reschedule_appointment(
    db: Session, *, appointment_id: str, new_slot_id: str, actor_id: str
) -> Appointment:
    appointment = get_appointment(db, appointment_id)
    if appointment.status not in (AppointmentStatus.booked, AppointmentStatus.rescheduled):
        raise ConflictError("Only booked appointments can be rescheduled")

    new_slot = get_slot(db, new_slot_id)
    if new_slot.status != SlotStatus.open:
        raise SlotUnavailableError(f"Slot {new_slot_id} is not available")

    old_slot = get_slot(db, appointment.slot_id)
    old_slot.status = SlotStatus.open

    new_slot.status = SlotStatus.booked
    appointment.slot_id = new_slot_id
    appointment.doctor_id = new_slot.doctor_id
    appointment.status = AppointmentStatus.rescheduled
    db.commit()
    db.refresh(appointment)
    audit_service.record(
        db, actor_id=actor_id, action="appointment.reschedule", entity_type="Appointment",
        entity_id=appointment.id, metadata={"new_slot_id": new_slot_id},
    )
    return appointment


def cancel_appointment(db: Session, *, appointment_id: str, actor_id: str) -> Appointment:
    appointment = get_appointment(db, appointment_id)
    if appointment.status == AppointmentStatus.cancelled:
        raise ConflictError("Appointment already cancelled")

    slot = get_slot(db, appointment.slot_id)
    slot.status = SlotStatus.open
    appointment.status = AppointmentStatus.cancelled
    db.commit()
    db.refresh(appointment)
    audit_service.record(
        db, actor_id=actor_id, action="appointment.cancel", entity_type="Appointment",
        entity_id=appointment.id,
    )
    return appointment


def get_appointment(db: Session, appointment_id: str) -> Appointment:
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        raise NotFoundError(f"Appointment {appointment_id} not found")
    return appointment


def list_patient_appointments(db: Session, patient_id: str) -> list[Appointment]:
    return (
        db.query(Appointment)
        .filter(Appointment.patient_id == patient_id)
        .order_by(Appointment.created_at.desc())
        .all()
    )
