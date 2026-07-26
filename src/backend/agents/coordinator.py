import logging

from backend.agents.runtime import run_agent_loop
from backend.agents.state import MAX_CLARIFICATION_ROUNDS, WorkflowState, persist_step
from backend.agents.tools.audit_tools import log_agent_decision
from backend.agents.tools.clarification_tools import request_clarification
from backend.agents.tools.escalation_tools import create_escalation
from backend.agents.tools.patient_tools import get_patient_profile
from backend.prompts.coordinator_prompt import COORDINATOR_SYSTEM_PROMPT

logger = logging.getLogger("agentcare.agents.coordinator")


def coordinator_node(state: WorkflowState) -> dict:
    logger.info("Workflow %s: Coordinator agent starting", state["workflow_run_id"])
    trace = list(state.get("trace", []))

    user_message = (
        f"Patient ID: {state['patient_id']}\n"
        f"Request: {state['request_text']}\n\n"
        "Confirm the patient record exists and summarize which administrative "
        "steps (routing, appointment, documents, follow-up) this request needs."
    )
    result = run_agent_loop(
        system_prompt=COORDINATOR_SYSTEM_PROMPT,
        tools=[get_patient_profile, log_agent_decision, request_clarification],
        user_message=user_message,
        agent_name="coordinator",
    )
    trace.append({"agent": "coordinator", "tool_calls": result["trace"], "output": result["content"]})

    clarification_call = next(
        (call for call in result["trace"] if call["tool"] == "request_clarification"), None
    )
    if clarification_call is not None:
        rounds = state.get("clarification_rounds", 0) + 1

        if rounds > MAX_CLARIFICATION_ROUNDS:
            reason = (
                f"Coordinator still couldn't resolve the request after "
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
                    "agent": "coordinator",
                    "tool_calls": [{"tool": "create_escalation", "args": {"reason": reason}, "result": tool_result}],
                    "output": f"Escalated to human review: {reason}",
                }
            )
            persist_step(
                state, trace, "coordinator",
                status="escalated", escalated=True, escalation_reason=reason,
                needs_clarification=False, clarification_question=None, clarification_rounds=rounds,
            )
            logger.warning(
                "Workflow %s: Coordinator escalated after %d unresolved clarification rounds",
                state["workflow_run_id"], rounds,
            )
            return {"trace": trace, "escalated": True, "escalation_reason": reason, "needs_clarification": False}

        question = clarification_call["result"].get("question", clarification_call["args"].get("question"))
        persist_step(
            state,
            trace,
            "coordinator",
            status="needs_clarification",
            needs_clarification=True,
            clarification_question=question,
            request_text=state["request_text"],
            clarification_rounds=rounds,
        )
        logger.info(
            "Workflow %s: Coordinator agent paused for clarification (round %d/%d): %r",
            state["workflow_run_id"], rounds, MAX_CLARIFICATION_ROUNDS, question,
        )
        return {"trace": trace, "needs_clarification": True, "clarification_question": question}

    persist_step(state, trace, "coordinator", needs_clarification=False, clarification_question=None)
    logger.info("Workflow %s: Coordinator agent finished", state["workflow_run_id"])
    return {"trace": trace, "needs_clarification": False}
