from datetime import date, datetime

from pydantic import BaseModel


class PatientProfileOut(BaseModel):
    id: str
    user_id: str
    date_of_birth: date | None
    phone: str | None
    preferred_language: str
    emergency_contact: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class PatientProfileUpdate(BaseModel):
    date_of_birth: date | None = None
    phone: str | None = None
    preferred_language: str | None = None
    emergency_contact: str | None = None
