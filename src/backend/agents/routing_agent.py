from backend.agents.runtime import run_agent_loop
from backend.agents.state import WorkflowState, persist_step
from backend.agents.tools.department_tools import classify_department, list_departments
from backend.prompts.routing_prompt import ROUTING_SYSTEM_PROMPT


def routing_agent_node(state: WorkflowState) -> dict:
    trace = list(state.get("trace", []))

    user_message = (
        f"Patient request: {state['request_text']}\n\n"
        "Determine the correct department for this request using the tools available."
    )
    result = run_agent_loop(
        system_prompt=ROUTING_SYSTEM_PROMPT,
        tools=[list_departments, classify_department],
        user_message=user_message,
    )
    trace.append({"agent": "routing", "tool_calls": result["trace"], "output": result["content"]})

    department_id = None
    department_name = None
    for call in result["trace"]:
        if call["tool"] == "classify_department":
            res = call["result"]
            if isinstance(res, dict) and res.get("id"):
                department_id, department_name = res["id"], res["name"]

    persist_step(state, trace, "routing", department_id=department_id, department_name=department_name)
    return {"trace": trace, "department_id": department_id, "department_name": department_name}
