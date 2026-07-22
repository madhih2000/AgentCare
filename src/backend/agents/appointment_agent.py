from backend.agents.runtime import run_agent_loop
from backend.agents.state import WorkflowState, persist_step
from backend.agents.tools.appointment_tools import (
    book_appointment,
    cancel_appointment,
    list_doctors,
    list_open_slots,
    reschedule_appointment,
)
from backend.prompts.appointment_prompt import APPOINTMENT_SYSTEM_PROMPT


def appointment_agent_node(state: WorkflowState) -> dict:
    if not state.get("department_id"):
        return {}

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
        tools=[list_doctors, list_open_slots, book_appointment, reschedule_appointment, cancel_appointment],
        user_message=user_message,
    )
    trace.append({"agent": "appointment", "tool_calls": result["trace"], "output": result["content"]})

    appointment_id = None
    appointment_start = None
    for call in result["trace"]:
        if call["tool"] == "book_appointment":
            res = call["result"]
            if isinstance(res, dict) and res.get("id"):
                appointment_id = res["id"]
                appointment_start = res.get("slot_start")

    persist_step(
        state, trace, "appointment", appointment_id=appointment_id, appointment_start=appointment_start
    )
    return {"trace": trace, "appointment_id": appointment_id, "appointment_start": appointment_start}
