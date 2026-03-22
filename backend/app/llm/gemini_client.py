"""Gemini vision client using REST API."""

import httpx
import structlog

from app.llm.base import LlmClient
from app.llm.gemini_pricing import usage_record

logger = structlog.get_logger()

_RETRY_ATTEMPTS = 3
_RETRY_DELAY = 1.0


class GeminiClient(LlmClient):
    def __init__(self, api_key: str, default_model: str = "gemini-2.5-flash") -> None:
        self.api_key = api_key
        self.default_model = default_model
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
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}"
            f":generateContent?key={self.api_key}"
        )

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
            # Disable all standard safety filters so we always get a response.
            "safetySettings": [
                {
                    "category": "HARM_CATEGORY_HARASSMENT",
                    "threshold": "BLOCK_NONE",
                },
                {
                    "category": "HARM_CATEGORY_HATE_SPEECH",
                    "threshold": "BLOCK_NONE",
                },
                {
                    "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                    "threshold": "BLOCK_NONE",
                },
                {
                    "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                    "threshold": "BLOCK_NONE",
                },
            ],
        }

        last_error: Exception | None = None
        for attempt in range(1, _RETRY_ATTEMPTS + 1):
            try:
                response = await self._client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()

                usage = data.get("usageMetadata") or {}
                if usage:
                    row = usage_record(
                        phase=usage_phase,
                        model=model,
                        prompt_tokens=usage.get("promptTokenCount"),
                        candidates_tokens=usage.get("candidatesTokenCount"),
                        total_tokens=usage.get("totalTokenCount"),
                    )
                    logger.info(
                        "gemini_usage",
                        model=model,
                        prompt_token_count=row["prompt_tokens"],
                        candidates_token_count=row["candidates_tokens"],
                        total_token_count=usage.get("totalTokenCount"),
                        thoughts_token_count=usage.get("thoughtsTokenCount"),
                        cost_usd=row["cost_usd"],
                        cost_inr=row["cost_inr"],
                    )
                    if usage_sink is not None:
                        usage_sink.append(row)

                # Log the raw Gemini response (truncated) for debugging
                try:
                    logger.debug(
                        "gemini_raw_json",
                        raw=response.text[:4000],
                        model=model,
                        attempt=attempt,
                    )
                except Exception:
                    # Logging should never break the request flow
                    pass

                # Extract text from Gemini response
                candidates = data.get("candidates", [])
                if not candidates:
                    raise ValueError("No candidates in Gemini response")

                content = candidates[0].get("content", {})
                parts = content.get("parts", [])
                if not parts:
                    raise ValueError("No parts in Gemini response")

                # Gemini 2.5 Flash is a thinking model — skip thought parts and concatenate ALL text parts
                text_chunks = []
                for part in parts:
                    if part.get("thought"):
                        continue
                    chunk = part.get("text", "")
                    if chunk:
                        text_chunks.append(chunk)

                text = "".join(text_chunks)

                if not text and parts:
                    # Fallback: use last part's text if all were thought parts
                    text = parts[-1].get("text", "")

                if not text:
                    raise ValueError("Empty text in Gemini response")

                logger.debug(
                    "gemini_parsed_response",
                    parts_count=len(parts),
                    thought_parts=sum(1 for p in parts if p.get("thought")),
                    text_preview=text[:300],
                )

                logger.info(
                    "gemini_success",
                    model=model,
                    attempt=attempt,
                    response_length=len(text),
                )
                return text

            except httpx.HTTPStatusError as e:
                last_error = e
                status = e.response.status_code
                logger.warning(
                    "gemini_http_error",
                    status=status,
                    attempt=attempt,
                    body=e.response.text[:200],
                )
                if status == 401 or status == 403:
                    raise ValueError("Invalid Gemini API key") from e
                if status == 429:
                    raise ValueError("Gemini rate limit exceeded") from e
                if status < 500 and status != 429:
                    raise
                # Retry on 5xx
                if attempt < _RETRY_ATTEMPTS:
                    import asyncio

                    await asyncio.sleep(_RETRY_DELAY * attempt)

            except httpx.TimeoutException as e:
                last_error = e
                logger.warning("gemini_timeout", attempt=attempt)
                if attempt < _RETRY_ATTEMPTS:
                    import asyncio

                    await asyncio.sleep(_RETRY_DELAY * attempt)

            except Exception as e:
                last_error = e
                logger.error("gemini_error", error=str(e), attempt=attempt)
                if attempt < _RETRY_ATTEMPTS:
                    import asyncio

                    await asyncio.sleep(_RETRY_DELAY * attempt)

        raise last_error or RuntimeError("Gemini request failed after all retries")

    async def generate_content(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str = "gemini-2.5-flash",
        temperature: float = 0.3,
        max_output_tokens: int = 1024,
        usage_sink: list[dict] | None = None,
        usage_phase: str = "gemini_generate_content",
    ) -> str:
        """Generic text-only content generation helper."""
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}"
            f":generateContent?key={self.api_key}"
        )

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

        response = await self._client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()

        usage = data.get("usageMetadata") or {}
        if usage:
            row = usage_record(
                phase=usage_phase,
                model=model,
                prompt_tokens=usage.get("promptTokenCount"),
                candidates_tokens=usage.get("candidatesTokenCount"),
                total_tokens=usage.get("totalTokenCount"),
            )
            logger.info(
                "gemini_usage",
                model=model,
                prompt_token_count=row["prompt_tokens"],
                candidates_token_count=row["candidates_tokens"],
                total_token_count=usage.get("totalTokenCount"),
                thoughts_token_count=usage.get("thoughtsTokenCount"),
                cost_usd=row["cost_usd"],
                cost_inr=row["cost_inr"],
            )
            if usage_sink is not None:
                usage_sink.append(row)

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

    async def close(self) -> None:
        await self._client.aclose()
