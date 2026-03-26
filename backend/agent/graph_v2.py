"""
V2 agent graph — 3-node architecture with evaluator-rewriter loop.

Flow:
  vision_node → (valid?) → generator_node → auditor_node → (pass? → END)
                                  ↑                            |
                                  └── (fail, rewrite ≤ 1) ────┘
               ↘ END (invalid image)

The auditor evaluates substantive reply quality (context fit, archetype match,
direction compliance, cringe, diversity, dialect). Style/punctuation fixes are
handled deterministically by _post_process_replies() in the endpoint layer.
"""

import structlog
from langgraph.graph import StateGraph, END

from agent.state import AgentState
from agent.nodes_v2 import vision_node, generator_node, auditor_node

logger = structlog.get_logger(__name__)


def _state_snapshot(state: AgentState) -> dict:
    analysis = state.get("analysis")
    has_analysis = analysis is not None
    visual_transcript_count = 0
    if isinstance(analysis, dict):
        visual_transcript_count = len(analysis.get("visual_transcript") or [])
    elif analysis is not None and hasattr(analysis, "visual_transcript"):
        visual_transcript_count = len(getattr(analysis, "visual_transcript") or [])

    drafts = state.get("drafts")
    reply_count = 0
    if isinstance(drafts, dict):
        reply_count = len(drafts.get("replies") or [])
    elif drafts is not None and hasattr(drafts, "replies"):
        reply_count = len(getattr(drafts, "replies") or [])

    return {
        "direction": state.get("direction", ""),
        "conversation_id": state.get("conversation_id", "") or "",
        "revision_count": state.get("revision_count", 0),
        "is_valid_chat": bool(state.get("is_valid_chat", False)),
        "has_analysis": has_analysis,
        "visual_transcript_count": visual_transcript_count,
        "has_drafts": drafts is not None,
        "reply_count": reply_count,
        "has_auditor_feedback": bool(state.get("auditor_feedback", "")),
        "core_lore_chars": len(state.get("core_lore", "") or ""),
        "past_memories_chars": len(state.get("past_memories", "") or ""),
    }


def check_valid_chat(state: AgentState) -> str:
    valid = bool(state.get("is_valid_chat", False))
    route = "generate" if valid else "end"
    logger.info(
        "llm_lifecycle",
        stage="graph_route_after_vision",
        trace_id=state.get("trace_id", ""),
        route=route,
        user_id=state.get("user_id", ""),
        conversation_id=state.get("conversation_id", "") or "",
        direction=state.get("direction", ""),
        revision_count=state.get("revision_count", 0),
        state_snapshot=_state_snapshot(state),
        bouncer_reason=(state.get("bouncer_reason") or "")[:200] if not valid else "",
    )
    return route


def check_audit(state: AgentState) -> str:
    """
    Route based on auditor verdict:
    - "end": replies are good enough → ship them
    - "rewrite": replies have issues → send back to generator with feedback
    """
    is_cringe = state.get("is_cringe", False)
    revision_count = state.get("revision_count", 0)

    if not is_cringe:
        logger.info(
            "llm_lifecycle",
            stage="graph_route_after_auditor",
            trace_id=state.get("trace_id", ""),
            route="end",
            user_id=state.get("user_id", ""),
            conversation_id=state.get("conversation_id", "") or "",
            direction=state.get("direction", ""),
            revision_count=revision_count,
            auditor_approved=True,
            state_snapshot=_state_snapshot(state),
        )
        return "end"

    if revision_count >= 2:
        logger.info(
            "llm_lifecycle",
            stage="graph_route_after_auditor",
            trace_id=state.get("trace_id", ""),
            route="end",
            user_id=state.get("user_id", ""),
            conversation_id=state.get("conversation_id", "") or "",
            direction=state.get("direction", ""),
            revision_count=revision_count,
            auditor_approved=True,
            note="max_rewrites_cap",
            state_snapshot=_state_snapshot(state),
        )
        return "end"

    logger.info(
        "llm_lifecycle",
        stage="graph_route_after_auditor",
        trace_id=state.get("trace_id", ""),
        route="rewrite",
        user_id=state.get("user_id", ""),
        conversation_id=state.get("conversation_id", "") or "",
        direction=state.get("direction", ""),
        revision_count=revision_count,
        auditor_approved=False,
        state_snapshot=_state_snapshot(state),
    )
    return "rewrite"


workflow = StateGraph(AgentState)

workflow.add_node("vision", vision_node)
workflow.add_node("generator", generator_node)
workflow.add_node("auditor", auditor_node)

workflow.set_entry_point("vision")

workflow.add_conditional_edges(
    "vision",
    check_valid_chat,
    {
        "generate": "generator",
        "end": END,
    },
)

workflow.add_edge("generator", "auditor")

workflow.add_conditional_edges(
    "auditor",
    check_audit,
    {
        "end": END,
        "rewrite": "generator",
    },
)

rizz_agent_v2 = workflow.compile()
