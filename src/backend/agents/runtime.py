import json
import logging

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool

from backend.agents.llm import get_llm_with_fallbacks
from backend.utils.retry import retry

logger = logging.getLogger("agentcare.agents")


@retry(times=4, base_delay=1.0, max_delay=20.0)
def _invoke_llm(llm_with_tools, messages):
    return llm_with_tools.invoke(messages)


def run_agent_loop(
    *, system_prompt: str, tools: list[BaseTool], user_message: str, max_iterations: int = 5
) -> dict:
    """Runs a bounded tool-calling loop for one agent: the LLM sees the system
    prompt + user message, may call any of `tools` (each a real service-backed
    LangChain tool), sees the tool results, and repeats until it returns a
    final text answer or the iteration budget runs out.

    Returns {"content": final text, "trace": [{"tool", "args", "result"}]}."""
    llm_with_tools = get_llm_with_fallbacks(tools)
    tools_by_name = {t.name: t for t in tools}

    messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_message)]
    trace: list[dict] = []

    for _ in range(max_iterations):
        try:
            response = _invoke_llm(llm_with_tools, messages)
        except Exception as exc:
            logger.error("LLM call failed after retries: %s", exc)
            return {"content": f"Agent step failed after retries: {exc}", "trace": trace, "failed": True}

        messages.append(response)
        tool_calls = getattr(response, "tool_calls", None) or []
        if not tool_calls:
            return {"content": response.content, "trace": trace}

        for call in tool_calls:
            tool_fn = tools_by_name.get(call["name"])
            if tool_fn is None:
                result = {"error": f"unknown tool {call['name']}"}
            else:
                try:
                    result = tool_fn.invoke(call["args"])
                except Exception as exc:
                    logger.error("Tool %s failed: %s", call["name"], exc)
                    result = {"error": str(exc)}
            trace.append({"tool": call["name"], "args": call["args"], "result": result})
            messages.append(
                ToolMessage(content=json.dumps(result, default=str), tool_call_id=call["id"])
            )

    last_text = messages[-1].content if hasattr(messages[-1], "content") else ""
    return {"content": last_text or "Reached step limit without a final answer.", "trace": trace}
