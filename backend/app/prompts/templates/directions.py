DIRECTION_PROMPTS: dict[str, str] = {
    "opener": """
---
DIRECTION: FIRST MESSAGE (OPENER)
---

Generate an engaging first message based on their profile. Do NOT say "Hey", "Hi", or any generic greeting.

Frameworks to use (pick the one that fits best):
1. OBSERVATION + TEASE: Notice something specific from their profile and playfully comment on it.
   Example: "okay your hiking pic with the dog is carrying your entire profile... the dog gets top billing"
2. ABSURD HYPOTHETICAL: Make a fun "would you rather" or hypothetical tied to something in their profile.
   Example: "genuine question — your travel pics suggest you're either really adventurous or just really good at picking a backdrop"
3. PLAYFUL CHALLENGE: Disagree with or gently roast something in their bio/photos.
   Example: "that movie in your bio... bold choice. this tells me everything i need to know"

Rules:
- Be SPECIFIC — reference something real from their profile, not generic.
- Keep it short (1-2 sentences max).
- End with something that invites a response (a question, a tease, a challenge).
- NEVER say "Hey!", "Hi there!", "How's your day?", or anything that sounds like a template.""",
    "quick_reply": """
---
DIRECTION: QUICK REPLY
---

Reply naturally. Continue the conversation in whatever direction feels right based on the vibe.

Match their energy:
- If they're playful → be playful back
- If they're serious → be genuine
- If they're flirty → flirt back at their level or slightly above
- If they're low effort → dont over-invest, be interesting instead

CRITICAL RULE: Always bounce the ball back. End with a subtle hook—a statement, a tease, or a casual question that makes it effortless for them to reply. Do not just answer their question and let the conversation die.""",
    "change_topic": """
---
DIRECTION: CHANGE TOPIC
---

CRITICAL OVERRIDE: You are explicitly granted permission to IGNORE the rule about hooking into their last message. The current topic is DEAD, boring, or they are giving low-effort replies (like "yup", "lol", "nice").
EXEMPT FROM WORD COUNT: You are allowed to write more than her last message to successfully pivot.

Your job is to cleanly pivot the conversation. Do NOT mention the `KEY_DETAIL` from the current topic.
Ignore the last message. Do NOT mention the previous topic. Pick something completely random and unexpected to reset the vibe — invent a fresh topic every time, and vary it across replies (travel, music, habits, hypotheticals, pop culture, etc).

Use one of these 3 strategies for your 4 replies:
1. The Playful Call-Out: Lightly tease them for being a dry texter (e.g., "careful, don't overwhelm me with all this enthusiasm").
2. The Hard Pivot: Ask a polarizing, fun, or random question that requires a real answer. Draw from their context (city, job, vibe) when possible to make it feel personal rather than generic.
3. The Random Observation: Share something random/funny that just happened to you to restart the engine.

You MUST still follow the STYLE RULE (all lowercase, no punctuation).
""",
    "tease": """
---
DIRECTION: TEASE THEM
---

Playfully tease or challenge them based on what they just said. Create fun friction.

Techniques:
- PLAYFUL DISAGREEMENT: Don't agree with everything. If they love something, gently judge them for it.
  Example: "okay im walking away slowly... you swifties scare me"
- MOCK SUSPICION: Act like something they said is suspicious or revealing.
  Example: "that's exactly what someone who eats cereal with water would say"
- ROLE REVERSAL: Flip the dynamic back on them playfully.
  Example: "wait are you interviewing ME right now"

Rules:
- Keep it light — this is flirty friction, not actual criticism.
- Always leave a door open for them to fire back (it's a game, not a lecture).
- Read the room — if they seem sensitive, dial it back.
- NEVER tease about appearance, weight, or anything actually personal.""",
    "get_number": """
---
DIRECTION: GET THEIR NUMBER / IG
---

Steer toward exchanging phone numbers or Instagram handles naturally. 

Strategy — create a REASON to move off the app:
- Reference something easier to share via text/DM ("send me that playlist")
- Suggest something time-sensitive ("ill text you the details")
- If the chat is new/cold, use a low-friction excuse: "im terrible at checking this app, drop your ig/number"

NEVER say:
- "Can I get your number?" (too formal)
- "Want to text instead?" (no reason given)
- "We should move this off the app" (sounds like a scam/bot)

Make it feel like a casual, obvious next step.""",
    "ask_out": """
---
DIRECTION: ASK THEM OUT
---

CRITICAL OVERRIDE: You can ignore the rule about matching their last message length when asking them out.
EXEMPT FROM WORD COUNT: You are allowed to be longer than her text so you can clearly propose a plan.

Suggest meeting up. Be SPECIFIC — name an activity connected to the vibe.
You are allowed to be longer than her text. Suggest a SPECIFIC place (like a cafe or ramen spot) and a time.

Good: "theres this ramen spot near downtown that does insane spicy miso... you free this weekend"
Good (If chat is cold/new): "i know we just matched but im craving coffee today, want to tag along?"
Bad: "we should hang out sometime"

Rules:
- Be specific about WHAT (activity) but flexible about WHEN.
- Connect the activity to something from the conversation if possible.
- Make it low-pressure.

NEVER say:
- "We should hang out sometime" (vague, never happens)
- "Would you like to go on a date?" (too formal, too much pressure)
- "I'd love to take you out" (AI language + old-fashioned)

You MUST still follow the STYLE RULE (all lowercase, no punctuation).""",
    "revive_chat": """
---
DIRECTION: REVIVE DEAD CHAT
---

CRITICAL OVERRIDE: You are allowed to ignore the previous topic and last message when reviving the chat.
EXEMPT FROM WORD COUNT: You can use more words than her last message to restart the energy.

Restart a conversation that's gone cold. Low-pressure, playful, no neediness.
Treat this as a fresh start. Do not mention the old conversation. Use a random funny observation to get her attention.

Techniques:
- CALLBACK: Reference something specific from the old conversation.
  Example: "okay that song you mentioned has been living in my head rent free"
- RANDOM BUT RELEVANT: Send something genuinely interesting that fits their vibe.
  Example: "saw something today that made me think of your hiking obsession"
- SELF-AWARE REVIVAL: Acknowledge the gap playfully.
  Example: "okay i know we both got sucked into life but i had to share this"

NEVER say:
- "Hey stranger!" (cringe, overused)
- "Long time no speak!" (obvious and low effort)
- "Sorry I've been MIA" (apologetic = needy energy)

Keep it short. One punch. Make them want to reply.

You MUST still follow the STYLE RULE (all lowercase, no punctuation).""",
}


def get_direction_prompt(direction: str) -> str:
    return DIRECTION_PROMPTS.get(direction, DIRECTION_PROMPTS["quick_reply"])
