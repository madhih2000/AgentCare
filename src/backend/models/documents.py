import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base


class PatientDocument(Base):
    __tablename__ = "patient_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_id: Mapped[str] = mapped_column(ForeignKey("patient_profiles.id"), nullable=False)
    document_type: Mapped[str] = mapped_column(String(80), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    document_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    is_duplicate_of: Mapped[str | None] = mapped_column(
        ForeignKey("patient_documents.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
