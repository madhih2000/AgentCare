from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.models.user import User
from backend.routes.deps import require_staff
from backend.schemas.audit import AuditEventOut
from backend.services import audit_service

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=list[AuditEventOut])
def list_audit_events(user: User = Depends(require_staff), db: Session = Depends(get_db)):
    return audit_service.list_events(db)
