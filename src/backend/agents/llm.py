import logging
from functools import lru_cache

from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool
from langchain_groq import ChatGroq

from backend.config import get_settings

logger = logging.getLogger("agentcare.agents.llm")


@lru_cache
def _build_groq(model: str, temperature: float) -> ChatGroq:
    settings = get_settings()
    return ChatGroq(
        api_key=settings.groq_api_key,
        model=model,
        temperature=temperature,
        # The SDK's own retry is disabled here — backend.utils.retry wraps the
        # call site with jittered exponential backoff instead, so there is a
        # single, observable retry policy instead of two stacked ones.
        max_retries=0,
    )


def get_llm_with_fallbacks(tools: list[BaseTool], temperature: float = 0.0) -> Runnable:
    """Primary model bound with `tools`, chained with backup models (also
    tools-bound) via LangChain's `.with_fallbacks()`. If the primary model
    errors (rate limit, outage, decommissioned model id), LangChain
    immediately retries the same request against the next model in the
    chain before this ever surfaces as a failure to the caller."""
    settings = get_settings()
    model_names = settings.groq_model_chain

    def _bind(model_name: str):
        llm = _build_groq(model_name, temperature)
        return llm.bind_tools(tools) if tools else llm

    primary, *fallbacks = (_bind(name) for name in model_names)
    if not fallbacks:
        return primary

    logger.debug("LLM fallback chain: %s", model_names)
    return primary.with_fallbacks(fallbacks)
