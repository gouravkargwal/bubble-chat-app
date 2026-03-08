"""LLM-as-judge evaluator — uses a separate LLM call to score reply quality."""

import json

from app.llm.base import LlmClient
from app.testing.scenarios.dataset import Scenario

from dataclasses import dataclass


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
        return (self.specificity + self.human_voice + self.fork_quality + self.contextual_fit + self.usability) / 5


@dataclass
class JudgeReport:
    reply_scores: list[ReplyScore]
    overall_score: float
    best_reply_index: int
    worst_reply_index: int
    improvement_notes: str = ""


_JUDGE_PROMPT = """You are a dating text quality evaluator. You score AI-generated reply suggestions for dating app conversations.

You are STRICT. A score of 7+ means the reply is genuinely good enough to copy-paste and send. Most AI replies are 4-6 range. Only exceptional replies get 8+.

## SCENARIO
{scenario_description}

Their message context: {screenshot_description}
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


async def evaluate(
    scenario: Scenario,
    replies: list[str],
    judge_client: LlmClient,
    judge_model: str,
) -> JudgeReport:
    """Score replies using an LLM judge."""
    padded = replies + ["(no reply)"] * (4 - len(replies))

    prompt = _JUDGE_PROMPT.format(
        scenario_description=scenario.description,
        screenshot_description=scenario.screenshot_description,
        direction=scenario.direction,
        reply_0=padded[0],
        reply_1=padded[1],
        reply_2=padded[2],
        reply_3=padded[3],
    )

    # Use httpx directly for judge calls — needs higher token limit than generation
    import httpx
    api_key = judge_client.api_key  # type: ignore[attr-defined]
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{judge_model}"
        f":generateContent?key={api_key}"
    )
    judge_payload = {
        "systemInstruction": {"parts": [{"text": "You are a strict dating text quality evaluator. Output valid JSON only."}]},
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 4000,
            "responseMimeType": "application/json",
        },
    }
    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, read=60.0)) as client:
        resp = await client.post(url, json=judge_payload)
        resp.raise_for_status()
        resp_data = resp.json()
        raw = resp_data["candidates"][0]["content"]["parts"][0]["text"]

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # Try extracting JSON from code block
        import re
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            data = json.loads(match.group(0))
        else:
            raise ValueError(f"Judge returned invalid JSON: {raw[:200]}")

    reply_scores = []
    for score_data in data.get("reply_scores", [])[:4]:
        reply_scores.append(ReplyScore(
            specificity=float(score_data.get("specificity", 5)),
            human_voice=float(score_data.get("human_voice", 5)),
            fork_quality=float(score_data.get("fork_quality", 5)),
            contextual_fit=float(score_data.get("contextual_fit", 5)),
            usability=float(score_data.get("usability", 5)),
            feedback=score_data.get("feedback", ""),
        ))

    return JudgeReport(
        reply_scores=reply_scores,
        overall_score=float(data.get("overall_score", 5)),
        best_reply_index=int(data.get("best_reply_index", 0)),
        worst_reply_index=int(data.get("worst_reply_index", 0)),
        improvement_notes=data.get("improvement_notes", ""),
    )
