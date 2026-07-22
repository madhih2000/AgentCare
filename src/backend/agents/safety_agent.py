import logging

from backend.agents.runtime import run_agent_loop
from backend.agents.state import WorkflowState, persist_step
from backend.agents.tools.escalation_tools import create_escalation
from backend.prompts.safety_prompt import SAFETY_SYSTEM_PROMPT
from backend.utils.validators import is_clinical_overreach_request, is_emergency_request

logger = logging.getLogger("agentcare.agents.safety")


def safety_agent_node(state: WorkflowState) -> dict:
    logger.info("Workflow %s: Safety & Escalation agent starting", state["workflow_run_id"])
    trace = list(state.get("trace", []))
    request_text = state["request_text"]

    # Deterministic, code-enforced boundary — cannot be talked out of by the
    # LLM. Runs before any LLM call so the safety rule holds even if the LLM
    # is unavailable or misbehaves.
    if is_emergency_request(request_text):
        reason = "Emergency language detected in request; requires immediate human attention."
    elif is_clinical_overreach_request(request_text):
        reason = "Request asks for diagnosis, prescription, or dosage guidance, which this system cannot provide."
    else:
        reason = None

    if reason:
        tool_result = create_escalation.invoke(
            {
                "workflow_run_id": state["workflow_run_id"],
                "reason": reason,
                "actor_id": state.get("actor_id") or "",
            }
        )
        trace.append(
            {
                "agent": "safety",
                "tool_calls": [{"tool": "create_escalation", "args": {"reason": reason}, "result": tool_result}],
                "output": f"Escalated to human review: {reason}",
            }
        )
        persist_step(state, trace, "safety", status="escalated", escalated=True, escalation_reason=reason)
        logger.warning(
            "Workflow %s: Safety agent ESCALATED (deterministic rule): %s", state["workflow_run_id"], reason
        )
        return {"trace": trace, "escalated": True, "escalation_reason": reason, "status": "escalated"}

    # Secondary LLM-judgement layer for ambiguous cases the keyword rules miss.
    user_message = (
        f"Patient request: {request_text}\n\n"
        "Decide whether this needs human escalation under your rules. If not, "
        "simply state that it is safe to proceed with normal administrative handling."
    )
    result = run_agent_loop(
        system_prompt=SAFETY_SYSTEM_PROMPT,
        tools=[create_escalation],
        user_message=user_message,
        agent_name="safety",
    )
    escalated = any(call["tool"] == "create_escalation" for call in result["trace"])
    trace.append({"agent": "safety", "tool_calls": result["trace"], "output": result["content"]})

    status = "escalated" if escalated else None
    persist_step(
        state, trace, "safety", status=status,
        escalated=escalated, escalation_reason=result["content"] if escalated else None,
    )
    logger.info(
        "Workflow %s: Safety agent finished (escalated=%s)", state["workflow_run_id"], escalated
    )
    return {
        "trace": trace,
        "escalated": escalated,
        "escalation_reason": result["content"] if escalated else None,
        "status": "escalated" if escalated else "in_progress",
    }
