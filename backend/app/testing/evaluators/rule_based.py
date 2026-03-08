"""Deterministic quality checks — fast, free, no LLM needed."""

import re
from dataclasses import dataclass, field

from app.domain.models import ParsedLlmResponse
from app.testing.scenarios.dataset import QualityCriteria


@dataclass
class CheckResult:
    name: str
    passed: bool
    score: float  # 0.0 to 1.0
    details: str = ""


@dataclass
class RuleReport:
    overall_score: float
    checks: list[CheckResult] = field(default_factory=list)
    reply_count: int = 0
    ai_ism_count: int = 0
    fork_rate: float = 0.0

    @property
    def passed(self) -> bool:
        return self.overall_score >= 0.6


# AI-ism patterns — if any of these appear in a reply, it's a red flag
_AI_ISMS = [
    r"I'd love to",
    r"That's (?:so |really )?amazing",
    r"That sounds (?:amazing|great|wonderful|incredible|lovely)",
    r"\babsolutely\b",
    r"I appreciate",
    r"What a \w+!",
    r"I totally (?:get|understand|agree)",
    r"That being said",
    r"I must say",
    r"I have to say",
    r"It seems like",
    r"In all honesty",
    r"Truth be told",
    r"To be honest",
    r"—",  # em dash
    r";(?!\))",  # semicolon (but not ;) wink emoji)
]

# Boring pattern phrases
_BORING_PATTERNS = [
    "how was your day",
    "tell me more about that",
    "we should hang out sometime",
    "that's cool",
    "same!",
    "nice!",
    "interesting",
    "what about you?",
]

# Fork indicators — at least one should be present
_FORK_INDICATORS = [
    r"\?",  # question mark
    r"\b(?:bet|prove|dare|try)\b",  # challenge words
    r"\.\.\.",  # ellipsis (hooks, trailing thoughts)
    r"\b(?:you seem|you look like|you strike me|youre (?:either|probably|definitely))\b",  # assumptions
    r"\b(?:or are you|or is it|or do you)\b",  # false dilemmas
    r"\b(?:unless|but only if)\b",  # conditionals
]


def evaluate(replies: list[str], criteria: QualityCriteria) -> RuleReport:
    """Run all deterministic quality checks on a set of replies."""
    checks: list[CheckResult] = []
    ai_ism_total = 0

    # Check 1: Reply count
    reply_count = len(replies)
    checks.append(CheckResult(
        name="reply_count",
        passed=reply_count == 4,
        score=1.0 if reply_count == 4 else 0.5 if reply_count >= 2 else 0.0,
        details=f"{reply_count} replies (expected 4)",
    ))

    # Check 2: AI-ism detection (per reply)
    for i, reply in enumerate(replies):
        isms_found = []
        for pattern in _AI_ISMS:
            if re.search(pattern, reply, re.IGNORECASE):
                isms_found.append(pattern)
        ai_ism_total += len(isms_found)
        if isms_found:
            checks.append(CheckResult(
                name=f"ai_isms_reply_{i}",
                passed=False,
                score=0.0,
                details=f"Reply {i+1} has AI-isms: {isms_found[:3]}",
            ))

    ai_ism_score = max(0.0, 1.0 - (ai_ism_total * 0.2))
    checks.append(CheckResult(
        name="ai_isms_total",
        passed=ai_ism_total == 0,
        score=ai_ism_score,
        details=f"{ai_ism_total} AI-isms found across all replies",
    ))

    # Check 3: Length limits
    length_violations = 0
    for i, reply in enumerate(replies):
        if len(reply) > criteria.max_length_chars:
            length_violations += 1
            checks.append(CheckResult(
                name=f"length_reply_{i}",
                passed=False,
                score=0.5,
                details=f"Reply {i+1}: {len(reply)} chars (max {criteria.max_length_chars})",
            ))
        if len(reply) < 10:
            length_violations += 1
            checks.append(CheckResult(
                name=f"length_too_short_{i}",
                passed=False,
                score=0.0,
                details=f"Reply {i+1}: only {len(reply)} chars (too short)",
            ))
    length_score = max(0.0, 1.0 - (length_violations * 0.25))

    # Check 4: Fork detection
    fork_count = 0
    for reply in replies:
        has_fork = any(re.search(p, reply, re.IGNORECASE) for p in _FORK_INDICATORS)
        if has_fork:
            fork_count += 1
    fork_rate = fork_count / max(len(replies), 1)
    if criteria.must_have_fork:
        checks.append(CheckResult(
            name="fork_presence",
            passed=fork_rate >= 0.75,
            score=fork_rate,
            details=f"{fork_count}/{len(replies)} replies have forks ({fork_rate:.0%})",
        ))

    # Check 5: Forbidden patterns
    forbidden_found = 0
    for i, reply in enumerate(replies):
        reply_lower = reply.lower()
        for pattern in criteria.forbidden_patterns:
            if pattern.lower() in reply_lower:
                forbidden_found += 1
                checks.append(CheckResult(
                    name=f"forbidden_{i}",
                    passed=False,
                    score=0.0,
                    details=f"Reply {i+1} contains forbidden: '{pattern}'",
                ))
    forbidden_score = max(0.0, 1.0 - (forbidden_found * 0.2))

    # Check 6: Must-reference check
    reference_score = 1.0
    if criteria.must_reference:
        found_refs = set()
        all_text = " ".join(replies).lower()
        for ref in criteria.must_reference:
            if ref.lower() in all_text:
                found_refs.add(ref)
        reference_score = len(found_refs) / len(criteria.must_reference)
        checks.append(CheckResult(
            name="must_reference",
            passed=reference_score >= 0.5,
            score=reference_score,
            details=f"Referenced {len(found_refs)}/{len(criteria.must_reference)}: {found_refs}",
        ))

    # Check 7: Structural diversity (word overlap between replies)
    diversity_score = 1.0
    if len(replies) >= 2:
        overlaps = []
        for i in range(len(replies)):
            for j in range(i + 1, len(replies)):
                words_i = set(replies[i].lower().split())
                words_j = set(replies[j].lower().split())
                union = words_i | words_j
                if union:
                    overlap = len(words_i & words_j) / len(union)
                    overlaps.append(overlap)
                    if overlap > 0.5:
                        checks.append(CheckResult(
                            name=f"diversity_{i}_{j}",
                            passed=False,
                            score=1.0 - overlap,
                            details=f"Replies {i+1} and {j+1} too similar ({overlap:.0%} overlap)",
                        ))
        if overlaps:
            avg_overlap = sum(overlaps) / len(overlaps)
            diversity_score = max(0.0, 1.0 - avg_overlap)

    # Check 8: Boring patterns
    boring_count = 0
    for reply in replies:
        reply_lower = reply.lower()
        for boring in _BORING_PATTERNS:
            if boring in reply_lower:
                boring_count += 1
    boring_score = max(0.0, 1.0 - (boring_count * 0.2))

    # Check 9: No-question check (if required)
    if criteria.must_not_ask_question:
        question_replies = sum(1 for r in replies if "?" in r)
        checks.append(CheckResult(
            name="no_questions",
            passed=question_replies == 0,
            score=1.0 if question_replies == 0 else max(0.0, 1.0 - question_replies * 0.3),
            details=f"{question_replies} replies contain questions",
        ))

    # Calculate overall score (weighted average)
    weights = {
        "ai_isms": 0.20,
        "length": 0.10,
        "forks": 0.20,
        "forbidden": 0.15,
        "reference": 0.15,
        "diversity": 0.10,
        "boring": 0.10,
    }
    overall = (
        ai_ism_score * weights["ai_isms"]
        + length_score * weights["length"]
        + fork_rate * weights["forks"]
        + forbidden_score * weights["forbidden"]
        + reference_score * weights["reference"]
        + diversity_score * weights["diversity"]
        + boring_score * weights["boring"]
    )

    return RuleReport(
        overall_score=overall,
        checks=checks,
        reply_count=reply_count,
        ai_ism_count=ai_ism_total,
        fork_rate=fork_rate,
    )
