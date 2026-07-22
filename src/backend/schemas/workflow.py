from datetime import datetime

from pydantic import BaseModel


class WorkflowRequestIn(BaseModel):
    message: str


class WorkflowRunOut(BaseModel):
    id: str
    patient_id: str
    current_step: str
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WorkflowStatusOut(WorkflowRunOut):
    trace: list[dict]
    summary: str | None = None
    escalated: bool = False
    escalation_reason: str | None = None
    department_id: str | None = None
    department_name: str | None = None
    appointment_id: str | None = None
    appointment_start: str | None = None
    missing_documents: list[str] = []
    final_summary: str | None = None


class EscalationOut(BaseModel):
    id: str
    workflow_run_id: str
    reason: str
    status: str
    reviewed_by: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class EscalationDecision(BaseModel):
    decision: str  # "approved" | "rejected"
    note: str | None = None


class ReminderOut(BaseModel):
    id: str
    patient_id: str
    appointment_id: str | None
    reminder_type: str
    scheduled_at: datetime
    status: str

    class Config:
        from_attributes = True
