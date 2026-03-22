"""
Gemini API cost from published list prices (USD per 1M tokens).

Source of truth: https://ai.google.dev/gemini-api/docs/pricing
Update this table when Google changes rates or you add models.

Billing note: Google invoices in USD; INR is an approximate conversion for dashboards.
"""

from __future__ import annotations

import structlog

logger = structlog.get_logger(__name__)

# Default INR display rate (override in callers if needed).
DEFAULT_INR_PER_USD = 90.0

# (input_usd_per_1m, output_usd_per_1m) — text/image/video input unless noted.
_MODEL_RATES: dict[str, tuple[float, float]] = {
    # Gemini 3.1 family (Developer API pricing page, Standard)
    "gemini-3.1-flash-lite-preview": (0.25, 1.50),
    "gemini-3.1-pro-preview": (2.00, 12.00),
    "gemini-3.1-pro": (2.00, 12.00),
    # Gemini 2.5 (common defaults for settings.gemini_model)
    "gemini-2.5-flash": (0.30, 2.50),
    "gemini-2.5-flash-lite": (0.10, 0.40),
    "gemini-2.5-flash-lite-preview-09-2025": (0.10, 0.40),
    # Embeddings (input only; output cost 0)
    "gemini-embedding-001": (0.15, 0.0),
    "models/gemini-embedding-001": (0.15, 0.0),
}

# Prefix fallbacks: first match wins (order matters — list specific prefixes first).
_PREFIX_RATES: list[tuple[str, tuple[float, float]]] = [
    ("gemini-3.1-flash-lite", (0.25, 1.50)),
    ("gemini-3.1-pro", (2.00, 12.00)),
    ("gemini-2.5-flash-lite", (0.10, 0.40)),
    ("gemini-2.5-flash", (0.30, 2.50)),
]


def normalize_model_name(model: str) -> str:
    m = model.strip()
    if m.startswith("models/"):
        m = m[len("models/") :]
    return m


def resolve_rates_per_million_tokens(model: str) -> tuple[float, float]:
    """Return (input_usd_per_1m, output_usd_per_1m) for a model id."""
    key = normalize_model_name(model)
    if key in _MODEL_RATES:
        return _MODEL_RATES[key]
    for prefix, rates in _PREFIX_RATES:
        if key.startswith(prefix):
            return rates
    logger.warning("gemini_pricing_unknown_model", model=model, normalized=key)
    return (0.30, 2.50)


def cost_usd_for_tokens(
    model: str,
    prompt_tokens: int,
    output_tokens: int,
) -> float:
    """Exact cost from token counts and the pricing table (paid tier assumptions)."""
    pin, pout = resolve_rates_per_million_tokens(model)
    return (max(0, prompt_tokens) / 1_000_000.0) * pin + (
        max(0, output_tokens) / 1_000_000.0
    ) * pout


def usd_to_inr(usd: float, inr_per_usd: float = DEFAULT_INR_PER_USD) -> float:
    return round(usd * inr_per_usd, 6)


def usage_record(
    *,
    phase: str,
    model: str,
    prompt_tokens: int | None,
    candidates_tokens: int | None,
    total_tokens: int | None = None,
    inr_per_usd: float = DEFAULT_INR_PER_USD,
) -> dict:
    """Single structured usage row + computed cost."""
    pt = int(prompt_tokens or 0)
    ct = int(candidates_tokens or 0)
    if total_tokens is not None and pt == 0 and ct == 0 and total_tokens > 0:
        # Only total_tokens — cannot split input vs output cost from this field alone.
        logger.warning(
            "gemini_pricing_only_total_tokens",
            phase=phase,
            model=model,
            total_tokens=total_tokens,
        )
    cost_usd = cost_usd_for_tokens(model, pt, ct)
    return {
        "phase": phase,
        "model": normalize_model_name(model),
        "prompt_tokens": pt,
        "candidates_tokens": ct,
        "total_tokens": pt + ct,
        "cost_usd": round(cost_usd, 8),
        "cost_inr": round(usd_to_inr(cost_usd, inr_per_usd), 6),
    }


def sum_usage_records(rows: list[dict]) -> dict:
    """Aggregate a list of usage_record dicts."""
    pt = sum(int(r.get("prompt_tokens", 0) or 0) for r in rows)
    ct = sum(int(r.get("candidates_tokens", 0) or 0) for r in rows)
    usd = sum(float(r.get("cost_usd", 0) or 0) for r in rows)
    return {
        "prompt_tokens": pt,
        "candidates_tokens": ct,
        "total_tokens": pt + ct,
        "cost_usd": round(usd, 8),
        "cost_inr": round(usd_to_inr(usd), 6),
        "call_count": len(rows),
    }
