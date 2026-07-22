from backend.agents.runtime import run_agent_loop
from backend.agents.state import WorkflowState, persist_step
from backend.agents.tools.document_tools import list_patient_documents, missing_documents
from backend.prompts.document_prompt import DOCUMENT_SYSTEM_PROMPT


def document_agent_node(state: WorkflowState) -> dict:
    trace = list(state.get("trace", []))

    user_message = (
        f"Patient ID: {state['patient_id']}\n"
        f"Department: {state.get('department_name') or 'unknown'}\n"
        f"Request: {state['request_text']}\n\n"
        "Report currently submitted documents and list anything still missing "
        "for this department."
    )
    result = run_agent_loop(
        system_prompt=DOCUMENT_SYSTEM_PROMPT,
        tools=[list_patient_documents, missing_documents],
        user_message=user_message,
    )
    trace.append({"agent": "document", "tool_calls": result["trace"], "output": result["content"]})

    missing: list[str] = []
    for call in result["trace"]:
        if call["tool"] == "missing_documents" and isinstance(call["result"], list):
            missing = call["result"]

    persist_step(state, trace, "document", missing_documents=missing)
    return {"trace": trace, "missing_documents": missing}
