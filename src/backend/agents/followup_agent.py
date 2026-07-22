import logging

from backend.agents.runtime import run_agent_loop
from backend.agents.state import WorkflowState, persist_step
from backend.agents.tools.reminder_tools import (
    create_appointment_reminder,
    create_document_followup_reminder,
)
from backend.prompts.followup_prompt import FOLLOWUP_SYSTEM_PROMPT

logger = logging.getLogger("agentcare.agents.followup")


def followup_agent_node(state: WorkflowState) -> dict:
    logger.info("Workflow %s: Follow-up agent starting", state["workflow_run_id"])
    trace = list(state.get("trace", []))

    lines = [f"Patient ID: {state['patient_id']}", f"actor_id: {state.get('actor_id')}"]
    if state.get("appointment_id"):
        lines.append(
            f"Booked appointment_id: {state['appointment_id']} starting at {state.get('appointment_start')}"
        )
    if state.get("missing_documents"):
        lines.append(f"Missing documents: {', '.join(state['missing_documents'])}")
    if len(lines) == 2:
        lines.append("No appointment was booked and no documents are missing; no reminders are needed.")

    result = run_agent_loop(
        system_prompt=FOLLOWUP_SYSTEM_PROMPT,
        tools=[create_appointment_reminder, create_document_followup_reminder],
        user_message="\n".join(lines),
        agent_name="followup",
    )
    trace.append({"agent": "followup", "tool_calls": result["trace"], "output": result["content"]})

    persist_step(state, trace, "followup", status="completed", final_summary=result["content"])
    logger.info("Workflow %s: Follow-up agent finished — workflow completed", state["workflow_run_id"])
    return {"trace": trace, "status": "completed", "final_summary": result["content"]}
