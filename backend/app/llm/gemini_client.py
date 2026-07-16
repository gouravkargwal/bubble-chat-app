"""Gemini client using google-genai SDK (replaces raw httpx REST)."""

from __future__ import annotations

import base64
import json
import time

import structlog
from opentelemetry import trace

from app.config import settings
from app.infrastructure.metrics import (
    llm_calls_total,
    llm_latency_seconds,
    llm_tokens_total,
    llm_cost_total,
)
from app.infrastructure.tracing import get_tracer
from app.llm.base import LlmClient
from app.llm.gemini_pricing import cost_usd_for_tokens, usage_record
from app.llm.genai import get_client, _usage_row_from_response

_otel_tracer = get_tracer(__name__)

logger = structlog.get_logger()


class GeminiClient(LlmClient):
    """Gemini client wrapping the google-genai SDK.

    Keeps the same interface as the old httpx-based client so all callers
    (profile_optimizer_service, audit_worker, rag_improvements, tests)
    work without changes.
    """

    def __init__(self, api_key: str, default_model: str | None = None) -> None:
        self.api_key = api_key
        self.default_model = default_model or settings.gemini_model
        # The SDK client is cached globally (lru_cache on get_client()).
        # We keep self._client for backward compat with test patches only.
        self._client = None  # no longer used; SDK handles auth internally

    async def vision_generate(
        self,
        system_prompt: str,
        user_prompt: str,
        base64_images: list[str],
        temperature: float,
        model: str | None = None,
        max_output_tokens: int = 2000,
        response_schema: dict | None = None,
        usage_sink: list[dict] | None = None,
        usage_phase: str = "gemini_vision_generate",
    ) -> str:
        """Vision + text generation via google-genai SDK."""
        model = model or self.default_model
        client = get_client()
        t_start = time.monotonic()

        # Build parts
        parts = []
        for img_b64 in base64_images:
            image_bytes = base64.b64decode(img_b64)
            from google.genai import types

            parts.append(
                types.Part.from_bytes(mime_type="image/jpeg", data=image_bytes)
            )

        config: dict = {
            "temperature": temperature,
            "max_output_tokens": max_output_tokens,
            "system_instruction": system_prompt,
        }
        if response_schema is not None:
            config["response_mime_type"] = "application/json"
            config["response_schema"] = response_schema

        operation = usage_phase
        with _otel_tracer.start_as_current_span(f"gemini.{usage_phase}.call") as span:
            span.set_attribute("gen_ai.system", "gemini")
            span.set_attribute("gen_ai.operation", operation)
            span.set_attribute("gen_ai.request.model", model)
            span.set_attribute("gen_ai.request.max_tokens", max_output_tokens)
            span.set_attribute("gen_ai.request.temperature", temperature)

            try:
                response = client.models.generate_content(
                    model=model,
                    contents=parts,
                    config=config,
                )
                duration = time.monotonic() - t_start

                span.set_attribute("gen_ai.response.status", "success")
                span.set_attribute("duration_ms", round(duration * 1000))

                llm_calls_total.labels(
                    model=model, operation=operation, status="success"
                ).inc()
                llm_latency_seconds.labels(model=model, operation=operation).observe(
                    duration
                )

                text = response.text

                # Usage tracking
                row = _usage_row_from_response(response, phase=usage_phase, model=model)
                if usage_sink is not None:
                    usage_sink.append(row)

                if row.get("prompt_tokens") or row.get("candidates_tokens"):
                    # Record metrics
                    llm_tokens_total.labels(
                        model=model, operation=operation, token_type="input"
                    ).inc(row.get("prompt_tokens", 0))
                    llm_tokens_total.labels(
                        model=model, operation=operation, token_type="output"
                    ).inc(row.get("candidates_tokens", 0))

                    cost = cost_usd_for_tokens(
                        model=model,
                        prompt_tokens=row.get("prompt_tokens", 0),
                        output_tokens=row.get("candidates_tokens", 0),
                    )
                    if cost > 0:
                        llm_cost_total.labels(model=model, operation=operation).inc(
                            cost
                        )

                logger.info(
                    "llm_lifecycle",
                    stage="sdk_gemini_complete",
                    phase=usage_phase,
                    model=model,
                    prompt_tokens=row.get("prompt_tokens"),
                    candidates_tokens=row.get("candidates_tokens"),
                    total_tokens=row.get("total_tokens"),
                )

                if not text:
                    raise ValueError("Empty text in Gemini response")

                return text

            except Exception as e:
                duration = time.monotonic() - t_start
                span.set_attribute("gen_ai.response.status", "error")
                span.record_exception(e)
                llm_calls_total.labels(
                    model=model, operation=operation, status="error"
                ).inc()
                llm_latency_seconds.labels(model=model, operation=operation).observe(
                    duration
                )
                logger.error(
                    "gemini_sdk_error",
                    error=str(e),
                    phase=usage_phase,
                    model=model,
                )
                raise

    async def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        response_schema: dict,
        model: str | None = None,
        temperature: float = 0.0,
        max_output_tokens: int = 1024,
        usage_sink: list[dict] | None = None,
        usage_phase: str = "gemini_generate_structured",
    ) -> dict:
        """Structured JSON generation via google-genai SDK."""
        from app.llm.genai import generate_structured as _structured

        model = model or self.default_model
        t_start = time.monotonic()

        # The SDK generate_structured expects a Pydantic schema, but this method
        # receives a raw dict schema. We use the SDK's text generation with
        # response_schema dict which also works.
        client = get_client()

        config: dict = {
            "temperature": temperature,
            "max_output_tokens": max_output_tokens,
            "response_mime_type": "application/json",
            "response_schema": response_schema,
            "system_instruction": system_prompt,
        }

        operation = usage_phase
        with _otel_tracer.start_as_current_span(f"gemini.{usage_phase}.call") as span:
            span.set_attribute("gen_ai.system", "gemini")
            span.set_attribute("gen_ai.operation", operation)
            span.set_attribute("gen_ai.request.model", model)
            span.set_attribute("gen_ai.request.max_tokens", max_output_tokens)
            span.set_attribute("gen_ai.request.temperature", temperature)

            try:
                response = client.models.generate_content(
                    model=model,
                    contents=user_prompt,
                    config=config,
                )
                duration = time.monotonic() - t_start

                span.set_attribute("gen_ai.response.status", "success")
                span.set_attribute("duration_ms", round(duration * 1000))

                llm_calls_total.labels(
                    model=model, operation=operation, status="success"
                ).inc()
                llm_latency_seconds.labels(model=model, operation=operation).observe(
                    duration
                )

                parsed = json.loads(response.text)

                row = _usage_row_from_response(response, phase=usage_phase, model=model)
                if usage_sink is not None:
                    usage_sink.append(row)

                if row.get("prompt_tokens") or row.get("candidates_tokens"):
                    llm_tokens_total.labels(
                        model=model, operation=operation, token_type="input"
                    ).inc(row.get("prompt_tokens", 0))
                    llm_tokens_total.labels(
                        model=model, operation=operation, token_type="output"
                    ).inc(row.get("candidates_tokens", 0))
                    cost = cost_usd_for_tokens(
                        model=model,
                        prompt_tokens=row.get("prompt_tokens", 0),
                        output_tokens=row.get("candidates_tokens", 0),
                    )
                    if cost > 0:
                        llm_cost_total.labels(model=model, operation=operation).inc(
                            cost
                        )

                logger.info(
                    "llm_lifecycle",
                    stage="sdk_gemini_structured",
                    phase=usage_phase,
                    model=model,
                )
                return parsed

            except Exception as e:
                duration = time.monotonic() - t_start
                span.set_attribute("gen_ai.response.status", "error")
                span.record_exception(e)
                llm_calls_total.labels(
                    model=model, operation=operation, status="error"
                ).inc()
                llm_latency_seconds.labels(model=model, operation=operation).observe(
                    duration
                )
                logger.error(
                    "gemini_sdk_structured_error",
                    error=str(e),
                    phase=usage_phase,
                    model=model,
                )
                raise

    async def generate_content(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str | None = None,
        temperature: float = 0.3,
        max_output_tokens: int = 1024,
        usage_sink: list[dict] | None = None,
        usage_phase: str = "gemini_generate_content",
    ) -> str:
        """Text-only content generation via google-genai SDK."""
        client = get_client()
        model = model or self.default_model
        t_start = time.monotonic()

        config: dict = {
            "temperature": temperature,
            "max_output_tokens": max_output_tokens,
            "system_instruction": system_prompt,
        }

        operation = usage_phase
        with _otel_tracer.start_as_current_span(f"gemini.{usage_phase}.call") as span:
            span.set_attribute("gen_ai.system", "gemini")
            span.set_attribute("gen_ai.operation", operation)
            span.set_attribute("gen_ai.request.model", model)

            try:
                response = client.models.generate_content(
                    model=model,
                    contents=user_prompt,
                    config=config,
                )
                duration = time.monotonic() - t_start

                span.set_attribute("gen_ai.response.status", "success")
                span.set_attribute("duration_ms", round(duration * 1000))

                llm_calls_total.labels(
                    model=model, operation=operation, status="success"
                ).inc()
                llm_latency_seconds.labels(model=model, operation=operation).observe(
                    duration
                )

                text = response.text

                row = _usage_row_from_response(response, phase=usage_phase, model=model)
                if usage_sink is not None:
                    usage_sink.append(row)

                if row.get("prompt_tokens") or row.get("candidates_tokens"):
                    llm_tokens_total.labels(
                        model=model, operation=operation, token_type="input"
                    ).inc(row.get("prompt_tokens", 0))
                    llm_tokens_total.labels(
                        model=model, operation=operation, token_type="output"
                    ).inc(row.get("candidates_tokens", 0))
                    cost = cost_usd_for_tokens(
                        model=model,
                        prompt_tokens=row.get("prompt_tokens", 0),
                        output_tokens=row.get("candidates_tokens", 0),
                    )
                    if cost > 0:
                        llm_cost_total.labels(model=model, operation=operation).inc(
                            cost
                        )

                logger.info(
                    "llm_lifecycle",
                    stage="sdk_gemini_content",
                    phase=usage_phase,
                    model=model,
                )

                if not text:
                    raise ValueError("Empty text in Gemini response")

                return text

            except Exception as e:
                duration = time.monotonic() - t_start
                span.set_attribute("gen_ai.response.status", "error")
                span.record_exception(e)
                llm_calls_total.labels(
                    model=model, operation=operation, status="error"
                ).inc()
                llm_latency_seconds.labels(model=model, operation=operation).observe(
                    duration
                )
                logger.error(
                    "gemini_sdk_content_error",
                    error=str(e),
                    phase=usage_phase,
                    model=model,
                )
                raise

    async def close(self) -> None:
        """No-op: the SDK client is module-level cached, not per-instance."""
        pass
