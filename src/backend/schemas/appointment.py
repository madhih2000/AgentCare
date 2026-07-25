from datetime import datetime

from pydantic import BaseModel


class SlotOut(BaseModel):
    id: str
    doctor_id: str
    start_time: datetime
    end_time: datetime
    status: str

    class Config:
        from_attributes = True


class SlotDetailOut(BaseModel):
    id: str
    doctor_id: str
    start_time: datetime
    end_time: datetime
    status: str
    appointment_id: str | None = None
    patient_name: str | None = None
    reason: str | None = None


class AppointmentOut(BaseModel):
    id: str
    patient_id: str
    doctor_id: str
    doctor_name: str
    department_name: str | None = None
    slot_id: str
    slot_start: datetime | None = None
    slot_end: datetime | None = None
    status: str
    reason: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BookAppointmentRequest(BaseModel):
    doctor_id: str
    slot_id: str
    reason: str | None = None


class RescheduleRequest(BaseModel):
    new_slot_id: str
