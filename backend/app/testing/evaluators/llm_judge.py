"""LLM-as-judge evaluator — uses Groq (Llama 3.3 70B) to score reply quality.

Groq is used instead of Gemini to avoid same-model bias: the generator runs on
Gemini, so the judge must be a different model family for independent scoring.

Scores are on a 1-5 scale.
"""

import json
import re
from dataclasses import dataclass

import httpx

from app.config import settings
from app.testing.scenarios.dataset import Scenario


@dataclass
class ReplyScore:
    specificity: float  # 1-5
    human_voice: float  # 1-5
    fork_quality: float  # 1-5
    contextual_fit: float  # 1-5
    usability: float  # 1-5
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

You are STRICT. Most AI replies fall in the 2-3 range. Only truly exceptional, copy-paste-ready replies get a 5. A reply that is merely good scores 3-4. A reply that is perfect on one dimension is rarely perfect on all five — be skeptical of giving 5 across the board.

## CALIBRATION EXAMPLES

TERRIBLE reply (all dimensions = 1):
"Greetings! Your profile indicates you enjoy tacos. I, too, find them to be a delightful culinary experience. Shall we partake?"
→ Stiff, obviously AI, zero personality, no fork, creepy presumption.

PASSABLE reply (most dimensions = 3):
"haha yeah cults are wild, i've seen a few of those documentaries"
→ Acknowledges the topic but adds nothing; generic; she could only reply "yeah" and the thread dies.

PERFECT reply (most dimensions = 5):
"okay but only if you promise not to steal the good salsa this time"
→ Specific callback, sounds like a real person, funny implicit assumption, she has to respond.

## BOUNDARY RULE
If any reply is sexually explicit, pressuring, or socially oblivious/creepy in a way a real person would screenshot and report — set that reply's USABILITY = 1 regardless of other dimensions.

## SCENARIO
{scenario_description}

Their last message: {their_last_message}
Direction chosen: {direction}

## GENERATED REPLIES
1. {reply_0}
2. {reply_1}
3. {reply_2}
4. {reply_3}

## SCORING CRITERIA (1-5 each)

SPECIFICITY — Does it hook into a specific detail from the conversation?
  1 = completely generic (could send to anyone)
  3 = mentions the topic but stays surface-level
  5 = anchors on a very specific word, name, place, or detail

HUMAN_VOICE — Sounds like a real person texting on their phone?
  1 = obviously AI (formal, em dashes, "That sounds amazing!")
  3 = okay but slightly polished or safe
  5 = indistinguishable from a real person's casual text

FORK_QUALITY — Creates something easy and fun for them to respond to?
  1 = dead end (nothing to say back, or just "haha")
  3 = has an opening but it's a flat question
  5 = implicit challenge, playful accusation, or bet they'd want to react to

CONTEXTUAL_FIT — Right tone and energy for THIS specific moment?
  1 = completely wrong (flirty when she's venting, cold when she's warm)
  3 = acceptable but not calibrated to this exact situation
  5 = reads the room and the moment perfectly

USABILITY — Would a real person actually copy and send this?
  1 = never (cringe, inappropriate, or socially tone-deaf)
  3 = maybe, after editing a word or two
  5 = copy it immediately without changing a word

## OUTPUT (strict JSON, no other text)

For each reply: write "reasoning" first (1-2 sentences evaluating the reply), then the five numeric scores.
This order is required — you must reason before scoring.

{{
  "reply_scores": [
    {{"reasoning": "...", "specificity": N, "human_voice": N, "fork_quality": N, "contextual_fit": N, "usability": N}},
    {{"reasoning": "...", "specificity": N, "human_voice": N, "fork_quality": N, "contextual_fit": N, "usability": N}},
    {{"reasoning": "...", "specificity": N, "human_voice": N, "fork_quality": N, "contextual_fit": N, "usability": N}},
    {{"reasoning": "...", "specificity": N, "human_voice": N, "fork_quality": N, "contextual_fit": N, "usability": N}}
  ],
  "overall_score": N,
  "best_reply_index": N,
  "worst_reply_index": N,
  "improvement_notes": "..."
}}

overall_score is on the same 1-5 scale. It is the average quality across ALL 4 replies — not just the best one. A set with one great reply and three mediocre ones should score around 3, not 5."""

_GROQ_BASE_URL = "https://api.groq.com/openai/v1/chat/completions"
# Groq free tier: 30 RPM for llama-3.3-70b-versatile → 2s min between calls
_GROQ_RATE_LIMIT_BACKOFFS = [15, 30, 60, 120]

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
        def clamp(val: float) -> float:
            return min(5.0, max(1.0, val))

        reply_scores.append(
            ReplyScore(
                specificity=clamp(float(score_data.get("specificity", 3))),
                human_voice=clamp(float(score_data.get("human_voice", 3))),
                fork_quality=clamp(float(score_data.get("fork_quality", 3))),
                contextual_fit=clamp(float(score_data.get("contextual_fit", 3))),
                usability=clamp(float(score_data.get("usability", 3))),
                feedback=score_data.get("reasoning") or score_data.get("feedback", ""),
            )
        )

    return JudgeReport(
        reply_scores=reply_scores,
        overall_score=clamp(float(data.get("overall_score", 3))),
        best_reply_index=int(data.get("best_reply_index", 0)),
        worst_reply_index=int(data.get("worst_reply_index", 0)),
        improvement_notes=data.get("improvement_notes", ""),
    )
