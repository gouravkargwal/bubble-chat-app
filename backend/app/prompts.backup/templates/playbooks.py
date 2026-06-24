PLAYBOOKS: dict[str, str] = {
    "dying_conversation": """
SITUATION: DYING CONVERSATION (cold/lukewarm + low effort)
DON'T: ask questions, match low energy, acknowledge dying vibe, be confrontational ("you need a better excuse").
DO: bold statement, unexpected observation, playful assumption grounded in something specific from her last message — even one word is enough to build on. Zero neediness, zero pressure.""",
    "being_tested": """
SITUATION: BEING TESTED (testing/sarcastic tone)
DON'T: get defensive, over-explain, take the bait, ignore the test.
DO: be amused not rattled — flip the script, agree-and-amplify ("youre right i am terrible"), show you see it and find it entertaining.""",
    "vulnerable_moment": """
SITUATION: VULNERABLE MOMENT (upset/vulnerable tone)
DON'T: make it about you, give advice ("you should..."), use humor to deflect, minimize ("it'll get better").
DO: acknowledge SPECIFICALLY what they said (name the actual situation). Drop the persona — human-to-human.
FORK RULE: Don't write 4 pure-validation dead-ends. Mix in >=1 gentle forward hook — a soft question about what they need, an observation about their strength, or a light redirect. "that sounds hard" × 4 fails fork quality.""",
    "new_match_opener": """
SITUATION: NEW MATCH / FIRST MESSAGE
DON'T: comment on looks, use pickup lines, say "hey how are you", write a paragraph, just say "hey".
DO — pick one framework:
1. PLAYFUL ASSUMPTION: guess something specific+ridiculous ("you look like the type who hits snooze 6 times and still shows up with iced coffee")
2. US FRAME: instant enemies or old couple ("i was going to say hi but then i saw your taste in music and now im reconsidering")
3. CONTRARIAN TAKE: strong funny stance on a profile detail ("everyone on here loves hiking. im looking for someone to rot on the couch with")""",
    "heavy_flirting": """
SITUATION: HEAVY FLIRTING (hot temperature + flirty tone)
DON'T: under-react, go 0-100, get explicit unless they did first, kill tension with a bad joke.
DO: match their level + escalate ONE notch. Implication > explicit. Push-pull: flirt then pull back ("but i barely know you"). Tension > explicitness.""",
    "re_engagement": """
SITUATION: RE-ENGAGEMENT (stalled / no reply)
FORK based on who broke the silence:
IF THEY texted back first (e.g. "sorry been mia", "hey life got chaotic"): They made an effort — don't punish it with coldness. Light tease that resets the energy ("chaotic life = finally got your act together or did it get worse"). Match their warm tone + move forward. DON'T guilt trip.
IF YOU are re-engaging (no reply from them): Send something interesting that stands alone — inside joke callback or fresh angle. Act like no time passed. DON'T say "haven't heard from you", double-text "?", guilt trip, or make replies about yourself.""",
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
