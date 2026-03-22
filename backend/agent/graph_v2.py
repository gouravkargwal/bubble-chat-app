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
    valid = bool(state.get("is_valid_chat", False))
    route = "generate" if valid else "end"
    logger.info(
        "llm_lifecycle",
        stage="graph_route_after_vision",
        route=route,
        user_id=state.get("user_id", ""),
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
            route="end",
            user_id=state.get("user_id", ""),
            revision_count=revision_count,
            auditor_approved=True,
        )
        return "end"

    if revision_count >= 2:
        logger.info(
            "llm_lifecycle",
            stage="graph_route_after_auditor",
            route="end",
            user_id=state.get("user_id", ""),
            revision_count=revision_count,
            auditor_approved=True,
            note="max_rewrites_cap",
        )
        return "end"

    logger.info(
        "llm_lifecycle",
        stage="graph_route_after_auditor",
        route="rewrite",
        user_id=state.get("user_id", ""),
        revision_count=revision_count,
        auditor_approved=False,
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
