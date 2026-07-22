from datetime import date, datetime

from pydantic import BaseModel


class DocumentOut(BaseModel):
    id: str
    patient_id: str
    document_type: str
    file_path: str
    document_date: date | None
    checksum: str
    is_duplicate_of: str | None
    created_at: datetime

    class Config:
        from_attributes = True
