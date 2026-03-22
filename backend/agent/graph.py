from langgraph.graph import StateGraph, END

from agent.state import AgentState
from agent.nodes import (
    bouncer_node,
    ocr_extractor_node,
    analyst_node,
    librarian_node,
    strategist_node,
    writer_node,
    auditor_node,
)


def check_cringe(state: AgentState) -> str:
    """
    The routing logic for the Reflection Loop.
    Determines if the drafts are safe to show the user, or if they need a rewrite.
    """
    if not state.get("is_cringe"):
        return "end"

    if state.get("revision_count", 0) >= 3:
        return "end"

    return "rewrite"


workflow = StateGraph(AgentState)


def check_bouncer(state: AgentState) -> str:
    """Route based on whether the image is a valid chat screenshot."""
    return "ocr_extractor" if state.get("is_valid_chat", False) else "end"


workflow.add_node("bouncer", bouncer_node)
workflow.add_node("ocr_extractor", ocr_extractor_node)
workflow.add_node("analyst", analyst_node)
workflow.add_node("librarian", librarian_node)
workflow.add_node("strategist", strategist_node)
workflow.add_node("writer", writer_node)
workflow.add_node("auditor", auditor_node)

workflow.set_entry_point("bouncer")
workflow.add_conditional_edges(
    "bouncer",
    check_bouncer,
    {
        "ocr_extractor": "ocr_extractor",
        "end": END,
    },
)
workflow.add_edge("ocr_extractor", "librarian")
workflow.add_edge("librarian", "analyst")
workflow.add_edge("analyst", "strategist")
workflow.add_edge("strategist", "writer")
workflow.add_edge("writer", "auditor")

workflow.add_conditional_edges(
    "auditor",
    check_cringe,
    {
        "rewrite": "writer",
        "end": END,
    },
)

rizz_agent = workflow.compile()
