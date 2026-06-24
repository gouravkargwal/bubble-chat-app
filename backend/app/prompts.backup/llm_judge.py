"""
LLM-as-judge prompts for evaluating reply quality.

The judge uses Groq (Llama 3.3 70B) to score reply quality independently
of the generator, avoiding same-model bias.
"""

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
