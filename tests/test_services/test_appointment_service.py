import pytest

from backend.services import appointment_service
from backend.services.exceptions import ConflictError, SlotUnavailableError


def test_book_appointment_marks_slot_booked(db, seeded_clinical, patient_profile):
    doctor = seeded_clinical["doctor"]
    slot = seeded_clinical["slot"]

    appt = appointment_service.book_appointment(
        db, patient_id=patient_profile.id, doctor_id=doctor.id, slot_id=slot.id,
        reason="Checkup", actor_id=patient_profile.user_id,
    )
    assert appt.status.value == "booked"

    refreshed_slot = appointment_service.get_slot(db, slot.id)
    assert refreshed_slot.status.value == "booked"


def test_double_booking_same_slot_raises_unavailable(db, seeded_clinical, patient_profile):
    doctor = seeded_clinical["doctor"]
    slot = seeded_clinical["slot"]

    appointment_service.book_appointment(
        db, patient_id=patient_profile.id, doctor_id=doctor.id, slot_id=slot.id,
        reason=None, actor_id=patient_profile.user_id,
    )
    with pytest.raises(SlotUnavailableError):
        appointment_service.book_appointment(
            db, patient_id=patient_profile.id, doctor_id=doctor.id, slot_id=slot.id,
            reason=None, actor_id=patient_profile.user_id,
        )


def test_reschedule_frees_old_slot_and_books_new(db, seeded_clinical, patient_profile):
    from datetime import timedelta

    from backend.models.clinical import AppointmentSlot, SlotStatus
    from backend.utils.ids import new_id
    from backend.utils.time import utcnow

    doctor = seeded_clinical["doctor"]
    old_slot = seeded_clinical["slot"]
    new_slot = AppointmentSlot(
        id=new_id(), doctor_id=doctor.id,
        start_time=utcnow() + timedelta(days=2), end_time=utcnow() + timedelta(days=2, minutes=30),
        status=SlotStatus.open,
    )
    db.add(new_slot)
    db.commit()

    appt = appointment_service.book_appointment(
        db, patient_id=patient_profile.id, doctor_id=doctor.id, slot_id=old_slot.id,
        reason=None, actor_id=patient_profile.user_id,
    )
    rescheduled = appointment_service.reschedule_appointment(
        db, appointment_id=appt.id, new_slot_id=new_slot.id, actor_id=patient_profile.user_id
    )
    assert rescheduled.slot_id == new_slot.id
    assert rescheduled.status.value == "rescheduled"
    assert appointment_service.get_slot(db, old_slot.id).status.value == "open"
    assert appointment_service.get_slot(db, new_slot.id).status.value == "booked"


def test_cancel_appointment_frees_slot(db, seeded_clinical, patient_profile):
    doctor = seeded_clinical["doctor"]
    slot = seeded_clinical["slot"]
    appt = appointment_service.book_appointment(
        db, patient_id=patient_profile.id, doctor_id=doctor.id, slot_id=slot.id,
        reason=None, actor_id=patient_profile.user_id,
    )
    cancelled = appointment_service.cancel_appointment(db, appointment_id=appt.id, actor_id=patient_profile.user_id)
    assert cancelled.status.value == "cancelled"
    assert appointment_service.get_slot(db, slot.id).status.value == "open"

    with pytest.raises(ConflictError):
        appointment_service.cancel_appointment(db, appointment_id=appt.id, actor_id=patient_profile.user_id)
