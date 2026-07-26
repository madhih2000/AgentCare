"""Tests the Coordinator's clarification-round cap: request_clarification can
pause the workflow repeatedly, but after MAX_CLARIFICATION_ROUNDS unresolved
attempts it must escalate to a human instead of asking forever."""

import backend.agents.coordinator as coordinator_module
import backend.agents.state as state_module
import backend.agents.tools.escalation_tools as escalation_tools_module
from backend.services import escalation_service, workflow_service


def _patch_session_local(monkeypatch, session_factory):
    monkeypatch.setattr(state_module, "SessionLocal", session_factory)
    monkeypatch.setattr(escalation_tools_module, "SessionLocal", session_factory)


def _always_asks_for_clarification(**kwargs):
    return {
        "content": "Could you clarify what you need?",
        "trace": [
            {
                "tool": "request_clarification",
                "args": {"question": "Which department is this about?"},
                "result": {"clarification_requested": True, "question": "Which department is this about?"},
            }
        ],
    }


def _make_state(run_id, patient_profile, clarification_rounds):
    return {
        "workflow_run_id": run_id,
        "patient_id": patient_profile.id,
        "actor_id": patient_profile.user_id,
        "request_text": "I need to see someone",
        "trace": [],
        "clarification_rounds": clarification_rounds,
    }


def test_clarification_pauses_under_the_round_cap(db, session_factory, monkeypatch, patient_profile):
    _patch_session_local(monkeypatch, session_factory)
    monkeypatch.setattr(coordinator_module, "run_agent_loop", _always_asks_for_clarification)
    run = workflow_service.create_workflow_run(db, patient_id=patient_profile.id, actor_id=patient_profile.user_id)

    result = coordinator_module.coordinator_node(_make_state(run.id, patient_profile, clarification_rounds=0))

    assert result["needs_clarification"] is True
    assert result.get("escalated") is not True
    assert escalation_service.list_open_escalations(db) == []


def test_clarification_escalates_after_max_rounds(db, session_factory, monkeypatch, patient_profile):
    _patch_session_local(monkeypatch, session_factory)
    monkeypatch.setattr(coordinator_module, "run_agent_loop", _always_asks_for_clarification)
    run = workflow_service.create_workflow_run(db, patient_id=patient_profile.id, actor_id=patient_profile.user_id)

    # Already at the cap going in — this call would be one clarification
    # round too many.
    state = _make_state(run.id, patient_profile, clarification_rounds=coordinator_module.MAX_CLARIFICATION_ROUNDS)
    result = coordinator_module.coordinator_node(state)

    assert result["escalated"] is True
    assert result["needs_clarification"] is False
    open_escalations = escalation_service.list_open_escalations(db)
    assert len(open_escalations) == 1
    assert open_escalations[0].workflow_run_id == run.id
