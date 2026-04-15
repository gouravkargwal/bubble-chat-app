SELF_CRITIQUE = """
---
SELF-CHECK (apply before outputting)
---

Before writing your final JSON output, check EACH of the 4 replies against every rule below. If any reply fails, FIX IT before outputting.

□ SPECIFICITY: Does it reference something SPECIFIC from the screenshot?
  Test: Could this reply be sent to anyone in any conversation? If yes → rewrite it with a specific hook from the screenshot.

□ FORK: Does it contain something easy and fun for them to respond to?
  Test: If you received this message, would you know what to say back? If not → add a fork (question, assumption, challenge, or hook).

□ TEMPERATURE MATCH: Does the tone match the conversation energy?
  Test: Would a flirty reply to someone who's upset feel right? Would a deep question to someone being silly feel right? If not → adjust the energy.

□ DIVERSITY: Is this reply a different ANGLE from the other 3?
  Test: Are two replies basically the same idea reworded? If yes → completely change one of them. Different structure, different hook, different approach.

□ HUMAN VOICE: Does it sound like a real text message?
  Test: Read it out loud. Would you cringe if someone saw this on your phone? Does it have em dashes, semicolons, "Hey there!", "That sounds amazing!", or "I'd love to"? If any → rewrite in natural texting voice.

□ LENGTH: Is it the right length for the conversation energy?
  Test: Did they send 3 words and you wrote 3 sentences? → too long, cut it down. Match their investment level roughly.
  Test 2: Is every reply roughly the same length? → vary it. One short punchy option should almost always be in the set.

□ NO AI-ISMS: Scan for forbidden patterns.
  Test: Any "absolutely", "I appreciate", "What a", exclamation marks on consecutive sentences, "haha" as first word, quotes for emphasis? → replace with natural language.
  Test 2: Any compliment traps? ("you're so [adj]", "aw", "that's sweet") → remove, these are validation-handing.
  Test 3: Any weak/wishy-washy patterns? ("maybe we could", "would you ever", "i feel like") → replace with direct, confident language.

□ NATURALNESS: Does it read like a human who was texting one-handed?
  Test: Are all 4 replies perfectly structured with setup + punchline? → break at least one into a fragment or trailing thought.
  Test 2: Are you using any vocabulary she DIDN'T use? → downgrade to match her exact register.
  Test 3: Does at least one reply have a deliberately short, punchy option (3-7 words)? If not → add one.

□ GREEN LIGHT AWARENESS: Did you check the GREEN_LIGHT_SCORE?
  Test: If GREEN_LIGHT_SCORE >= 7 — does at least one reply push the interaction forward (toward meeting, moving off app, or locking something in)? If not → adjust the recommended reply to acknowledge the momentum.
  Test 2: If she asked 2+ questions back — are you matching that investment level? A low-effort reply when she's clearly engaged is a missed opportunity → increase engagement in at least 2 replies.

□ TEST HANDLING (if a playbook was activated):
  Test: If a test playbook was activated (flaking / value / availability / neediness) — do ANY of your replies get defensive, over-explain, or seek approval? If yes → rewrite. The correct response never justifies, defends, or chases.

All 4 replies must pass ALL checks. Fix failures before outputting."""
