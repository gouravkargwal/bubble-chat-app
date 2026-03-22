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

from langgraph.graph import StateGraph, END

from agent.state import AgentState
from agent.nodes_v2 import vision_node, generator_node, auditor_node


def check_valid_chat(state: AgentState) -> str:
    return "generate" if state.get("is_valid_chat", False) else "end"


def check_audit(state: AgentState) -> str:
    """
    Route based on auditor verdict:
    - "end": replies are good enough → ship them
    - "rewrite": replies have issues → send back to generator with feedback
    """
    is_cringe = state.get("is_cringe", False)
    revision_count = state.get("revision_count", 0)

    if not is_cringe:
        return "end"

    if revision_count >= 2:
        return "end"

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
