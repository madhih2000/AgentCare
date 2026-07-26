import logging

from backend.agents.runtime import run_agent_loop
from backend.agents.state import MAX_CLARIFICATION_ROUNDS, WorkflowState, persist_step
from backend.agents.tools.appointment_tools import (
    book_appointment,
    cancel_appointment,
    list_doctors,
    list_open_slots,
    list_patient_appointment_history,
    reschedule_appointment,
)
from backend.agents.tools.clarification_tools import request_clarification
from backend.agents.tools.escalation_tools import create_escalation
from backend.prompts.appointment_prompt import APPOINTMENT_SYSTEM_PROMPT

logger = logging.getLogger("agentcare.agents.appointment")


def appointment_agent_node(state: WorkflowState) -> dict:
    if not state.get("department_id"):
        logger.info(
            "Workflow %s: Appointment agent skipped (no department routed)", state["workflow_run_id"]
        )
        return {}

    logger.info("Workflow %s: Appointment agent starting", state["workflow_run_id"])
    trace = list(state.get("trace", []))
    user_message = (
        f"Patient ID: {state['patient_id']}\n"
        f"Department: {state.get('department_name')} (id={state['department_id']})\n"
        f"Request: {state['request_text']}\n"
        f"actor_id to use for any booking/reschedule/cancel tool call: {state.get('actor_id')}\n\n"
        "If the patient is asking to book, reschedule, or cancel an appointment, do it "
        "using the tools. If they are not asking about appointments at all, say so "
        "without calling any booking tool."
    )
    result = run_agent_loop(
        system_prompt=APPOINTMENT_SYSTEM_PROMPT,
        tools=[
            list_doctors,
            list_open_slots,
            list_patient_appointment_history,
            book_appointment,
            reschedule_appointment,
            cancel_appointment,
            request_clarification,
        ],
        user_message=user_message,
        agent_name="appointment",
    )
    trace.append({"agent": "appointment", "tool_calls": result["trace"], "output": result["content"]})

    clarification_call = next(
        (call for call in result["trace"] if call["tool"] == "request_clarification"), None
    )
    if clarification_call is not None:
        rounds = state.get("clarification_rounds", 0) + 1

        if rounds > MAX_CLARIFICATION_ROUNDS:
            reason = (
                f"Appointment Agent still couldn't resolve a doctor/slot preference after "
                f"{MAX_CLARIFICATION_ROUNDS} clarifying questions: {state['request_text']!r}"
            )
            tool_result = create_escalation.invoke(
                {
                    "workflow_run_id": state["workflow_run_id"],
                    "reason": reason,
                    "actor_id": state.get("actor_id") or "",
                }
            )
            trace.append(
                {
                    "agent": "appointment",
                    "tool_calls": [{"tool": "create_escalation", "args": {"reason": reason}, "result": tool_result}],
                    "output": f"Escalated to human review: {reason}",
                }
            )
            persist_step(
                state, trace, "appointment",
                status="escalated", escalated=True, escalation_reason=reason,
                needs_clarification=False, clarification_question=None, clarification_rounds=rounds,
            )
            logger.warning(
                "Workflow %s: Appointment agent escalated after %d unresolved clarification rounds",
                state["workflow_run_id"], rounds,
            )
            return {"trace": trace, "escalated": True, "escalation_reason": reason, "needs_clarification": False}

        question = clarification_call["result"].get("question", clarification_call["args"].get("question"))
        persist_step(
            state,
            trace,
            "appointment",
            status="needs_clarification",
            needs_clarification=True,
            clarification_question=question,
            request_text=state["request_text"],
            clarification_rounds=rounds,
        )
        logger.info(
            "Workflow %s: Appointment agent paused for clarification (round %d/%d): %r",
            state["workflow_run_id"], rounds, MAX_CLARIFICATION_ROUNDS, question,
        )
        return {"trace": trace, "needs_clarification": True, "clarification_question": question}

    appointment_id = None
    appointment_start = None
    for call in result["trace"]:
        if call["tool"] == "book_appointment":
            res = call["result"]
            if isinstance(res, dict) and res.get("id"):
                appointment_id = res["id"]
                appointment_start = res.get("slot_start")

    persist_step(
        state, trace, "appointment",
        appointment_id=appointment_id, appointment_start=appointment_start, needs_clarification=False,
    )
    logger.info(
        "Workflow %s: Appointment agent finished (appointment_id=%s)",
        state["workflow_run_id"], appointment_id,
    )
    return {
        "trace": trace,
        "appointment_id": appointment_id,
        "appointment_start": appointment_start,
        "needs_clarification": False,
    }
