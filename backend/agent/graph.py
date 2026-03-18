from langgraph.graph import StateGraph, END

import structlog
from agent.state import AgentState
from agent.nodes import (
    bouncer_node,
    analyst_node,
    strategist_node,
    writer_node,
    auditor_node,
)

logger = structlog.get_logger(__name__)


def check_cringe(state: AgentState) -> str:
    """
    The routing logic for the Reflection Loop.
    Determines if the drafts are safe to show the user, or if they need a rewrite.
    """
    # 1. If the auditor approved the drafts (no cringe detected), we are done!
    if not state.get("is_cringe"):
        logger.info(
            "agent_route_auditor",
            decision="end",
            is_cringe=state.get("is_cringe"),
            revision_count=state.get("revision_count", 0),
        )
        return "end"

    # 2. The CTO Safety Valve: Prevent infinite loops and massive API bills.
    # If it has already tried to rewrite 2 times (3 total attempts), force it to end.
    # Even a slightly flawed reply is better than an endless loop crashing the app.
    if state.get("revision_count", 0) >= 3:
        logger.info(
            "agent_route_auditor",
            decision="end",
            is_cringe=state.get("is_cringe"),
            revision_count=state.get("revision_count", 0),
            reason="max_revisions",
        )
        return "end"

    # 3. Otherwise, the drafts are cringe. Send them back to the Writer node with feedback.
    logger.info(
        "agent_route_auditor",
        decision="rewrite",
        is_cringe=state.get("is_cringe"),
        revision_count=state.get("revision_count", 0),
    )
    return "rewrite"


# --- 1. Initialize the Graph ---
workflow = StateGraph(AgentState)

def check_bouncer(state: AgentState) -> str:
    """
    Route based on whether the image is a valid chat screenshot.
    """
    decision = "analyst" if state.get("is_valid_chat", False) else "end"
    logger.info(
        "agent_route_bouncer",
        decision=decision,
        is_valid_chat=state.get("is_valid_chat", False),
        bouncer_reason=state.get("bouncer_reason", ""),
    )
    return decision

# --- 2. Add the Nodes ("The Factory Stations") ---
workflow.add_node("bouncer", bouncer_node)
workflow.add_node("analyst", analyst_node)
workflow.add_node("strategist", strategist_node)
workflow.add_node("writer", writer_node)
workflow.add_node("auditor", auditor_node)

# --- 3. Define the Linear Flow ("The Conveyor Belt") ---
workflow.set_entry_point("bouncer")
workflow.add_conditional_edges(
    "bouncer",
    check_bouncer,
    {
        "analyst": "analyst",
        "end": END,
    },
)
workflow.add_edge("analyst", "strategist")
workflow.add_edge("strategist", "writer")
workflow.add_edge("writer", "auditor")

# --- 4. The Magic: The Conditional Loop ---
# This tells LangGraph to pause at the 'auditor' node, run the `check_cringe` function,
# and use the returned string to decide which path to take.
workflow.add_conditional_edges(
    "auditor",
    check_cringe,
    {
        "rewrite": "writer",  # Send it back to the kitchen
        "end": END,  # Serve the dish to the user
    },
)

# --- 5. Compile the Agent ---
rizz_agent = workflow.compile()
