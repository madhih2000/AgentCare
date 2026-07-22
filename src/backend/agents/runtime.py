import json
import logging

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool

from backend.agents.llm import get_llm_with_fallbacks
from backend.utils.retry import retry

logger = logging.getLogger("agentcare.agents")


def _short(value, limit: int = 200) -> str:
    text = json.dumps(value, default=str)
    return text if len(text) <= limit else text[:limit] + "…"


@retry(times=4, base_delay=1.0, max_delay=20.0)
def _invoke_llm(llm_with_tools, messages):
    return llm_with_tools.invoke(messages)


def run_agent_loop(
    *,
    system_prompt: str,
    tools: list[BaseTool],
    user_message: str,
    max_iterations: int = 5,
    agent_name: str = "agent",
) -> dict:
    """Runs a bounded tool-calling loop for one agent: the LLM sees the system
    prompt + user message, may call any of `tools` (each a real service-backed
    LangChain tool), sees the tool results, and repeats until it returns a
    final text answer or the iteration budget runs out.

    Returns {"content": final text, "trace": [{"tool", "args", "result"}]}."""
    llm_with_tools = get_llm_with_fallbacks(tools)
    tools_by_name = {t.name: t for t in tools}

    logger.info("[%s] LLM turn starting (tools=%s)", agent_name, list(tools_by_name))

    messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_message)]
    trace: list[dict] = []

    for turn in range(1, max_iterations + 1):
        try:
            response = _invoke_llm(llm_with_tools, messages)
        except Exception as exc:
            logger.error("[%s] LLM call failed after retries: %s", agent_name, exc)
            return {"content": f"Agent step failed after retries: {exc}", "trace": trace, "failed": True}

        messages.append(response)
        tool_calls = getattr(response, "tool_calls", None) or []
        if not tool_calls:
            logger.info("[%s] finished after %d LLM turn(s): %s", agent_name, turn, _short(response.content))
            return {"content": response.content, "trace": trace}

        for call in tool_calls:
            logger.info("[%s] tool call -> %s(%s)", agent_name, call["name"], _short(call["args"]))
            tool_fn = tools_by_name.get(call["name"])
            if tool_fn is None:
                logger.warning("[%s] unknown tool requested: %s", agent_name, call["name"])
                result = {"error": f"unknown tool {call['name']}"}
            else:
                try:
                    result = tool_fn.invoke(call["args"])
                    logger.info("[%s] tool result <- %s: %s", agent_name, call["name"], _short(result))
                except Exception as exc:
                    logger.error("[%s] tool %s failed: %s", agent_name, call["name"], exc)
                    result = {"error": str(exc)}
            trace.append({"tool": call["name"], "args": call["args"], "result": result})
            messages.append(
                ToolMessage(content=json.dumps(result, default=str), tool_call_id=call["id"])
            )

    logger.warning("[%s] reached max_iterations=%d without a final answer", agent_name, max_iterations)
    last_text = messages[-1].content if hasattr(messages[-1], "content") else ""
    return {"content": last_text or "Reached step limit without a final answer.", "trace": trace}
