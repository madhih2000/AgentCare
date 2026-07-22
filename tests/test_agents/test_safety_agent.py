"""Tests the Safety & Escalation Agent's deterministic, code-enforced
boundary. The emergency/clinical-overreach path never calls the LLM, so
these run fully offline. `backend.agents.state` and
`backend.agents.tools.escalation_tools` each hold their own `SessionLocal`
reference bound at import time, so both are monkeypatched to the shared
in-memory test engine for the duration of the test."""

import backend.agents.safety_agent as safety_agent_module
import backend.agents.state as state_module
import backend.agents.tools.escalation_tools as escalation_tools_module
from backend.services import escalation_service, workflow_service


def _patch_session_local(monkeypatch, session_factory):
    monkeypatch.setattr(state_module, "SessionLocal", session_factory)
    monkeypatch.setattr(escalation_tools_module, "SessionLocal", session_factory)


def _make_workflow_run(db, patient_profile):
    return workflow_service.create_workflow_run(
        db, patient_id=patient_profile.id, actor_id=patient_profile.user_id
    )


def test_emergency_request_is_escalated_without_calling_llm(
    db, session_factory, monkeypatch, patient_profile
):
    _patch_session_local(monkeypatch, session_factory)
    run = _make_workflow_run(db, patient_profile)

    state = {
        "workflow_run_id": run.id,
        "patient_id": patient_profile.id,
        "actor_id": patient_profile.user_id,
        "request_text": "I have severe chest pain and can't breathe, please help",
        "trace": [],
    }
    result = safety_agent_module.safety_agent_node(state)

    assert result["escalated"] is True
    assert result["status"] == "escalated"
    open_escalations = escalation_service.list_open_escalations(db)
    assert len(open_escalations) == 1
    assert open_escalations[0].workflow_run_id == run.id


def test_clinical_overreach_request_is_escalated(db, session_factory, monkeypatch, patient_profile):
    _patch_session_local(monkeypatch, session_factory)
    run = _make_workflow_run(db, patient_profile)

    state = {
        "workflow_run_id": run.id,
        "patient_id": patient_profile.id,
        "actor_id": patient_profile.user_id,
        "request_text": "Can you diagnose what disease I have and prescribe medicine?",
        "trace": [],
    }
    result = safety_agent_module.safety_agent_node(state)

    assert result["escalated"] is True
    assert "diagnosis" in result["escalation_reason"].lower() or "prescription" in result["escalation_reason"].lower()


def test_benign_request_does_not_escalate(db, session_factory, monkeypatch, patient_profile):
    _patch_session_local(monkeypatch, session_factory)
    run = _make_workflow_run(db, patient_profile)

    # The benign path falls through to the secondary LLM check — stub it out
    # so this test stays offline and deterministic.
    monkeypatch.setattr(
        safety_agent_module,
        "run_agent_loop",
        lambda **kwargs: {"content": "Safe to proceed with normal handling.", "trace": []},
    )

    state = {
        "workflow_run_id": run.id,
        "patient_id": patient_profile.id,
        "actor_id": patient_profile.user_id,
        "request_text": "I'd like to book a cardiology appointment for next week",
        "trace": [],
    }
    result = safety_agent_module.safety_agent_node(state)

    assert result["escalated"] is False
    assert result["status"] == "in_progress"
    assert escalation_service.list_open_escalations(db) == []
