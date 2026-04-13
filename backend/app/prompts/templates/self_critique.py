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

□ NO AI-ISMS: Scan for forbidden patterns.
  Test: Any "absolutely", "I appreciate", "What a", exclamation marks on consecutive sentences, "haha" as first word, quotes for emphasis? → replace with natural language.

All 4 replies must pass ALL checks. Fix failures before outputting."""
