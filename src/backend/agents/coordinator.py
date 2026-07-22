import logging

from backend.agents.runtime import run_agent_loop
from backend.agents.state import WorkflowState, persist_step
from backend.agents.tools.audit_tools import log_agent_decision
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
        tools=[get_patient_profile, log_agent_decision],
        user_message=user_message,
        agent_name="coordinator",
    )
    trace.append({"agent": "coordinator", "tool_calls": result["trace"], "output": result["content"]})
    persist_step(state, trace, "coordinator")
    logger.info("Workflow %s: Coordinator agent finished", state["workflow_run_id"])
    return {"trace": trace}
