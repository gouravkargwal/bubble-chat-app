"""
Capture Gemini token usage from google-genai SDK
and attach exact costs via app.llm.gemini_pricing.
"""

from __future__ import annotations

import time
from typing import Any

import structlog
from langchain_core.messages import SystemMessage
from pydantic import BaseModel

from app.config import settings
from app.llm.gemini_pricing import usage_record
from app.llm.genai import generate_structured as _genai_structured

logger = structlog.get_logger(__name__)


def _convert_langchain_messages_to_prompt(
    messages: list,
) -> tuple[str, str]:
    """Convert LangChain message list (SystemMessage, HumanMessage) into
    (system_prompt, user_content) strings for use with google-genai SDK.

    The system prompt comes from the first SystemMessage, and the user content
    is the concatenation of all subsequent messages (typically one HumanMessage
    with a JSON string).
    """
    system_prompt = ""
    user_parts: list[str] = []

    for msg in messages:
        if isinstance(msg, SystemMessage):
            system_prompt = msg.content or ""
        else:
            content = msg.content or ""
            if isinstance(content, str):
                user_parts.append(content)
            elif isinstance(content, list):
                # HumanMessage with image parts — handled separately by callers
                user_parts.append(str(content))

    user_content = "\n".join(user_parts) if user_parts else ""
    return system_prompt, user_content


def invoke_structured_groq(
    *,
    model: str,
    temperature: float,
    schema: type[BaseModel],
    messages: list,
    phase: str,
) -> tuple[Any, dict]:
    """
    Structured-output call against Groq via its OpenAI-compatible endpoint
    (langchain_openai.ChatOpenAI). Used to A/B a stronger writer on the generator
    node ONLY. Returns (parsed_pydantic, usage_row) in the same shape as the Gemini
    invoker. cost_usd is logged 0.0 — Gemini pricing does not apply to Groq.
    """
    from langchain_core.callbacks import BaseCallbackHandler
    from langchain_core.outputs import LLMResult
    from langchain_openai import ChatOpenAI

    from agent.nodes_v2._shared import LLM_MAX_RETRIES, LLM_TIMEOUT_SECONDS

    # Define callback inside function to avoid module-level import issues.
    class _GroqCB(BaseCallbackHandler):
        def __init__(self, *, phase: str, model: str) -> None:
            self.phase = phase
            self.model = model
            self.prompt_tokens: int = 0
            self.candidates_tokens: int = 0
            self._seen: bool = False

        def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
            pt, ct, _ = _extract_tokens_from_llm_result(response)
            if pt or ct:
                self.prompt_tokens = pt
                self.candidates_tokens = ct
                self._seen = True

    cb = _GroqCB(phase=phase, model=model)
    llm = ChatOpenAI(
        model=model,
        temperature=temperature,
        api_key=settings.groq_api_key,
        base_url="https://api.groq.com/openai/v1",
        timeout=LLM_TIMEOUT_SECONDS,
        max_retries=LLM_MAX_RETRIES,
    ).with_structured_output(schema, method="function_calling")

    t0 = time.monotonic()
    result = llm.invoke(messages, config={"callbacks": [cb]})
    elapsed_ms = int((time.monotonic() - t0) * 1000)
    pt, ct = cb.prompt_tokens, cb.candidates_tokens
    row = {
        "phase": phase,
        "model": model,
        "prompt_tokens": pt,
        "candidates_tokens": ct,
        "cached_tokens": 0,
        "total_tokens": pt + ct,
        "cost_usd": 0.0,
    }
    logger.info(
        "llm_lifecycle",
        stage="structured_groq_complete",
        phase=phase,
        model=model,
        temperature=temperature,
        elapsed_ms=elapsed_ms,
        prompt_tokens=pt,
        candidates_tokens=ct,
        total_tokens=pt + ct,
    )
    return result, row


def _extract_tokens_from_llm_result(response: LLMResult) -> tuple[int, int, int]:
    """Normalize LangChain / Google GenAI token fields. Returns (prompt, output, cached)."""
    pt, ct, cached = 0, 0, 0

    for gen_list in response.generations:
        for gen in gen_list:
            msg = getattr(gen, "message", None)
            if msg is None:
                continue
            um = getattr(msg, "usage_metadata", None)
            if isinstance(um, dict) and um:
                pt = int(
                    um.get("input_tokens")
                    or um.get("prompt_tokens")
                    or um.get("prompt_token_count")
                    or 0
                )
                ct = int(
                    um.get("output_tokens")
                    or um.get("completion_tokens")
                    or um.get("candidates_token_count")
                    or 0
                )
                details = um.get("input_token_details")
                cached = int(
                    (details.get("cache_read") if isinstance(details, dict) else 0)
                    or um.get("cached_content_token_count")
                    or um.get("cache_read_input_tokens")
                    or 0
                )
                if pt or ct:
                    return pt, ct, cached

    if response.llm_output and isinstance(response.llm_output, dict):
        tu = response.llm_output.get("token_usage")
        if isinstance(tu, dict):
            pt = int(tu.get("prompt_tokens") or tu.get("input_tokens") or 0)
            ct = int(tu.get("completion_tokens") or tu.get("output_tokens") or 0)

    return pt, ct, cached


def invoke_structured_gemini(
    *,
    model: str,
    temperature: float,
    schema: type[BaseModel],
    messages: list,
    phase: str,
) -> tuple[Any, dict]:
    """
    Single structured-output Gemini call via google-genai SDK.
    Replaces the old LangChain-based implementation.

    Converts LangChain messages to plain strings, calls the SDK,
    returns (parsed_pydantic, usage_row dict).

    Note: the old fallback mechanism (retry with gemini_fallback_model)
    is now handled by the google-genai SDK internally.
    """
    system_prompt, user_content = _convert_langchain_messages_to_prompt(messages)

    return _genai_structured(
        model=model,
        temperature=temperature,
        schema=schema,
        system_prompt=system_prompt,
        user_content=user_content,
        phase=phase,
    )
