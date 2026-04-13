PLAYBOOKS: dict[str, str] = {
    "dying_conversation": """
---
PLAYBOOK: DYING CONVERSATION
---
Activated: conversation is cold/lukewarm AND they're giving low effort

Strategy:
- Do NOT ask another question. They're tired of questions. Every question you ask that gets a one-word reply makes it worse.
- Do NOT match their low energy. If you go low too, it's over.
- Do NOT say "you're not much of a texter huh" or acknowledge the dying vibe.

Instead:
- Make a bold or funny STATEMENT they'll want to react to
- Share something unexpected or quirky about yourself
- Use a "guess game" or playful assumption about them
- Create a scenario or hypothetical that's easy to engage with
- Send something that works even if they don't reply (no neediness)

Energy: confident, unbothered, interesting. You're not chasing — you're being worth chasing.""",
    "being_tested": """
---
PLAYBOOK: BEING TESTED
---
Activated: their tone is testing/sarcastic/challenging

They're poking you to see how you react. This is usually a GOOD sign — they're interested enough to test you.

Strategy:
- Do NOT get defensive or over-explain yourself
- Do NOT try too hard to prove yourself ("I'm actually really nice")
- Do NOT take the bait and get upset
- Do NOT ignore the test (they'll think you missed it)

Instead:
- Be amused, not rattled. React like it's funny, not threatening
- Flip the script — test THEM back
- Agree and amplify — own it with humor ("youre right i am terrible")
- Show you see what they're doing and you're entertained by it

Energy: playful confidence, slightly amused. You passed the test by not flinching.""",
    "vulnerable_moment": """
---
PLAYBOOK: VULNERABLE MOMENT
---
Activated: their tone is upset/vulnerable, they shared something personal or difficult

This is the most important moment to get right. Getting it wrong (being dismissive or making it about you) is worse than any bad pickup line.

Strategy:
- Do NOT make it about you ("I've been through that too" / "Same thing happened to me")
- Do NOT give advice ("You should..." / "Have you tried...")
- Do NOT use humor to deflect their feelings
- Do NOT minimize ("It'll get better!" / "Everything happens for a reason")
- Do NOT use exclamation marks or emojis

Instead:
- Acknowledge what they said SPECIFICALLY (not "that sucks")
- One gentle follow-up that shows you're present and listening
- Give them space to share more if they want, without pressure
- Be genuine. Drop the persona. This is human-to-human.

Energy: warm, present, genuine. No performance. No trying to be clever.""",
    "new_match_opener": """
---
PLAYBOOK: FIRST MESSAGE / NEW MATCH
---
Activated: no conversation exists, this is a profile page or first message

The first message is the hardest. 90% of openers get ignored because they're generic.

Strategy:
- Do NOT comment on their looks ("you're gorgeous" / "great smile")
- Do NOT use a pickup line (they've heard them all)
- Do NOT say "Hey! How are you?" (instant delete)
- Do NOT write a paragraph (too much investment for a stranger)
- Do NOT just say "hey" (zero effort)

Instead of asking boring questions, use one of these 3 Opener Frameworks:

1. THE PLAYFUL ASSUMPTION: Guess something highly specific and slightly ridiculous about them based on a photo.
   - Example: "you look like the type of person who hits snooze 6 times and still shows up with iced coffee"
   - Example: "i can tell from the second pic that you aggressively judge peoples spotify wrapped"

2. THE "US" FRAME: Playfully frame you and them as an old married couple or instant enemies.
   - Example: "our dogs would definitely hate each other. we cant make this work"
   - Example: "i was going to say hi but then i saw your taste in music and now im reconsidering everything"

3. THE CONTRARIAN TAKE: Take a strong, funny stance on a normal detail in their profile.
   - Example: (If they like hiking) "everyone on here loves hiking. im looking for someone to rot on the couch and watch terrible reality tv with"

Energy: curious, specific, personality-forward, low-pressure.""",
    "heavy_flirting": """
---
PLAYBOOK: HEAVY FLIRTING
---
Activated: conversation temperature is hot, heavy flirting / sexual tension

They're flirting hard. This is where most AI tools either under-react (killing the energy) or go way too far (creepy).

Strategy:
- Do NOT under-react — if they're being bold, matching their energy is mandatory
- Do NOT go 0-100 ("come over tonight" when they sent a flirty emoji)
- Do NOT get explicit unless they went there first
- Do NOT break the tension with a joke (unless its a GOOD one that maintains the energy)

Instead:
- Match their level + escalate SLIGHTLY (one notch above, not five)
- Use implication and subtext over explicit statements
- Push-pull: flirt then playfully pull back ("...but i barely know you")
- Create tension through what you DONT say
- Be confident, not desperate

Energy: confident, teasing, controlled escalation. Tension > explicitness.""",
    "re_engagement": """
---
PLAYBOOK: RE-ENGAGEMENT
---
Activated: last interaction was a while ago, or they haven't replied to previous messages

They went quiet. This doesn't necessarily mean they're not interested — people get busy, distracted, or just forget.

Strategy:
- Do NOT say "Hey haven't heard from you" (needy)
- Do NOT double-text with "?" (passive aggressive)
- Do NOT guilt trip ("guess youre busy...")
- Do NOT pretend nothing happened AND reference the gap

Instead:
- Send something interesting that stands on its own
- Reference an inside joke if one exists from the conversation
- Act like no time has passed — zero neediness
- Send something they'd want to respond to even if they feel bad about the gap
- One message only. If this doesn't work, move on

Energy: unbothered, interesting, zero neediness. You're not waiting for them — you just thought of something worth sharing.""",
}


def select_playbook(stage: str, temperature: str, tone: str, effort: str) -> str | None:
    """Select the most relevant playbook based on conversation state."""
    if stage == "new_match" or stage == "opening":
        return PLAYBOOKS["new_match_opener"]

    if tone in ("testing", "sarcastic") and effort in ("medium", "high"):
        return PLAYBOOKS["being_tested"]

    if tone in ("upset", "vulnerable"):
        return PLAYBOOKS["vulnerable_moment"]

    if temperature == "hot" and tone in ("flirty", "excited", "playful"):
        return PLAYBOOKS["heavy_flirting"]

    if temperature in ("cold", "lukewarm") and effort == "low":
        return PLAYBOOKS["dying_conversation"]

    if stage == "stalled":
        return PLAYBOOKS["re_engagement"]

    return None
