"""Tests the Appointment Agent's ability to pause on a doctor-preference
question (same request_clarification + round-cap mechanism as the
Coordinator) instead of picking a doctor arbitrarily."""

import backend.agents.appointment_agent as appointment_agent_module
import backend.agents.state as state_module
import backend.agents.tools.escalation_tools as escalation_tools_module
from backend.services import escalation_service, workflow_service


def _patch_session_local(monkeypatch, session_factory):
    monkeypatch.setattr(state_module, "SessionLocal", session_factory)
    monkeypatch.setattr(escalation_tools_module, "SessionLocal", session_factory)


def _asks_for_doctor_preference(**kwargs):
    return {
        "content": "Dr. Verma or Dr. Mehta — do you have a preference?",
        "trace": [
            {
                "tool": "request_clarification",
                "args": {"question": "Dr. Verma or Dr. Mehta — do you have a preference?"},
                "result": {
                    "clarification_requested": True,
                    "question": "Dr. Verma or Dr. Mehta — do you have a preference?",
                },
            }
        ],
    }


def _make_state(run_id, patient_profile, department, clarification_rounds):
    return {
        "workflow_run_id": run_id,
        "patient_id": patient_profile.id,
        "actor_id": patient_profile.user_id,
        "request_text": "I need a cardiology appointment",
        "department_id": department.id,
        "department_name": department.name,
        "trace": [],
        "clarification_rounds": clarification_rounds,
    }


def test_appointment_agent_skips_when_no_department_routed(patient_profile):
    state = {
        "workflow_run_id": "does-not-matter",
        "patient_id": patient_profile.id,
        "trace": [],
    }
    result = appointment_agent_module.appointment_agent_node(state)
    assert result == {}


def test_appointment_agent_pauses_for_doctor_preference(
    db, session_factory, monkeypatch, patient_profile, seeded_clinical
):
    _patch_session_local(monkeypatch, session_factory)
    monkeypatch.setattr(appointment_agent_module, "run_agent_loop", _asks_for_doctor_preference)
    run = workflow_service.create_workflow_run(db, patient_id=patient_profile.id, actor_id=patient_profile.user_id)

    state = _make_state(run.id, patient_profile, seeded_clinical["department"], clarification_rounds=0)
    result = appointment_agent_module.appointment_agent_node(state)

    assert result["needs_clarification"] is True
    assert "preference" in result["clarification_question"]
    assert escalation_service.list_open_escalations(db) == []


def test_appointment_agent_escalates_after_max_rounds(
    db, session_factory, monkeypatch, patient_profile, seeded_clinical
):
    _patch_session_local(monkeypatch, session_factory)
    monkeypatch.setattr(appointment_agent_module, "run_agent_loop", _asks_for_doctor_preference)
    run = workflow_service.create_workflow_run(db, patient_id=patient_profile.id, actor_id=patient_profile.user_id)

    state = _make_state(
        run.id, patient_profile, seeded_clinical["department"],
        clarification_rounds=appointment_agent_module.MAX_CLARIFICATION_ROUNDS,
    )
    result = appointment_agent_module.appointment_agent_node(state)

    assert result["escalated"] is True
    assert result["needs_clarification"] is False
    open_escalations = escalation_service.list_open_escalations(db)
    assert len(open_escalations) == 1
    assert open_escalations[0].workflow_run_id == run.id
