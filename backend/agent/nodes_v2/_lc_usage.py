"""
Capture Gemini token usage from LangChain ChatGoogleGenerativeAI callbacks
and attach exact costs via app.llm.gemini_pricing.
"""

from __future__ import annotations

import time
from typing import Any

import structlog
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult
from pydantic import BaseModel

from agent.nodes_v2._shared import build_llm
from app.config import settings
from app.llm.gemini_pricing import usage_record

logger = structlog.get_logger(__name__)


class GeminiLangChainUsageCallback(BaseCallbackHandler):
    """Reads token counts from the last on_llm_end payload (one structured call)."""

    def __init__(self, *, phase: str, model: str) -> None:
        self.phase = phase
        self.model = model
        self.prompt_tokens: int = 0
        self.candidates_tokens: int = 0
        self._seen: bool = False

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:  # noqa: ANN401
        pt, ct = _extract_tokens_from_llm_result(response)
        if pt or ct:
            self.prompt_tokens = pt
            self.candidates_tokens = ct
            self._seen = True

    def to_usage_row(self) -> dict:
        if not self._seen or (self.prompt_tokens == 0 and self.candidates_tokens == 0):
            logger.warning(
                "gemini_langchain_usage_missing",
                phase=self.phase,
                model=self.model,
            )
        return usage_record(
            phase=self.phase,
            model=self.model,
            prompt_tokens=self.prompt_tokens,
            candidates_tokens=self.candidates_tokens,
        )


def _extract_tokens_from_llm_result(response: LLMResult) -> tuple[int, int]:
    """Normalize LangChain / Google GenAI token fields."""
    pt, ct = 0, 0

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
                if pt or ct:
                    return pt, ct

    if response.llm_output and isinstance(response.llm_output, dict):
        tu = response.llm_output.get("token_usage")
        if isinstance(tu, dict):
            pt = int(tu.get("prompt_tokens") or tu.get("input_tokens") or 0)
            ct = int(tu.get("completion_tokens") or tu.get("output_tokens") or 0)

    return pt, ct


def _is_capacity_error(exc: BaseException) -> bool:
    """True when Gemini returns 429 (rate limit) or 503 (overload)."""
    tokens = ("429", "503", "UNAVAILABLE", "RESOURCE_EXHAUSTED", "high demand")
    seen: set[int] = set()
    cur: BaseException | None = exc
    while cur is not None and id(cur) not in seen:
        seen.add(id(cur))
        if any(t in str(cur) for t in tokens):
            return True
        cur = getattr(cur, "__cause__", None) or getattr(cur, "__context__", None)
    return False


def invoke_structured_gemini(
    *,
    model: str,
    temperature: float,
    schema: type[BaseModel],
    messages: list,
    phase: str,
) -> tuple[Any, dict]:
    """
    Single structured-output Gemini call with usage + exact USD/INR from gemini_pricing.

    On 429 or 503 from the primary model, retries once with `settings.gemini_fallback_model`.

    Returns (parsed_pydantic, usage_row dict).
    """
    models_to_try = [model]
    fallback = settings.gemini_fallback_model
    if fallback and fallback != model:
        models_to_try.append(fallback)

    last_exc: BaseException | None = None
    for attempt_model in models_to_try:
        cb = GeminiLangChainUsageCallback(phase=phase, model=attempt_model)
        llm = build_llm(model=attempt_model, temperature=temperature, structured_output=schema)
        t0 = time.monotonic()
        try:
            result = llm.invoke(messages, config={"callbacks": [cb]})
        except Exception as exc:
            last_exc = exc
            if attempt_model != models_to_try[-1] and _is_capacity_error(exc):
                logger.warning(
                    "gemini_fallback_triggered",
                    primary_model=model,
                    fallback_model=fallback,
                    phase=phase,
                    error=str(exc)[:200],
                )
                continue
            raise

        row = cb.to_usage_row()
        elapsed_ms = int((time.monotonic() - t0) * 1000)
        logger.info(
            "llm_lifecycle",
            stage="structured_gemini_complete",
            phase=phase,
            model=attempt_model,
            temperature=temperature,
            elapsed_ms=elapsed_ms,
            prompt_tokens=row.get("prompt_tokens"),
            candidates_tokens=row.get("candidates_tokens"),
            total_tokens=row.get("total_tokens"),
            cost_usd=row.get("cost_usd"),
        )
        return result, row

    # All attempts exhausted — re-raise last error
    raise last_exc  # type: ignore[misc]
