"""
LangGraph graph definitions for the AIVOA complaint intake workflow.

Two compiled graphs:
1. complaint_graph  — for new complaint text/document analysis
2. followup_graph   — for conversational corrections

Architecture:
- input_type is set by FastAPI BEFORE the graph runs (correction #2)
- document parsing completes BEFORE the graph runs (correction #3)
- conditional edges drive follow-up routing
"""
from langgraph.graph import StateGraph, START, END

from app.ai.state import ComplaintState
from app.ai.nodes import (
    extract_complaint,
    validate_fields,
    assess_risk,
    build_copilot_response,
    understand_followup,
    merge_state,
    reassess_if_needed,
    build_correction_response,
)


# ─────────────────────────────────────────────
# Graph 1: Complaint analysis (text or document)
# ─────────────────────────────────────────────
# Flow: extract → validate → assess_risk → build_copilot_response

def _should_continue_after_extraction(state: ComplaintState) -> str:
    """Route to error response if extraction failed, otherwise continue."""
    if state.get("workflow_status") in ("extraction_failed", "error"):
        return "build_copilot_response"
    return "validate_fields"


def build_complaint_graph() -> StateGraph:
    graph = StateGraph(ComplaintState)

    graph.add_node("extract_complaint", extract_complaint)
    graph.add_node("validate_fields", validate_fields)
    graph.add_node("assess_risk", assess_risk)
    graph.add_node("build_copilot_response", build_copilot_response)

    graph.add_edge(START, "extract_complaint")
    graph.add_conditional_edges(
        "extract_complaint",
        _should_continue_after_extraction,
        {
            "validate_fields": "validate_fields",
            "build_copilot_response": "build_copilot_response",
        },
    )
    graph.add_edge("validate_fields", "assess_risk")
    graph.add_edge("assess_risk", "build_copilot_response")
    graph.add_edge("build_copilot_response", END)

    return graph


# ─────────────────────────────────────────────
# Graph 2: Follow-up / conversational correction
# ─────────────────────────────────────────────
# Flow: understand_followup → merge_state → reassess_if_needed → build_correction_response

def _route_after_followup_parse(state: ComplaintState) -> str:
    """Route to clarification response if parsing failed or no updates found."""
    status = state.get("workflow_status", "")
    if status in ("followup_parse_failed", "followup_no_message"):
        return "build_correction_response"
    return "merge_state"


def build_followup_graph() -> StateGraph:
    graph = StateGraph(ComplaintState)

    graph.add_node("understand_followup", understand_followup)
    graph.add_node("merge_state", merge_state)
    graph.add_node("reassess_if_needed", reassess_if_needed)
    graph.add_node("build_correction_response", build_correction_response)

    graph.add_edge(START, "understand_followup")
    graph.add_conditional_edges(
        "understand_followup",
        _route_after_followup_parse,
        {
            "merge_state": "merge_state",
            "build_correction_response": "build_correction_response",
        },
    )
    graph.add_edge("merge_state", "reassess_if_needed")
    graph.add_edge("reassess_if_needed", "build_correction_response")
    graph.add_edge("build_correction_response", END)

    return graph


# Compile graphs at module load — these are reused across requests
complaint_graph = build_complaint_graph().compile()
followup_graph = build_followup_graph().compile()
