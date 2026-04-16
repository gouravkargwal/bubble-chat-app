"""LLM-as-judge evaluator — uses Groq (Llama 3.3 70B) to score reply quality.

Groq is used instead of Gemini to avoid same-model bias: the generator runs on
Gemini, so the judge must be a different model family for independent scoring.
"""

import json
import re
from dataclasses import dataclass

import httpx

from app.config import settings
from app.testing.scenarios.dataset import Scenario


@dataclass
class ReplyScore:
    specificity: float  # 1-10
    human_voice: float  # 1-10
    fork_quality: float  # 1-10
    contextual_fit: float  # 1-10
    usability: float  # 1-10
    feedback: str = ""

    @property
    def average(self) -> float:
        return (
            self.specificity
            + self.human_voice
            + self.fork_quality
            + self.contextual_fit
            + self.usability
        ) / 5


@dataclass
class JudgeReport:
    reply_scores: list[ReplyScore]
    overall_score: float
    best_reply_index: int
    worst_reply_index: int
    improvement_notes: str = ""


_SYSTEM_PROMPT = "You are a strict dating text quality evaluator. Output valid JSON only. No markdown, no explanation — pure JSON."

_JUDGE_PROMPT = """You are a dating text quality evaluator. You score AI-generated reply suggestions for dating app conversations.

You are STRICT. A score of 7+ means the reply is genuinely good enough to copy-paste and send. Most AI replies are 4-6 range. Only exceptional replies get 8+.

## SCENARIO
{scenario_description}

Their last message: {their_last_message}
Direction chosen: {direction}

## GENERATED REPLIES
1. {reply_0}
2. {reply_1}
3. {reply_2}
4. {reply_3}

## SCORING CRITERIA (1-10 each)

SPECIFICITY: Does it reference something specific from the conversation?
  1 = completely generic (could send to anyone)
  5 = mentions the topic but generically
  10 = hooks into a very specific detail from the conversation

HUMAN_VOICE: Does it sound like a real person texting on their phone?
  1 = obviously AI (formal, em dashes, "That sounds amazing!")
  5 = okay but slightly polished
  10 = indistinguishable from a real person's text

FORK_QUALITY: Does it create something easy and fun for them to respond to?
  1 = dead end (they'd have nothing to say back)
  5 = has a question but it's generic
  10 = creates a fun choice/challenge/assumption they'd want to respond to

CONTEXTUAL_FIT: Is the tone and energy right for THIS specific moment?
  1 = completely wrong energy (flirty reply to someone who's upset)
  5 = acceptable but not perfectly calibrated
  10 = reads the room perfectly

USABILITY: Would a real person actually copy this and send it?
  1 = never, it's cringe or inappropriate
  5 = maybe, with some editing
  10 = they'd copy it immediately without changing a word

## OUTPUT (strict JSON, no other text)

{{
  "reply_scores": [
    {{"specificity": N, "human_voice": N, "fork_quality": N, "contextual_fit": N, "usability": N, "feedback": "..."}},
    {{"specificity": N, "human_voice": N, "fork_quality": N, "contextual_fit": N, "usability": N, "feedback": "..."}},
    {{"specificity": N, "human_voice": N, "fork_quality": N, "contextual_fit": N, "usability": N, "feedback": "..."}},
    {{"specificity": N, "human_voice": N, "fork_quality": N, "contextual_fit": N, "usability": N, "feedback": "..."}}
  ],
  "overall_score": N,
  "best_reply_index": N,
  "worst_reply_index": N,
  "improvement_notes": "..."
}}"""

_GROQ_BASE_URL = "https://api.groq.com/openai/v1/chat/completions"
# Groq free tier: 30 RPM for llama-3.3-70b-versatile → 2s min between calls
_GROQ_RATE_LIMIT_BACKOFFS = [5, 15, 30]


async def evaluate(
    scenario: Scenario,
    replies: list[str],
    judge_client: object = None,  # kept for API compat, unused
    judge_model: str | None = None,
    _retry: int = 0,
) -> JudgeReport:
    """Score replies using Groq Llama 3.3 70B as judge."""
    api_key = settings.groq_api_key
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Get a free key at https://console.groq.com"
        )

    model = judge_model or settings.groq_model
    padded = replies + ["(no reply)"] * (4 - len(replies))

    prompt = _JUDGE_PROMPT.format(
        scenario_description=scenario.description,
        their_last_message=scenario.their_last_message or scenario.description,
        direction=scenario.direction,
        reply_0=padded[0],
        reply_1=padded[1],
        reply_2=padded[2],
        reply_3=padded[3],
    )

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
        "max_tokens": 2000,
        "response_format": {"type": "json_object"},
    }

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, read=60.0)) as client:
            resp = await client.post(
                _GROQ_BASE_URL,
                json=payload,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
            )
            if resp.status_code == 429:
                if _retry < len(_GROQ_RATE_LIMIT_BACKOFFS):
                    import asyncio

                    wait = _GROQ_RATE_LIMIT_BACKOFFS[_retry]
                    await asyncio.sleep(wait)
                    return await evaluate(
                        scenario=scenario,
                        replies=replies,
                        judge_model=judge_model,
                        _retry=_retry + 1,
                    )
                raise ValueError("Groq rate limit exceeded after retries")
            resp.raise_for_status()
            raw = resp.json()["choices"][0]["message"]["content"] or ""
    except httpx.HTTPStatusError as e:
        raise ValueError(
            f"Groq HTTP error {e.response.status_code}: {e.response.text[:200]}"
        ) from e

    raw = raw.strip()
    # Groq occasionally returns content without outer {} — wrap it
    if raw and not raw.startswith("{"):
        raw = "{" + raw
    if raw and not raw.endswith("}"):
        raw = raw + "}"

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            data = json.loads(match.group(0))
        else:
            raise ValueError(f"Judge returned invalid JSON: {raw[:300]}")

    reply_scores = []
    for score_data in data.get("reply_scores", [])[:4]:
        reply_scores.append(
            ReplyScore(
                specificity=float(score_data.get("specificity", 5)),
                human_voice=float(score_data.get("human_voice", 5)),
                fork_quality=float(score_data.get("fork_quality", 5)),
                contextual_fit=float(score_data.get("contextual_fit", 5)),
                usability=float(score_data.get("usability", 5)),
                feedback=score_data.get("feedback", ""),
            )
        )

    return JudgeReport(
        reply_scores=reply_scores,
        overall_score=float(data.get("overall_score", 5)),
        best_reply_index=int(data.get("best_reply_index", 0)),
        worst_reply_index=int(data.get("worst_reply_index", 0)),
        improvement_notes=data.get("improvement_notes", ""),
    )
