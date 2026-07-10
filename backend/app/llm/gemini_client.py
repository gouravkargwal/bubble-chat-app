"""Gemini vision client using REST API."""

import json
import time

import httpx
import structlog
from opentelemetry import trace

from app.config import settings
from app.infrastructure.metrics import (
    llm_calls_total,
    llm_latency_seconds,
    llm_tokens_total,
    llm_cost_total,
    llm_fallback_total,
)
from app.infrastructure.tracing import get_tracer
from app.llm.base import LlmClient
from app.llm.gemini_pricing import usage_record

_otel_tracer = get_tracer(__name__)

_FALLBACK_TRIGGER_STATUSES = {429, 503}

logger = structlog.get_logger()

_RETRY_ATTEMPTS = 3
_RETRY_DELAY = 1.0


class GeminiClient(LlmClient):
    def __init__(self, api_key: str, default_model: str | None = None) -> None:
        self.api_key = api_key
        self.default_model = default_model or settings.gemini_model
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(30.0, read=60.0))

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
        model = model or self.default_model

        parts: list[dict] = [{"text": user_prompt}]
        for img in base64_images:
            parts.append(
                {
                    "inlineData": {
                        "mimeType": "image/jpeg",
                        "data": img,
                    }
                }
            )

        generation_config: dict = {
            "temperature": temperature,
            "maxOutputTokens": max_output_tokens,
            "responseMimeType": "application/json",
        }
        if response_schema is not None:
            generation_config["responseSchema"] = response_schema

        payload = {
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"parts": parts}],
            "generationConfig": generation_config,
            "safetySettings": [
                {"category": c, "threshold": "BLOCK_NONE"}
                for c in (
                    "HARM_CATEGORY_HARASSMENT",
                    "HARM_CATEGORY_HATE_SPEECH",
                    "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                    "HARM_CATEGORY_DANGEROUS_CONTENT",
                )
            ],
        }

        primary_model = model
        fallback_model = settings.gemini_fallback_model
        models_to_try = [primary_model]
        if fallback_model and fallback_model != primary_model:
            models_to_try.append(fallback_model)

        last_error: Exception | None = None
        for model_attempt in models_to_try:
            attempt_url = (
                f"https://generativelanguage.googleapis.com/v1beta/models/{model_attempt}"
                f":generateContent?key={self.api_key}"
            )
            for attempt in range(1, _RETRY_ATTEMPTS + 1):
                operation = usage_phase
                start_time = time.monotonic()
                with _otel_tracer.start_as_current_span(
                    f"gemini.{usage_phase}.call"
                ) as span:
                    span.set_attribute("gen_ai.system", "gemini")
                    span.set_attribute("gen_ai.operation", operation)
                    span.set_attribute("gen_ai.request.model", model_attempt)
                    span.set_attribute("gen_ai.request.max_tokens", max_output_tokens)
                    span.set_attribute("gen_ai.request.temperature", temperature)
                    span.set_attribute("gen_ai.request.attempt", attempt)
                    span.set_attribute("http.url", attempt_url)

                    try:
                        response = await self._client.post(attempt_url, json=payload)
                        response.raise_for_status()
                        data = response.json()
                        duration = time.monotonic() - start_time

                        # Record LLM call success
                        llm_calls_total.labels(
                            model=model_attempt, operation=operation, status="success"
                        ).inc()
                        llm_latency_seconds.labels(
                            model=model_attempt, operation=operation
                        ).observe(duration)

                        span.set_attribute("gen_ai.response.status", "success")
                        span.set_attribute("duration_ms", round(duration * 1000))

                        usage = data.get("usageMetadata") or {}
                        if usage:
                            prompt_tokens = usage.get("promptTokenCount") or 0
                            candidates_tokens = usage.get("candidatesTokenCount") or 0
                            total_tokens = usage.get("totalTokenCount") or 0

                            span.set_attribute(
                                "gen_ai.usage.prompt_tokens", prompt_tokens
                            )
                            span.set_attribute(
                                "gen_ai.usage.completion_tokens", candidates_tokens
                            )
                            span.set_attribute(
                                "gen_ai.usage.total_tokens", total_tokens
                            )

                            llm_tokens_total.labels(
                                model=model_attempt,
                                operation=operation,
                                token_type="input",
                            ).inc(prompt_tokens)
                            llm_tokens_total.labels(
                                model=model_attempt,
                                operation=operation,
                                token_type="output",
                            ).inc(candidates_tokens)

                            row = usage_record(
                                phase=usage_phase,
                                model=model_attempt,
                                prompt_tokens=prompt_tokens,
                                candidates_tokens=candidates_tokens,
                                total_tokens=total_tokens,
                            )
                            if usage_sink is not None:
                                usage_sink.append(row)

                            from app.llm.gemini_pricing import estimate_cost

                            cost = estimate_cost(
                                model=model_attempt,
                                prompt_tokens=prompt_tokens,
                                completion_tokens=candidates_tokens,
                            )
                            if cost > 0:
                                llm_cost_total.labels(
                                    model=model_attempt, operation=operation
                                ).inc(cost)

                        # Extract text from Gemini response
                        candidates = data.get("candidates", [])
                        if not candidates:
                            raise ValueError("No candidates in Gemini response")

                        content = candidates[0].get("content", {})
                        parts = content.get("parts", [])
                        if not parts:
                            raise ValueError("No parts in Gemini response")

                        text_chunks = []
                        for part in parts:
                            if part.get("thought"):
                                continue
                            chunk = part.get("text", "")
                            if chunk:
                                text_chunks.append(chunk)

                        text = "".join(text_chunks)

                        if not text and parts:
                            text = parts[-1].get("text", "")

                        if not text:
                            raise ValueError("Empty text in Gemini response")

                        logger.info(
                            "llm_lifecycle",
                            stage="rest_gemini_complete",
                            phase=usage_phase,
                            model=model_attempt,
                            prompt_tokens=(
                                usage.get("promptTokenCount") if usage else None
                            ),
                            candidates_tokens=(
                                usage.get("candidatesTokenCount") if usage else None
                            ),
                            total_tokens=(
                                usage.get("totalTokenCount") if usage else None
                            ),
                        )

                        return text

                    except httpx.HTTPStatusError as e:
                        last_error = e
                        duration = time.monotonic() - start_time
                        status = e.response.status_code
                        span.set_attribute("gen_ai.response.status", f"http_{status}")
                        span.set_attribute("http.status_code", status)
                        logger.warning(
                            "gemini_http_error",
                            status=status,
                            attempt=attempt,
                            model=model_attempt,
                            body=e.response.text[:200],
                        )

                        llm_calls_total.labels(
                            model=model_attempt, operation=operation, status="error"
                        ).inc()
                        llm_latency_seconds.labels(
                            model=model_attempt, operation=operation
                        ).observe(duration)

                        if status == 401 or status == 403:
                            raise ValueError("Invalid Gemini API key") from e
                        if status in _FALLBACK_TRIGGER_STATUSES:
                            if model_attempt != models_to_try[-1]:
                                break
                            raise ValueError(
                                f"Gemini capacity error (HTTP {status}) on all models"
                            ) from e
                        if status < 500:
                            raise
                        if attempt < _RETRY_ATTEMPTS:
                            import asyncio

                            await asyncio.sleep(_RETRY_DELAY * attempt)

                    except httpx.TimeoutException as e:
                        last_error = e
                        duration = time.monotonic() - start_time
                        span.set_attribute("gen_ai.response.status", "timeout")
                        logger.warning(
                            "gemini_timeout", attempt=attempt, model=model_attempt
                        )

                        llm_calls_total.labels(
                            model=model_attempt, operation=operation, status="timeout"
                        ).inc()
                        llm_latency_seconds.labels(
                            model=model_attempt, operation=operation
                        ).observe(duration)

                        if attempt < _RETRY_ATTEMPTS:
                            import asyncio

                            await asyncio.sleep(_RETRY_DELAY * attempt)

                    except Exception as e:
                        last_error = e
                        duration = time.monotonic() - start_time
                        span.set_attribute("gen_ai.response.status", "error")
                        span.record_exception(e)
                        logger.error(
                            "gemini_error",
                            error=str(e),
                            attempt=attempt,
                            model=model_attempt,
                        )

                        llm_calls_total.labels(
                            model=model_attempt, operation=operation, status="error"
                        ).inc()
                        llm_latency_seconds.labels(
                            model=model_attempt, operation=operation
                        ).observe(duration)

                        if attempt < _RETRY_ATTEMPTS:
                            import asyncio

                            await asyncio.sleep(_RETRY_DELAY * attempt)
            else:
                raise last_error or RuntimeError(
                    "Gemini request failed after all retries"
                )

        raise last_error or RuntimeError("Gemini request failed after all retries")

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
        """Structured JSON generation with a response schema."""
        model = model or self.default_model

        generation_config: dict = {
            "temperature": temperature,
            "maxOutputTokens": max_output_tokens,
            "responseMimeType": "application/json",
            "responseSchema": response_schema,
        }

        payload = {
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"parts": [{"text": user_prompt}]}],
            "generationConfig": generation_config,
            "safetySettings": [
                {"category": c, "threshold": "BLOCK_NONE"}
                for c in (
                    "HARM_CATEGORY_HARASSMENT",
                    "HARM_CATEGORY_HATE_SPEECH",
                    "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                    "HARM_CATEGORY_DANGEROUS_CONTENT",
                )
            ],
        }

        primary_model = model
        fallback_model = settings.gemini_fallback_model
        models_to_try = [primary_model]
        if fallback_model and fallback_model != primary_model:
            models_to_try.append(fallback_model)

        last_error: Exception | None = None
        for model_attempt in models_to_try:
            attempt_url = (
                f"https://generativelanguage.googleapis.com/v1beta/models/{model_attempt}"
                f":generateContent?key={self.api_key}"
            )
            for attempt in range(1, _RETRY_ATTEMPTS + 1):
                operation = usage_phase
                start_time = time.monotonic()
                with _otel_tracer.start_as_current_span(
                    f"gemini.{usage_phase}.call"
                ) as span:
                    span.set_attribute("gen_ai.system", "gemini")
                    span.set_attribute("gen_ai.operation", operation)
                    span.set_attribute("gen_ai.request.model", model_attempt)
                    span.set_attribute("gen_ai.request.max_tokens", max_output_tokens)
                    span.set_attribute("gen_ai.request.temperature", temperature)
                    span.set_attribute("gen_ai.request.attempt", attempt)
                    span.set_attribute("http.url", attempt_url)

                    try:
                        response = await self._client.post(attempt_url, json=payload)
                        response.raise_for_status()
                        data = response.json()
                        duration = time.monotonic() - start_time

                        llm_calls_total.labels(
                            model=model_attempt, operation=operation, status="success"
                        ).inc()
                        llm_latency_seconds.labels(
                            model=model_attempt, operation=operation
                        ).observe(duration)

                        span.set_attribute("gen_ai.response.status", "success")
                        span.set_attribute("duration_ms", round(duration * 1000))

                        usage = data.get("usageMetadata") or {}
                        if usage:
                            prompt_tokens = usage.get("promptTokenCount") or 0
                            candidates_tokens = usage.get("candidatesTokenCount") or 0

                            span.set_attribute(
                                "gen_ai.usage.prompt_tokens", prompt_tokens
                            )
                            span.set_attribute(
                                "gen_ai.usage.completion_tokens", candidates_tokens
                            )

                            llm_tokens_total.labels(
                                model=model_attempt,
                                operation=operation,
                                token_type="input",
                            ).inc(prompt_tokens)
                            llm_tokens_total.labels(
                                model=model_attempt,
                                operation=operation,
                                token_type="output",
                            ).inc(candidates_tokens)

                            row = usage_record(
                                phase=usage_phase,
                                model=model_attempt,
                                prompt_tokens=prompt_tokens,
                                candidates_tokens=candidates_tokens,
                                total_tokens=usage.get("totalTokenCount") or 0,
                            )
                            if usage_sink is not None:
                                usage_sink.append(row)

                            from app.llm.gemini_pricing import estimate_cost

                            cost = estimate_cost(
                                model=model_attempt,
                                prompt_tokens=prompt_tokens,
                                completion_tokens=candidates_tokens,
                            )
                            if cost > 0:
                                llm_cost_total.labels(
                                    model=model_attempt, operation=operation
                                ).inc(cost)

                        candidates = data.get("candidates", [])
                        if not candidates:
                            raise ValueError("No candidates in structured response")

                        content = candidates[0].get("content", {})
                        parts = content.get("parts", [])
                        if not parts:
                            raise ValueError("No parts in structured response")

                        text_chunks = []
                        for part in parts:
                            if part.get("thought"):
                                continue
                            chunk = part.get("text", "")
                            if chunk:
                                text_chunks.append(chunk)

                        text = "".join(text_chunks)
                        if not text and parts:
                            text = parts[-1].get("text", "")

                        if not text:
                            raise ValueError("Empty text in structured response")

                        parsed = json.loads(text)

                        logger.info(
                            "llm_lifecycle",
                            stage="rest_gemini_structured",
                            phase=usage_phase,
                            model=model_attempt,
                        )
                        return parsed

                    except httpx.HTTPStatusError as e:
                        last_error = e
                        duration = time.monotonic() - start_time
                        status = e.response.status_code
                        span.set_attribute("gen_ai.response.status", f"http_{status}")
                        span.set_attribute("http.status_code", status)
                        logger.warning(
                            "gemini_structured_http_error",
                            status=status,
                            attempt=attempt,
                            model=model_attempt,
                            body=e.response.text[:200],
                        )

                        llm_calls_total.labels(
                            model=model_attempt, operation=operation, status="error"
                        ).inc()
                        llm_latency_seconds.labels(
                            model=model_attempt, operation=operation
                        ).observe(duration)

                        if status == 401 or status == 403:
                            raise ValueError("Invalid Gemini API key") from e
                        if status in _FALLBACK_TRIGGER_STATUSES:
                            if model_attempt != models_to_try[-1]:
                                logger.warning(
                                    "gemini_fallback_triggered",
                                    primary_model=primary_model,
                                    fallback_model=fallback_model,
                                    phase=usage_phase,
                                    status=status,
                                )
                                llm_fallback_total.labels(
                                    primary_model=primary_model,
                                    fallback_model=fallback_model,
                                    reason=f"http_{status}",
                                ).inc()
                                break
                            raise ValueError(
                                f"Gemini capacity error (HTTP {status}) on all models"
                            ) from e
                        if status < 500:
                            raise
                        if attempt < _RETRY_ATTEMPTS:
                            import asyncio

                            await asyncio.sleep(_RETRY_DELAY * attempt)

                    except httpx.TimeoutException as e:
                        last_error = e
                        duration = time.monotonic() - start_time
                        span.set_attribute("gen_ai.response.status", "timeout")
                        logger.warning(
                            "gemini_structured_timeout",
                            attempt=attempt,
                            model=model_attempt,
                        )

                        llm_calls_total.labels(
                            model=model_attempt, operation=operation, status="timeout"
                        ).inc()
                        llm_latency_seconds.labels(
                            model=model_attempt, operation=operation
                        ).observe(duration)

                        if attempt < _RETRY_ATTEMPTS:
                            import asyncio

                            await asyncio.sleep(_RETRY_DELAY * attempt)

                    except Exception as e:
                        last_error = e
                        duration = time.monotonic() - start_time
                        span.set_attribute("gen_ai.response.status", "error")
                        span.record_exception(e)
                        logger.error(
                            "gemini_structured_error",
                            error=str(e),
                            attempt=attempt,
                            model=model_attempt,
                        )

                        llm_calls_total.labels(
                            model=model_attempt, operation=operation, status="error"
                        ).inc()
                        llm_latency_seconds.labels(
                            model=model_attempt, operation=operation
                        ).observe(duration)

                        if attempt < _RETRY_ATTEMPTS:
                            import asyncio

                            await asyncio.sleep(_RETRY_DELAY * attempt)
            else:
                raise last_error or RuntimeError(
                    "Gemini structured request failed after all retries"
                )

        raise last_error or RuntimeError(
            "Gemini structured request failed after all models"
        )

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
        """Generic text-only content generation helper."""
        model = model or self.default_model

        generation_config: dict = {
            "temperature": temperature,
            "maxOutputTokens": max_output_tokens,
            "responseMimeType": "text/plain",
        }

        payload = {
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"parts": [{"text": user_prompt}]}],
            "generationConfig": generation_config,
        }

        primary_model = model
        fallback_model = settings.gemini_fallback_model
        models_to_try = [primary_model]
        if fallback_model and fallback_model != primary_model:
            models_to_try.append(fallback_model)

        operation = usage_phase
        last_error: Exception | None = None
        for model_attempt in models_to_try:
            attempt_url = (
                f"https://generativelanguage.googleapis.com/v1beta/models/{model_attempt}"
                f":generateContent?key={self.api_key}"
            )
            start_time = time.monotonic()
            with _otel_tracer.start_as_current_span(
                f"gemini.{usage_phase}.call"
            ) as span:
                span.set_attribute("gen_ai.system", "gemini")
                span.set_attribute("gen_ai.operation", operation)
                span.set_attribute("gen_ai.request.model", model_attempt)
                span.set_attribute("http.url", attempt_url)

                try:
                    response = await self._client.post(attempt_url, json=payload)
                    response.raise_for_status()
                except httpx.HTTPStatusError as e:
                    last_error = e
                    duration = time.monotonic() - start_time
                    status = e.response.status_code
                    span.set_attribute("gen_ai.response.status", f"http_{status}")
                    span.set_attribute("http.status_code", status)

                    llm_calls_total.labels(
                        model=model_attempt, operation=operation, status="error"
                    ).inc()
                    llm_latency_seconds.labels(
                        model=model_attempt, operation=operation
                    ).observe(duration)

                    if (
                        status in _FALLBACK_TRIGGER_STATUSES
                        and model_attempt != models_to_try[-1]
                    ):
                        logger.warning(
                            "gemini_fallback_triggered",
                            primary_model=primary_model,
                            fallback_model=fallback_model,
                            phase=usage_phase,
                            status=status,
                        )
                        llm_fallback_total.labels(
                            primary_model=primary_model,
                            fallback_model=fallback_model,
                            reason=f"http_{status}",
                        ).inc()
                        continue
                    raise

                duration = time.monotonic() - start_time
                data = response.json()

                span.set_attribute("gen_ai.response.status", "success")
                span.set_attribute("duration_ms", round(duration * 1000))

                llm_calls_total.labels(
                    model=model_attempt, operation=operation, status="success"
                ).inc()
                llm_latency_seconds.labels(
                    model=model_attempt, operation=operation
                ).observe(duration)

                usage = data.get("usageMetadata") or {}
                if usage:
                    prompt_tokens = usage.get("promptTokenCount") or 0
                    candidates_tokens = usage.get("candidatesTokenCount") or 0

                    span.set_attribute("gen_ai.usage.prompt_tokens", prompt_tokens)
                    span.set_attribute(
                        "gen_ai.usage.completion_tokens", candidates_tokens
                    )

                    llm_tokens_total.labels(
                        model=model_attempt, operation=operation, token_type="input"
                    ).inc(prompt_tokens)
                    llm_tokens_total.labels(
                        model=model_attempt, operation=operation, token_type="output"
                    ).inc(candidates_tokens)

                    row = usage_record(
                        phase=usage_phase,
                        model=model_attempt,
                        prompt_tokens=prompt_tokens,
                        candidates_tokens=candidates_tokens,
                        total_tokens=usage.get("totalTokenCount") or 0,
                    )
                    if usage_sink is not None:
                        usage_sink.append(row)

                    from app.llm.gemini_pricing import estimate_cost

                    cost = estimate_cost(
                        model=model_attempt,
                        prompt_tokens=prompt_tokens,
                        completion_tokens=candidates_tokens,
                    )
                    if cost > 0:
                        llm_cost_total.labels(
                            model=model_attempt, operation=operation
                        ).inc(cost)

                candidates = data.get("candidates", [])
                if not candidates:
                    raise ValueError("No candidates in Gemini text response")

                content = candidates[0].get("content", {})
                parts = content.get("parts", [])
                if not parts:
                    raise ValueError("No parts in Gemini text response")

                text_chunks = [p.get("text", "") for p in parts if p.get("text")]
                text = "".join(text_chunks).strip()
                if not text:
                    raise ValueError("Empty text in Gemini text response")

                return text

        raise last_error or RuntimeError(
            "Gemini generate_content failed after all models"
        )

    async def close(self) -> None:
        await self._client.aclose()
