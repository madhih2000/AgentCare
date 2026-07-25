import logging
from pathlib import Path

from langgraph.graph import END, StateGraph

from backend.agents.appointment_agent import appointment_agent_node
from backend.agents.coordinator import coordinator_node
from backend.agents.document_agent import document_agent_node
from backend.agents.followup_agent import followup_agent_node
from backend.agents.routing_agent import routing_agent_node
from backend.agents.safety_agent import safety_agent_node, safety_precheck_node
from backend.agents.state import WorkflowState
from backend.config import get_settings

logger = logging.getLogger("agentcare.graph")

_compiled_graph = None


def _route_after_precheck(state: WorkflowState) -> str:
    return "escalated" if state.get("escalated") else "coordinator"


def _route_after_coordinator(state: WorkflowState) -> str:
    return "clarify" if state.get("needs_clarification") else "safety"


def _route_after_safety(state: WorkflowState) -> str:
    return "escalated" if state.get("escalated") else "routing"


def _build_checkpointer():
    settings = get_settings()
    if settings.langgraph_checkpointer == "sqlite":
        try:
            import sqlite3

            from langgraph.checkpoint.sqlite import SqliteSaver

            db_path = Path(settings.langgraph_checkpoint_db)
            db_path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(str(db_path), check_same_thread=False)
            return SqliteSaver(conn)
        except OSError:
            # Read-only filesystem (e.g. Vercel's serverless functions
            # outside /tmp) or any other local-disk problem. The checkpointer
            # isn't the source of truth for workflow progress — WorkflowRun
            # .state_json is (see agents/state.py::persist_step) — so falling
            # back to an in-memory checkpointer only costs checkpoint replay
            # across restarts, not correctness. Better than crashing every
            # workflow run over a misconfigured/unwritable path.
            logger.warning(
                "LANGGRAPH_CHECKPOINTER=sqlite but %s isn't writable here; "
                "falling back to MemorySaver for this process.",
                settings.langgraph_checkpoint_db,
            )

    from langgraph.checkpoint.memory import MemorySaver

    return MemorySaver()


def build_graph():
    graph = StateGraph(WorkflowState)
    graph.add_node("safety_precheck", safety_precheck_node)
    graph.add_node("coordinator", coordinator_node)
    graph.add_node("safety", safety_agent_node)
    graph.add_node("routing", routing_agent_node)
    graph.add_node("appointment", appointment_agent_node)
    graph.add_node("document", document_agent_node)
    graph.add_node("followup", followup_agent_node)

    graph.set_entry_point("safety_precheck")
    graph.add_conditional_edges(
        "safety_precheck", _route_after_precheck, {"escalated": END, "coordinator": "coordinator"}
    )
    graph.add_conditional_edges(
        "coordinator", _route_after_coordinator, {"clarify": END, "safety": "safety"}
    )
    graph.add_conditional_edges("safety", _route_after_safety, {"escalated": END, "routing": "routing"})
    graph.add_edge("routing", "appointment")
    graph.add_edge("appointment", "document")
    graph.add_edge("document", "followup")
    graph.add_edge("followup", END)

    return graph.compile(checkpointer=_build_checkpointer())


def get_compiled_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    return _compiled_graph


def run_workflow(
    *,
    workflow_run_id: str,
    patient_id: str,
    actor_id: str,
    request_text: str,
    initial_trace: list[dict] | None = None,
) -> WorkflowState:
    """Runs the graph from its entry point (the deterministic safety precheck).
    `initial_trace` carries forward the trace already shown to the user when
    this call resumes a workflow that was previously paused by the
    coordinator's request_clarification tool — without it, resuming would
    wipe the pipeline history the patient already saw."""
    graph = get_compiled_graph()
    initial_state: WorkflowState = {
        "workflow_run_id": workflow_run_id,
        "patient_id": patient_id,
        "actor_id": actor_id,
        "request_text": request_text,
        "trace": initial_trace or [],
        "escalated": False,
        "missing_documents": [],
        "status": "in_progress",
        "needs_clarification": False,
        "clarification_question": None,
    }
    config = {"configurable": {"thread_id": workflow_run_id}}
    logger.info(
        "Workflow %s: === starting for patient %s: %r ===", workflow_run_id, patient_id, request_text
    )
    try:
        final_state = graph.invoke(initial_state, config=config)
        logger.info(
            "Workflow %s: === finished with status=%s ===", workflow_run_id, final_state.get("status")
        )
        return final_state
    except Exception as exc:
        logger.error("Workflow %s: === failed: %s ===", workflow_run_id, exc)
        from backend.agents.state import persist_step

        persist_step(initial_state, [{"agent": "graph", "tool_calls": [], "output": str(exc)}], "failed", status="failed")
        raise
