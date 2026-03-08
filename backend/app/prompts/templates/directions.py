DIRECTION_PROMPTS: dict[str, str] = {
    "quick_reply": """
══════════════════════════════════════
DIRECTION: QUICK REPLY
══════════════════════════════════════

Reply naturally. Continue the conversation in whatever direction feels right based on the vibe.

Match their energy:
- If they're playful → be playful back
- If they're serious → be genuine
- If they're flirty → flirt back at their level or slightly above
- If they're low effort → dont over-invest, be interesting instead

Don't force a direction. Just be the best version of a natural reply.""",

    "get_number": """
══════════════════════════════════════
DIRECTION: GET THEIR NUMBER
══════════════════════════════════════

Steer toward exchanging phone numbers, but ONLY if conversation temperature is warm or hot.

If temperature is lukewarm/cold → warm it up first. Don't force it into a dead convo.

Strategy — create a REASON to move off the app:
- Reference something that would be easier to share via text ("send me that playlist")
- Suggest something time-sensitive ("ill text you the details")
- Make it feel like a natural next step, not a big ask

NEVER say:
- "Can I get your number?" (too direct, too formal)
- "Want to text instead?" (no reason given)
- "We should move this off the app" (sounds like a sales pitch)

INSTEAD create a scenario where exchanging numbers is the obvious next move.""",

    "ask_out": """
══════════════════════════════════════
DIRECTION: ASK THEM OUT
══════════════════════════════════════

Suggest meeting up. Be SPECIFIC — name an activity connected to something they mentioned.

Good: "theres this ramen spot near downtown that does insane spicy miso... you free this weekend"
Bad: "we should hang out sometime"

Rules:
- If temperature is cold/lukewarm → warm it up first, don't ask out into a dead conversation
- Be specific about WHAT (activity) but flexible about WHEN
- Connect the activity to something from the conversation
- Make it low-pressure ("no pressure but" is also cringe — just make the suggestion casual)

NEVER say:
- "We should hang out sometime" (vague, never happens)
- "Would you like to go on a date?" (too formal, too much pressure)
- "I'd love to take you out" (AI language + old-fashioned)""",

    "keep_playful": """
══════════════════════════════════════
DIRECTION: KEEP IT PLAYFUL
══════════════════════════════════════

Keep the conversation fun, flirty, and light. Your job is to make both people smile at their phones.

Techniques:
- Tease them gently about something they said
- Create inside jokes from the conversation
- Playfully challenge or disagree with something
- Use absurd hypotheticals ("okay but if you could only eat one food forever...")
- Riff on their energy — if they're being silly, be silly back

This is NOT about being a comedian or trying too hard. It's about creating a fun, easy energy.

Avoid:
- Forced jokes that dont connect to the conversation
- "Haha" as a filler before every message
- Being goofy when they're being flirty (read the room)""",

    "go_deeper": """
══════════════════════════════════════
DIRECTION: GO DEEPER
══════════════════════════════════════

Move toward a more real, meaningful conversation. Ask something thoughtful that connects to what they shared.

The key is being SPECIFIC, not generic:
Bad: "Tell me more about your travels"
Good: "what made you pick japan specifically... was it the food or are you one of those studio ghibli people"

Bad: "That's really interesting, what else do you like?"
Good: "okay so hiking and cooking... are these like stress relief things or just who you are"

Rules:
- Don't just say "tell me more" — thats lazy
- Connect your question to something specific they said
- Share a small vulnerable thing about yourself to invite reciprocation
- Don't go TOO deep too fast (dont ask about childhood trauma on message 5)""",

    "change_topic": """
══════════════════════════════════════
DIRECTION: CHANGE TOPIC
══════════════════════════════════════

Pivot to something new. Use a BRIDGE from what they said to transition naturally.

Good transitions:
- "okay that reminds me..." + new topic
- "wait speaking of [thing]..." + related new topic
- "okay completely random but [interesting thing]" (owning the pivot)
- Use something from their profile you haven't talked about yet

Bad transitions:
- "anyway" (lazy, signals you're bored)
- "random question but" (overused)
- "so..." (dead energy)
- Completely ignoring what they said and asking something unrelated

The new topic should be INTERESTING — something that reveals personality or creates playful debate. Not "so what do you do for work" energy.""",
}


def get_direction_prompt(direction: str) -> str:
    return DIRECTION_PROMPTS.get(direction, DIRECTION_PROMPTS["quick_reply"])
