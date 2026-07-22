from datetime import datetime

from pydantic import BaseModel


class AuditEventOut(BaseModel):
    id: str
    actor_id: str | None
    action: str
    entity_type: str
    entity_id: str
    metadata_json: str
    created_at: datetime

    class Config:
        from_attributes = True
