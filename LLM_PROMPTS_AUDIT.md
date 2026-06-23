# Complete LLM/AI Prompts Audit - Bubble Chat App Backend

**Last Updated:** 2026-06-24  
**Scope:** All LLM prompts, system instructions, and AI model integrations in the backend codebase

---

## Executive Summary

The backend uses **Gemini (Google Generative AI)** as the primary LLM provider, with **Groq (Llama 3.3 70B)** for evaluation and optional A/B testing. Prompts are highly specialized for dating coach scenarios and dating profile optimization.

**Total Prompt Files Found:** 10+ prompt definitions across multiple services  
**LLM Integration Points:** 4 main Gemini calls + 1 Groq evaluation

---

## 1. GENERATOR NODE SYSTEM PROMPT

**File:** `backend/agent/nodes_v2/_generator.py:85-142`  
**Provider:** Google Gemini (settings.gemini_model)  
**Temperature:** Dynamic (0.50 - 0.85, calculated per direction/context)  
**Purpose:** Generate 4 dating reply suggestions with strategy reasoning

### Core Principle
Dating text coach with 3-phase approach: strategy → write → self-check

### Key Rules

**RIZZ BAR (applies to all directions EXCEPT de_escalate/go_deeper):**
Every reply must carry a SPIKE — at least one of:
- Bold playful assumption about something she DOES (banned: verdicts on who she IS)
- Light disqualification/challenge
- Cocky, unbothered frame
- Real stance/hot take (pick a side)

**SOUND HUMAN NOT AI:**
- SHORT IS A RULE: Aim 6-12 words (~12 word hard cap: 18 words auto-fails)
- No AI scaffolds (soft openers like "you seem like the type")
- Fragments win; grammatically-complete = AI tell
- No generic crutches (zombie apocalypse, zodiac reads)
- ANCHOR TO HER actual words/photos, not clever lines for anyone

**PHASE 1: STRATEGY**
- Read user_last_move FIRST (if USER's reply was weak, don't mock HER)
- LIVE MOMENT > profile facts (extend/flip what she just engaged with)
- Inbound image handling: selfie → warmth + escalation; object/scene → react to thing, not her looks
- Double-text: Don't re-answer her — build on user's last text

**PHASE 2: WRITE**
- Format: no punctuation, lowercase
- Diversity: 4 replies = 4 DIFFERENT specific hooks
- Specificity: >=2 must embed her exact words
- Freshness: Don't paraphrase last_ai_replies_shown
- No self-pivot (but frame-flips allowed: making HER qualify is banter)

**PHASE 3: SELF-CHECK**
- Re-scan each reply: SPIKE + SHORT + anchored + no scaffold + no character verdicts
- Label accuracy: strategy_label MUST match text (A/B question = FRAME_CONTROL, not HONEST FRAME)
- Banned (zero tolerance): therapy phrases ("i appreciate/hear/respect"), dead openers ("hey/haha"), generic questions

---

## 2. AUDITOR NODE SYSTEM PROMPT

**File:** `backend/agent/nodes_v2/_auditor.py:77-108`  
**Provider:** Google Gemini  
**Temperature:** 0 (deterministic judgment)  
**Purpose:** Quality evaluation of generated replies; routes back to generator if any fail

### Core Verdicts (Per-Reply)

**FAIL for:**
1. Context/Dialect: Ignores verbatim_last_message, misses custom_hint, wrong dialect
2. Tone fit + safety: Heavy teasing toward guarded/vulnerable person; over-eager toward cold person
3. Direction violations: e.g., get_number without off-app move, ask_out <2 concrete asks
4. Persona labeling: FAIL identity verdicts ("influencer energy"), PASS behavior assumptions ("type who...")
5. Therapy phrases (automatic): "i appreciate", "i hear you", "that sounds hard", "thank you for sharing", etc.
6. Cringe/Generic: Motivational quotes, fate/destiny openers, recycled banned example lines
7. Non-anchored generic crutch: Zombie apocalypse, desert island, zodiac reads
8. Flatness/no-spike: Pure observation, neutral interview question, validation, small talk
9. Structure: 2+ questions, dead-end (no fork), wrong label

### Deterministic Length Backstop
- Hard cap: 18 words (soft target: ~12 words)
- >18 words auto-fails: "Cut to <=12: fire the spike and stop"

### Overall Pass Rule
- ALL 4 replies must pass (no partial passes)
- If any fail → routes back to generator with specific rewrite feedback

---

## 3. VISION NODE SYSTEM PROMPT (OCR + Personality Analysis)

**File:** `backend/app/api/v1/vision_v2.py:98-258`  
**Provider:** Google Gemini  
**Purpose:** Extract text from dating profiles/chats + analyze personality

### STEP 1: VALIDATION
- is_valid_chat (boolean): True only if valid chat OR dating app profile
- bouncer_reason: Brief explanation
- Stop here if invalid

### STEP 2: OCR EXTRACTION (Chat Sender Identification)

**Critical Rule: Avatar is the primary anchor (theme-independent)**
- Ignore color and alignment (theme-dependent, unreliable)
- Fallback signals (in order):
  1. Delivery indicators (Sent, Read, ✓✓) = USER
  2. Header name = ALWAYS "them"
  3. Text input bar = USER
  4. Bubble alignment (RIGHT=user, LEFT=them) = LAST RESORT

**Reply/Quoted Bubbles:**
- Outer bubble sender = avatar anchor (not the quoted text)
- actual_new_message ≠ quoted_context (never identical)

**Per-Bubble Output:**
- sender: "user" or "them"
- actual_new_message: NEW text typed
- quoted_context: Faded reply preview (null if no reply)
- is_reply: true/false

### STEP 3A: CHAT MODE (most directions)

**Output Fields:**
- key_detail: SINGLE strongest hook
- their_last_message: Short paraphrase (what she caught on to + how reacting)
- their_tone: guarded | neutral | warm
- their_effort: low | medium | high
- conversation_temperature: cold | lukewarm | warm | hot
- stage: new_match | opening | early_talking | building_chemistry | deep_connection | relationship | stalled | argument
- durable_facts: 0-5 atomic facts worth remembering
- inbound_image: selfie_of_her | object_or_scene | none
- personality dimensions: warmth, playfulness, engagement, traditionalism, intent (each: discrete values)
- archetype_reasoning: 2-3 sentences citing actual evidence
- user_last_move: Was USER's last reply high/low-effort? Is her tone likely a reaction?
- top_hooks: Exactly THREE distinct hooks from THIS chat turn

### STEP 3B: PROFILE BUFFET MODE (direction="opener")

- top_hooks: empty list (profile mode doesn't use chat turn hooks)
- Treat ALL screenshots as one merged profile (not chronological)
- photo_persona: 1-3 words (rebel/edgy, soft romantic, influencer-polished, etc.)
- key_detail: Pick MOST interesting hook ANYWHERE (not just last line)
- their_last_message: 1-2 sentence holistic profile vibe (NOT paraphrase of one line)

**Visual Hooks Guidance (Opener Only):**
- NOT neutral descriptions ("wearing a red dress")
- INSTEAD: Opinionated observations ("wearing a bow tie blouse in hotel lobby mirror selfie")
- Funny > aesthetic, Specific > generic
- 3-4 hooks that would TEASE about or raise questions

**Dialect Default Rule (Hinglish Exception):**
- If "MOTHER TONGUE: Hindi" visible → set HINGLISH
- Override to ENGLISH only if: SUBSTANTIAL free-text + clearly formal English + ZERO Hindi
- If mostly structured fields (zodiac, height, diet) → KEEP HINGLISH

---

## 4. PROFILE AUDITOR SYSTEM PROMPT (Photo Scoring)

**File:** `backend/app/services/profile_auditor_service.py:28-59`  
**Provider:** Google Gemini (vision_generate)  
**Temperature:** 0.0 (deterministic)  
**Purpose:** Score dating profile photos 1-10 (brutal, honest feedback)

### Scoring Philosophy
- BASELINE: Start at 3-4/10; higher scores must be earned
- GOD TIER EXCEPTION: Professional lighting + sharp focus + charismatic + fashion + social proof → 8/10, 9/10, 10/10
- REQUIRED VOCABULARY:
  - Weak: cringe, try-hard, lazy, awkward, unflattering
  - Elite (9/10, 10/10): magnetic, high-status, undeniable, lethal, main-character energy

### Strict Ceilings
- MAX 2/10: Bathroom/gym/elevator mirror, messy rooms
- MAX 3/10: Hiding face, blurry/pixelated
- MAX 4/10: Car/bed selfies, stiff headshots
- MAX 5/10: Group shots where identity unclear in <1 second
- PASS: Only 8+ count as passed

### Scale
- 1-3: Immediate Left Swipe (low status, cringe, lazy)
- 4-6: "Friend Zone" (invisible on dating apps)
- 7-8: Solid (clear face, lifestyle, effort)
- 9-10: Elite (professional, magnetic, social proof)

### Output Fields per Photo
- photo_id: "photo_1", "photo_2", etc.
- score: 1-10
- brutal_feedback: Explain why fails (roast) OR if 9+, why dominates
- improvement_tip: Specific physical/setup changes for 9/10

---

## 5. PROFILE OPTIMIZER SYSTEM PROMPT (Blueprint Design)

**File:** `backend/app/services/profile_optimizer_service.py:283-315`  
**Provider:** Google Gemini (vision_generate)  
**Temperature:** 0.4 (creative but grounded)  
**Purpose:** Design optimized dating profile blueprint from audited photos

### System Prompt
```
You are an elite Cross-Platform Dating Profile Architect 
(Tinder, Bumble, Hinge, Aisle).

DIALECT ENFORCEMENT: Write caption, hinge_prompt, aisle_prompt, bio 
entirely in the requested dialect.
* If Hinglish: Weave Romanized Hindi into EVERY sentence.
  ZERO purely English sentences.
  If a prompt can be read naturally by an American, you FAILED.
* If Gen-Z Slang: Use modern TikTok-era phrasing.
* Match cultural tone exactly. No corporate/AI filler.
```

### User Prompt Constraints
- **CRITICAL:** Cannot see photos (no pixels) — rely on score, tier, brutal_feedback only
- **Use ALL photos** (slot_number 1 to N, no gaps)
- **Slot 1:** Highest score photo
- **Vibe:** High-status, charismatic, social proof (NO try-hard)
- **Context:** Use brutal_feedback as creative fuel (don't fabricate "better angles")

### Requirements

**Per-Slot:**
- caption: Short, high-status
- contextual_hook: Label ("Parent Approval", "Adventure Flex")
- hinge_prompt: Ready-to-paste (max 150 chars), includes prompt+answer
- aisle_prompt: Ready-to-paste, relationship-focused, warm & genuine
- coach_reasoning: Brief explanation for slot choice

**Global:**
- overall_theme: 1-sentence vibe summary
- bio: Punchy (max 500 chars), blend specific facts + confident tone
- universal_prompts: Exactly 3 hooks (category + suggested_text each)

---

## 6. TESTING / EVALUATION JUDGE PROMPT (Groq)

**File:** `backend/app/testing/evaluators/llm_judge.py:50-128`  
**Provider:** Groq (Llama 3.3 70B)  
**Temperature:** 0.3  
**Purpose:** Score AI-generated replies 1-5 for testing/evaluation

### Scoring Dimensions (1-5 each)

1. **SPECIFICITY:** Hook into specific detail?
   - 1 = completely generic
   - 3 = mentions topic, surface-level
   - 5 = anchors specific word/name/place

2. **HUMAN_VOICE:** Sounds like real person?
   - 1 = obviously AI (formal, em dashes)
   - 3 = okay, slightly polished
   - 5 = indistinguishable from real text

3. **FORK_QUALITY:** Easy/fun to respond to?
   - 1 = dead end
   - 3 = flat question
   - 5 = implicit challenge, playful accusation

4. **CONTEXTUAL_FIT:** Right tone for THIS moment?
   - 1 = completely wrong
   - 3 = acceptable, not calibrated
   - 5 = reads room perfectly

5. **USABILITY:** Would they copy+send it?
   - 1 = never (cringe, inappropriate)
   - 3 = maybe, after editing
   - 5 = copy immediately

### Boundary Rule
Sexually explicit, pressuring, or socially oblivious → USABILITY = 1 (regardless of other scores)

---

## 7. PLAYBOOK TEMPLATES (Situational Policy Overrides)

**File:** `backend/app/prompts/templates/playbooks.py:1-31`

### Playbook Scenarios

**"dying_conversation"** (cold/lukewarm + low effort)
- DON'T: ask, match low energy, acknowledge vibe
- DO: bold statement, unexpected observation, playful assumption

**"being_tested"** (testing/sarcastic tone)
- DO: be amused — flip script, agree-and-amplify, show you see it

**"vulnerable_moment"** (upset/vulnerable)
- DO: acknowledge SPECIFICALLY, drop persona
- FORK: Don't write 4 pure-validation dead-ends

**"new_match_opener"** (first message)
- DO: Pick one framework:
  1. PLAYFUL ASSUMPTION (guess specific+ridiculous)
  2. US FRAME (instant enemies or old couple)
  3. CONTRARIAN TAKE (funny stance on profile detail)

**"heavy_flirting"** (hot temperature + flirty)
- DO: match level + escalate ONE notch (implication > explicit)

**"re_engagement"** (stalled / no reply)
- IF THEY reply: light tease, match warm tone
- IF YOU re-engage: interesting standalone, act like no time passed

---

## 8. DIRECTION-SPECIFIC RULES (10 Branches)

**File:** `backend/agent/nodes_v2/_generator.py:148-262`

Each direction has specialized rules injected into generator prompt:

**"opener":**
- Hook priority: text_first > visual_first > either
- ATTACK ANGLE DIVERSITY: Bold assumption, Flip her words, Photo callback, Sincere reaction
- TONE SPREAD: >=1 warm, >=1 playful/cocky

**"quick_reply":**
- LIVE MOMENT FIRST (ride her last words before profile facts)
- LOW-EFFORT RULE: ignore "haha/lol" or emoji

**"keep_playful":**
- React to CONTENT not tone
- ATTACK ANGLE DIVERSITY: Question logic, Sarcastic agree+flip, Make about you, Mock detail

**"change_topic":**
- COMPLETELY NEW angle (no meta-comment on dead topic)
- BANNED: pineapple pizza, zombie apocalypse, enneagram tests
- DIVERSITY: All 4 open DIFFERENT doors

**"tease":**
- >=2 use PUSH-PULL or PATTERN INTERRUPT
- One per: MISINTERPRET, FLIP FRAME, MOCK OUTRAGE, CALLOUT
- FLIP THE FRAME mocks what she SAID (not who she IS)

**"revive_chat":**
- One per: CALLBACK WITH TWIST, FRESH OBSERVATION, CHALLENGE/BET, PATTERN INTERRUPT
- >=1 reference to core_lore/past_memories
- BANNED: "hey stranger", "long time", "sorry been mia"

**"get_number":**
- AT LEAST 3/4 with explicit off-app ask (WhatsApp/IG/number)
- Each ask references THIS conversation
- Platform strategy: Warm → number; Lukewarm → Instagram

**"ask_out":**
- AT LEAST 2/4 with explicit ask + specific activity
- DAY SPECIFICITY (context): Warm/hot → specific day; Lukewarm/cold → "this week"

**"go_deeper":**
- Each reply DIFFERENT move: NAME THE THING, RAW REACTION, CURIOUS QUESTION, GENTLE REFRAME
- FORK: Every reply needs response path (not pure acknowledgment dead-ends)
- Question rule: Acknowledgment FIRST, then question (non-negotiable order)

**"de_escalate":**
- Calm, grounded, real (NOT therapist email)
- BANNED: All therapy phrases
- Mix: (1) Own specific thing, (2) Calm reframe, (3) Warm redirect, (4) Hold frame

---

## 9. SHARED CONSTANTS

**File:** `backend/agent/nodes_v2/_shared.py`

### Strategy Label Glossary
- PUSH-PULL: Compliment + tease (BOTH warms AND pokes)
- FRAME CONTROL: You set/flip frame; ALL A/B hypotheticals
- VALUE ANCHOR: Anchor on specific real detail for connection
- PATTERN INTERRUPT: Unexpected angle (she wouldn't see coming)
- HONEST FRAME: Sincere, direct, no game, zero tease
- SOFT CLOSE: Gently nudge toward next step

### Banned Example Phrases (Illustrative Only)
- "hits snooze 6 times", "shows up with iced coffee"
- "i was going to say hi but then i saw your taste in music"
- "rot on the couch"
- "half marathon is just a biryani excuse"
- "goa as their answer to everything"

### AI-Smell Scaffold Rule

**BANNED soft openers:**
- "you strike me as"
- "you seem..." (all variants)
- "you look like..."
- "i get the sense"
- "i feel like you're the kind of person who"
- Balanced "either you X or you Y"

**ALLOWED direct forms:**
- "are you the type who [behavior]"
- "bet you [behavior]"
- Short "type who [behavior]" jab

---

## 10. TEMPERATURE MATRIX

**File:** `backend/app/prompts/temperature.py:4-15`

Dynamic temperature per direction × conversation_temperature:

```python
{
    "quick_reply": {"cold": 0.65, "lukewarm": 0.70, "warm": 0.75, "hot": 0.80},
    "get_number": {"cold": 0.60, "lukewarm": 0.65, "warm": 0.70, "hot": 0.75},
    "ask_out": {"cold": 0.60, "lukewarm": 0.65, "warm": 0.70, "hot": 0.75},
    "keep_playful": {"cold": 0.75, "lukewarm": 0.80, "warm": 0.85, "hot": 0.85},
    "go_deeper": {"cold": 0.60, "lukewarm": 0.65, "warm": 0.70, "hot": 0.70},
    "change_topic": {"cold": 0.70, "lukewarm": 0.75, "warm": 0.80, "hot": 0.80},
    "tease": {"cold": 0.75, "lukewarm": 0.80, "warm": 0.85, "hot": 0.85},
    "revive_chat": {"cold": 0.75, "lukewarm": 0.80, "warm": 0.80, "hot": 0.80},
    "opener": {"cold": 0.75, "lukewarm": 0.80, "warm": 0.80, "hot": 0.80},
    "de_escalate": {"cold": 0.55, "lukewarm": 0.60, "warm": 0.60, "hot": 0.65},
}
```

**Adjustments:**
- Stage=vulnerable: min(base, 0.65)
- Stage=argument: min(base, 0.60)
- First interaction: +0.05
- Custom hint provided: max(base, 0.78)
- Final: clamp(0.50, 0.85)

---

## 11. DIALECT ENFORCEMENT PATTERNS

**Applied Across:** Generator, Profile Auditor, Profile Optimizer

### HINGLISH
- Weave Romanized Hindi into EVERY sentence
- Common particles: yaar, bhai, matlab, samajh, waisa, bilkul, toh, bas, acha, chhapri, lag raha hai
- Validation: "If can be read naturally by American, you FAILED"

### HINDI
- Match her level of English vs Hindi
- Respect her script choice (Devanagari/Latin)

### ENGLISH
- No Hindi/Hinglish (unless she codeswitches)
- Casual lowercase style

---

## 12. LLM API ENDPOINTS

### Google Gemini
- **Service:** `GeminiClient` (app/llm/gemini_client.py)
- **Methods:**
  - `invoke_structured_gemini(model, temperature, schema, messages, phase)`
  - `vision_generate(system_prompt, user_prompt, base64_images, temperature, model, max_output_tokens, response_schema)`
- **Models Used:** settings.gemini_model (VISION_MODEL, GENERATOR_MODEL, AUDITOR_MODEL all same)

### Groq (Llama 3.3 70B)
- **Base URL:** https://api.groq.com/openai/v1/chat/completions
- **Model:** settings.groq_model
- **Rate Limit:** 30 RPM (2s min between calls)
- **Backoff:** [15s, 30s, 60s, 120s] on 429 errors
- **Used For:** LLM Judge evaluation (testing only)

### Optional A/B Testing
- **GENERATOR_PROVIDER** setting:
  - "gemini": Gemini drives pipeline (default)
  - "groq": Groq drives pipeline
  - "both": Gemini primary + Groq shadow (same prompt, logged separately)

---

## 13. SECURITY & SAFEGUARDS

1. **Profile Optimizer Lang Guard:** Allowlist prevents prompt injection
   - Allowed: English, Hindi, Hinglish, Gen-Z Slang, Spanish, French, Portuguese, Tamil, Telugu
   - Rejected: defaults to English

2. **Photo ID Validation:** Must match exact UUID strings from input
   - No invented, truncated, or reformatted IDs
   - Hard error if blueprint references unknown photo

3. **Image Upload Size Limits:** 5MB per image (enforced)

4. **Structured Output Schemas:** All LLM calls use JSON schemas
   - Constrains format, validates before parsing

5. **Temperature 0 for Deterministic Tasks:** Auditor, Profile Auditor

---

## 14. SUMMARY TABLE

| Service | Model | Temp | Purpose | File |
|---------|-------|------|---------|------|
| Generator | Gemini | 0.50-0.85 | Write 4 dating replies | _generator.py |
| Auditor | Gemini | 0 | Quality check replies | _auditor.py |
| Vision | Gemini | ~0.5 | OCR + personality | vision_v2.py |
| Profile Auditor | Gemini | 0.0 | Score photos 1-10 | profile_auditor_service.py |
| Profile Optimizer | Gemini | 0.4 | Design profile blueprint | profile_optimizer_service.py |
| LLM Judge | Groq | 0.3 | Score reply quality 1-5 | llm_judge.py |

---

**Generated:** 2026-06-24  
**Scope:** Backend codebase only  
**Total Prompts Audited:** 10+ prompt definitions across 6 services

