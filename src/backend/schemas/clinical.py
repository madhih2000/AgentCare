from datetime import datetime

from pydantic import BaseModel


class DepartmentOut(BaseModel):
    id: str
    name: str
    description: str | None
    active: bool

    class Config:
        from_attributes = True


class DoctorOut(BaseModel):
    id: str
    department_id: str
    name: str
    active: bool

    class Config:
        from_attributes = True


class DoctorCreate(BaseModel):
    department_id: str
    name: str


class SlotCreate(BaseModel):
    doctor_id: str
    start_time: datetime
    end_time: datetime
