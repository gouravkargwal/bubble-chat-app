"""
Deterministic post-processing for reply validation and style enforcement.

- validate_and_fix_replies: ensures exactly 4 replies with exactly 1 recommended
- post_process_replies: strips punctuation, forces lowercase (runs after auditor approves)

These run in code with zero latency cost — no LLM calls.
"""

import structlog

from agent.state import WriterOutput, ReplyOption, StrategyLabel

logger = structlog.get_logger(__name__)

REQUIRED_REPLY_COUNT = 4


def validate_and_fix_replies(gen_out: "GeneratorOutput") -> "GeneratorOutput":  # type: ignore[name-defined]
    """Ensure exactly 4 replies with exactly 1 recommended. Backfill if short."""
    replies = list(gen_out.replies)

    # Backfill if fewer than 4 replies
    while len(replies) < REQUIRED_REPLY_COUNT:
        logger.warning("generator_backfill_reply", current_count=len(replies))
        # Clone the last reply with a different label as a fallback
        if replies:
            last = replies[-1]
            fallback_labels: list[StrategyLabel] = [
                "PUSH-PULL",
                "FRAME CONTROL",
                "SOFT CLOSE",
                "VALUE ANCHOR",
                "PATTERN INTERRUPT",
            ]
            used_labels = {r.strategy_label for r in replies}
            unused = [l for l in fallback_labels if l not in used_labels]
            label = unused[0] if unused else "PATTERN INTERRUPT"
            replies.append(
                ReplyOption(
                    text=last.text,
                    strategy_label=label,
                    is_recommended=False,
                    coach_reasoning="(auto-generated fallback)",
                )
            )
        else:
            break  # No replies at all — can't backfill from nothing

    # Truncate if more than 4
    replies = replies[:REQUIRED_REPLY_COUNT]

    # Ensure exactly 1 recommended
    recommended_count = sum(1 for r in replies if r.is_recommended)
    if recommended_count == 0 and replies:
        replies[0] = replies[0].model_copy(update={"is_recommended": True})
    elif recommended_count > 1:
        seen_first = False
        for i, r in enumerate(replies):
            if r.is_recommended:
                if seen_first:
                    replies[i] = r.model_copy(update={"is_recommended": False})
                else:
                    seen_first = True

    return gen_out.model_copy(update={"replies": replies})


def post_process_replies(drafts: WriterOutput) -> WriterOutput:
    """
    Deterministic mechanical fixes applied after auditor approval.
    Zero latency cost, 100% enforcement of style rules.
    """
    fixed_replies = []
    for r in drafts.replies:
        text = r.text
        # Strip forbidden punctuation
        for ch in ["'", ",", ".", "!", "?", '"', ";"]:
            text = text.replace(ch, "")
        # Force lowercase
        text = text.lower().strip()
        # Collapse double spaces from punctuation removal
        while "  " in text:
            text = text.replace("  ", " ")
        fixed_replies.append(r.model_copy(update={"text": text}))
    return WriterOutput(replies=fixed_replies)
