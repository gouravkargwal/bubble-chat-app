"""
V2 agent nodes — 3-node architecture with evaluator-rewriter loop.

Modules:
  _shared.py          — constants, helpers, LLM builder, librarian DB fetch
  _vision.py          — Node 1: bouncer + OCR + analysis (single Gemini multimodal call)
  _generator.py       — Node 2: strategy + writer (structured output, conditional prompts)
  _auditor.py         — Node 3: quality evaluator (per-reply verdicts, rewrite feedback)
  _post_processor.py  — deterministic style fixes (punctuation, casing) + reply validation
"""

from agent.nodes_v2._vision import vision_node
from agent.nodes_v2._generator import generator_node
from agent.nodes_v2._auditor import auditor_node
from agent.nodes_v2._post_processor import post_process_replies

# Backward-compat alias used by vision_v2.py endpoint
_post_process_replies = post_process_replies

__all__ = [
    "vision_node",
    "generator_node",
    "auditor_node",
    "post_process_replies",
    "_post_process_replies",
]
