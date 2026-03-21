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


def check_valid_chat(state: AgentState) -> str:
    decision = "generate" if state.get("is_valid_chat", False) else "end"
    logger.info(
        "agent_v2_route_vision",
        decision=decision,
        is_valid_chat=state.get("is_valid_chat", False),
        bouncer_reason=state.get("bouncer_reason", ""),
    )
    return decision


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
            "agent_v2_route_auditor",
            decision="end",
            revision_count=revision_count,
        )
        return "end"

    # Safety valve: max 1 rewrite (2 total generator calls).
    # revision_count is incremented by generator_node, so after the first pass
    # it's 1, and after a rewrite it would be 2.
    if revision_count >= 2:
        logger.info(
            "agent_v2_route_auditor",
            decision="end",
            reason="max_rewrites_reached",
            revision_count=revision_count,
        )
        return "end"

    logger.info(
        "agent_v2_route_auditor",
        decision="rewrite",
        revision_count=revision_count,
        auditor_feedback_preview=str(state.get("auditor_feedback", ""))[:100],
    )
    return "rewrite"


# --- Build the graph ---
workflow = StateGraph(AgentState)

workflow.add_node("vision", vision_node)
workflow.add_node("generator", generator_node)
workflow.add_node("auditor", auditor_node)

workflow.set_entry_point("vision")

# vision → (valid?) → generator or END
workflow.add_conditional_edges(
    "vision",
    check_valid_chat,
    {
        "generate": "generator",
        "end": END,
    },
)

# generator → auditor (always)
workflow.add_edge("generator", "auditor")

# auditor → (pass?) → END or back to generator
workflow.add_conditional_edges(
    "auditor",
    check_audit,
    {
        "end": END,
        "rewrite": "generator",
    },
)

rizz_agent_v2 = workflow.compile()
