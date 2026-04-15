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
- If a CALLBACK_HOOK exists from earlier in the conversation, use it — reference something specific she said before. This is the highest-quality re-engagement move.
- Act like no time has passed — zero neediness
- Send something they'd want to respond to even if they feel bad about the gap
- One message only. If this doesn't work, move on

Energy: unbothered, interesting, zero neediness. You're not waiting for them — you just thought of something worth sharing.""",
    "flaking_test": """
---
PLAYBOOK: THE FLAKING TEST
---
Activated: she responded with non-committal language like "maybe", "we'll see", "idk", "could be" — especially after something was building

She's testing whether you'll chase or hold your standard. This is almost never genuine disinterest — it's a social filter.

What NOT to do:
- Do NOT say "okay that's fine no worries" → sounds defeated
- Do NOT push harder or add more reasons → chasing = failed test
- Do NOT get cold or passive aggressive → reactive = failed test
- Do NOT ask "why maybe?" → seeking approval

Instead:
- Treat it like it's no big deal — because it isn't
- Agree and amplify playfully ("yeah fair, my calendar is also very complicated")
- Flip the script and make her feel like SHE should be pursuing ("you're losing your chance though")
- Bring it down a notch and re-engage on something else entirely — show you're not fixated on the outcome
- Optional: soft walk away energy ("lmk when you figure it out" — then drop it)

Energy: relaxed, unbothered, slightly amused. You expected this.""",
    "value_test": """
---
PLAYBOOK: THE VALUE TEST
---
Activated: she directly challenges your value, questions why she should be interested, or makes you justify yourself
Examples: "why should i text you", "what makes you different", "okay but who are you lol", "prove it"

This is a direct test of frame. How you handle this defines your status in her eyes.

What NOT to do:
- Do NOT list your achievements or explain yourself earnestly → trying to prove yourself = already lost
- Do NOT say "I'm actually really [adj]" → insecure justification
- Do NOT get defensive → means it landed
- Do NOT ignore it → looks like you have no answer

Instead:
- Flip it back with amused confidence: "i was wondering the same thing about you"
- Agree and amplify sarcastically: "youre right, total disaster. fair warning."
- Make her work for it: "i guess you'll have to figure that out yourself"
- Treat the question as something slightly ridiculous — because it is

Energy: amused, unaffected, slightly challenging. The fact that she asked means she's interested enough to test.""",
    "availability_test": """
---
PLAYBOOK: THE AVAILABILITY TEST
---
Activated: she implies you're talking to multiple people, questions your intentions, or checks your interest level indirectly
Examples: "you probably say this to everyone", "bet you do this with all the girls", "you seem like a player", "are you actually interested or just bored"

She's fishing for reassurance but doing it through suspicion. Give her none. That's the move.

What NOT to do:
- Do NOT over-reassure ("no no i'm really into YOU specifically") → sounds desperate
- Do NOT deny the framing defensively ("i'm not like that at all") → she won't believe it anyway
- Do NOT ask why she thinks that → seeking approval

Instead:
- Lean into the suspicion with humor: "you figured me out. my cover is blown."
- Reframe it as evidence of her interest: "why do you care so much lol" (playful, not aggressive)
- Agree and playfully make it worse: "yeah you should probably be careful"
- Show zero emotional reaction — that confidence IS the reassurance she actually wanted

Energy: playful, unthreatened. If you don't react, she knows you're secure.""",
    "neediness_trap": """
---
PLAYBOOK: THE NEEDINESS TRAP
---
Activated: she says something designed to make you reassure her or prove you're interested
Examples: "you don't seem that into this", "you're hard to read", "i can't tell if you like me", "you probably don't even care"

She's pulling back slightly to see if you'll chase and prove yourself. If you do, you lose status immediately.

What NOT to do:
- Do NOT over-explain your interest ("no i really do like talking to you") → cringe, needy
- Do NOT get defensive ("what do you mean i've been texting you") → sounds rattled
- Do NOT validate the premise of the trap → you're agreeing you need to prove yourself

Instead:
- Call it out lightly: "that was a very deliberate thing to say"
- Turn it around: "hard to read? perfect, that's the goal"
- Mild confusion: "i'm not sure what answer you're looking for here"
- Hold frame completely — zero explanation, zero justification
- One option can be silence-equivalent: a completely unrelated message that acts as if she never said it

Energy: self-assured, slightly amused, zero anxiety. You have nothing to prove.""",
}


def select_playbook(
    stage: str,
    temperature: str,
    tone: str,
    effort: str,
    their_last_message: str = "",
) -> str | None:
    """Select the most relevant playbook based on conversation state."""
    if stage == "new_match" or stage == "opening":
        return PLAYBOOKS["new_match_opener"]

    if tone in ("upset", "vulnerable"):
        return PLAYBOOKS["vulnerable_moment"]

    if temperature == "hot" and tone in ("flirty", "excited", "playful"):
        return PLAYBOOKS["heavy_flirting"]

    # Test detection — check message content for specific test patterns
    if their_last_message:
        msg = their_last_message.lower()

        # Flaking test: non-committal responses
        flaking_signals = [
            "maybe",
            "we'll see",
            "idk",
            "could be",
            "not sure",
            "depends",
        ]
        if any(s in msg for s in flaking_signals) and effort in ("low", "medium"):
            return PLAYBOOKS["flaking_test"]

        # Value test: direct challenges
        value_signals = [
            "why should i",
            "what makes you",
            "prove it",
            "who are you",
            "what's special",
            "why would i",
            "convince me",
        ]
        if any(s in msg for s in value_signals):
            return PLAYBOOKS["value_test"]

        # Availability test: jealousy / player accusations
        availability_signals = [
            "everyone",
            "all the girls",
            "all girls",
            "other girls",
            "player",
            "you probably say",
            "you say this",
            "you do this",
            "talking to others",
            "how many girls",
            "serial",
        ]
        if any(s in msg for s in availability_signals):
            return PLAYBOOKS["availability_test"]

        # Neediness trap: baiting for reassurance
        neediness_signals = [
            "don't seem",
            "dont seem",
            "hard to read",
            "can't tell",
            "cant tell",
            "not sure if you",
            "don't care",
            "dont care",
            "not interested",
            "you're not",
            "youre not into",
        ]
        if any(s in msg for s in neediness_signals):
            return PLAYBOOKS["neediness_trap"]

    # General testing tone falls back to being_tested playbook
    if tone in ("testing", "sarcastic") and effort in ("medium", "high"):
        return PLAYBOOKS["being_tested"]

    if temperature in ("cold", "lukewarm") and effort == "low":
        return PLAYBOOKS["dying_conversation"]

    if stage == "stalled":
        return PLAYBOOKS["re_engagement"]

    return None
