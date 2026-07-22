import pytest

from backend.services import escalation_service, workflow_service
from backend.services.exceptions import ConflictError


def test_create_and_resolve_escalation(db, patient_profile):
    run = workflow_service.create_workflow_run(db, patient_id=patient_profile.id, actor_id=patient_profile.user_id)
    escalation = escalation_service.create_escalation(
        db, workflow_run_id=run.id, reason="Emergency language detected", actor_id=None
    )
    assert escalation.status.value == "open"
    assert escalation in escalation_service.list_open_escalations(db)

    resolved = escalation_service.resolve_escalation(
        db, escalation_id=escalation.id, decision="approved", reviewer_id=patient_profile.user_id
    )
    assert resolved.status.value == "approved"
    assert resolved.reviewed_by == patient_profile.user_id
    assert escalation_service.list_open_escalations(db) == []


def test_resolving_twice_raises_conflict(db, patient_profile):
    run = workflow_service.create_workflow_run(db, patient_id=patient_profile.id, actor_id=patient_profile.user_id)
    escalation = escalation_service.create_escalation(
        db, workflow_run_id=run.id, reason="Ambiguous request", actor_id=None
    )
    escalation_service.resolve_escalation(
        db, escalation_id=escalation.id, decision="rejected", reviewer_id=patient_profile.user_id
    )
    with pytest.raises(ConflictError):
        escalation_service.resolve_escalation(
            db, escalation_id=escalation.id, decision="approved", reviewer_id=patient_profile.user_id
        )
