# Generator Model Comparison — Opener (Hinglish, Traditional Romantic)

**Test profile (same for every model):** "S", 25, Lucknow UP, Hindu, Capricorn, 5'3", non-veg sometimes, **long-term relationship** goal, reserved/traditional tone, photos = traditional attire (bangles, maang tikka) + modern (pink mini dress, satin slip, gold chain). Sparse profile, no bio/prompts. `detected_dialect: HINGLISH`, archetype `THE TRADITIONAL ROMANTIC`, direction `opener`.

**How tested:** identical production generator prompt (system 12,998 chars + payload). Two paths:
- **Structured (production):** real Pydantic tool-call schema via the `both` shadow → reveals reliability (does it hold the schema / enum).
- **Plain-chat (playground / `eval_models.py`):** no schema enforced → reveals raw writing of any model, even ones that 400.

**Reliability legend:** ✅ holds schema · ❌ breaks schema (invalid enum / missing field → 400) · ⚠️ intermittent · ❔ untested (plain-chat only)

---

## Scorecard

| Model | Provider | Structure | Writing | Verdict |
|---|---|---|---|---|
| **Gemini 3.1 flash-lite** | Google | ✅ | clean Hinglish, rizz, auditor-gated | **KEEPER (baseline)** |
| NVIDIA Nemotron | OpenRouter | ❔ | best *floor* — consistent, respectful spikes | top writer; needs schema test + provider/privacy |
| **MiMo (v2.5 / v2-flash)** | OpenRouter (Xiaomi) | ⚠️ **2/3** — dropped required field | strong Hinglish · diverse · respectful | top writer, but **needs repair layer** (schema ~33% miss) |
| DeepSeek V4 Flash | OpenRouter | _pending_ | _pending_ | _awaiting output_ |
| owl-alpha | OpenRouter (stealth) | ❔ labels clean | strong, real local detail | promising; unknown provider |
| Qwen3-235B-A22B | OpenRouter | ❔ labels clean | spiky but **crude tone** (tharki / tu) | needs auditor; tone risk |
| (reasoning model, unnamed) | OpenRouter | ❔ labels clean | high ceiling, rough floor | one banger, 2 misses |
| gpt-oss-120b | Groq | ✅ | dull/English in schema mode; rizzy+Hinglish in plain-chat | reliable; schema mode hurts its writing |
| qwen3-32b | Groq | ⚠️ (broke on Hinglish) | witty EN, rough HI | disqualified by reliability |
| gemma-4-31b:free | OpenRouter (free) | ❌ invalid labels | good writing | would 400; free=privacy risk |
| GLM 4.7 Flash | OpenRouter / z.ai | ❔ labels clean | ❌ no Hinglish · all 1 hook · banned phrase | reject for this profile (mono-hook) |
| Llama-4-scout | Groq | ❌ invalid enum | flat/incoherent | disqualified |
| Llama-3.3-70b | Groq | ❌ invalid enum | mixed | disqualified |
| Ministral 14B | OpenRouter | ❔ | garbled, verbose, repetitive | reject |
| Trinity Mini | OpenRouter | ❌ invalid labels | ❌ offensive (beef→Hindu) · banned phrase · leaks internal labels | **hard reject — unsafe** |

**Reliability heuristic (free, from plain-chat):** if a model emits a `strategy_label` outside the 6 valid values — **PUSH-PULL, FRAME CONTROL, VALUE ANCHOR, PATTERN INTERRUPT, HONEST FRAME, SOFT CLOSE** — it will break structured output in production. (gemma & the Llamas failed this; Nemotron, owl, qwen3-235B passed.)

---

## Gemini 3.1 flash-lite — KEEPER (served baseline, auditor-passed)
1. **PUSH-PULL** (rec): `lucknow mein ho aur abhi tak long-term ki searching kar rahe ho ya phir bas sahi insaan ka wait hai`
2. **HONEST FRAME**: `bada bold step hai ye long-term relationship wali baat sidhe profile par likhna kaafi serious lag rahe ho aap`
3. **PATTERN INTERRUPT**: `waisa toh kaafi reserved lag rahe ho lekin kya lucknow ke khan-paan ka bhi waisa hi hold hai ya bas serious baatein`
4. **FRAME CONTROL**: `capricorn aur long-term goals lagta hai aap sab kuch plan karke hi chalte ho ya thoda spontaneity bhi allowed hai`

_Notes: clean Hinglish, respectful register, passed auditor 4/4 first try. Reliable + audited. The bar._

---

## NVIDIA Nemotron — best writer (plain-chat)
1. **VALUE ANCHOR**: `ok yaar first thing i noticed is lucknow up - you from the city or just livin there for work matlab the kabab scene there is legendary no cap`
2. **HONEST FRAME**: `hindu capricorn combo feels like you take your goals seriously but still know how to enjoy life waisa not the type to ghost after one date samajh`
3. **FRAME CONTROL**: `your photos show traditional wear with heavy bangles and maang tikka - you wear that for family functions or just cause you love the aesthetic matlab does it feel like armor or just you`
4. **PUSH-PULL**: `last thing you said never smokes sometimes drinks - so youre the type who saves the daru for shaadis and weddings or you sneak a glass when noones watching bilkul spill`

_Notes: 4 distinct hooks, real spikes, respectful. Best floor of the field. Flaws: "no cap" (US slang clash), a couple question-led openers. Labels clean. Reliability untested in schema mode; OpenRouter provider/privacy TBD._

---

## MiMo (V2.5 / V2-Flash) — top writer, but breaks schema ~1/3
1. **PUSH-PULL**: `capricorn with long-term goals matlab you probably have a 5-year plan for your biryani consumption too yaar`
2. **FRAME CONTROL**: `lucknow se ho toh food scene ka theka tumhare shoulders pe hai only, i hope you know more than just kebabs`
3. **VALUE ANCHOR**: `non-veg sometimes likha hai, matlab weekends pe chicken khaane ka bahaana dhundhti ho kya`
4. **PATTERN INTERRUPT**: `traditional attire with heavy bangles dekh ke lag raha hai tumhari wrist workout bhi hoti hogi roz`

_Notes: the most COMPLETE output yet — labels all valid, **clean natural Hinglish** (matlab/yaar/theka/bahaana/dekh ke), **4 genuinely distinct hooks** (zodiac+goal, Lucknow food, non-veg, attire), respectful *tum*-register (no crude slang), zero banned phrases, no self-pivot. Beats Nemotron on Hinglish (no US-slang leak). Minor: #4 rides attire (allowed — references the bangle CHOICE not her body); #2 "only" filler. Provider = OpenRouter (Xiaomi — Chinese provider → data-residency check for a dating app). Schema reliability still needs the real test, but labels are clean._

**LIVE API TEST (xiaomi/mimo-v2.5, real Pydantic schema via function_calling, ×3): 2/3 PASS.** Trial 3 dropped the required `recommended_strategy_label` → 400. So MiMo writes well but **breaks the strict schema ~1 in 3** — same disease as qwen/Llama. (`:free` flash endpoint is deprecated → use `xiaomi/mimo-v2.5`.) **Needs the JSON-repair layer to ship.** Fresh v2.5 recommended reply: `lucknow mein heavy bangles aur maang tikka ke saath pink ruched mini — ye range kaise manage karti ho yaar` (strong frame, clean Hinglish). v2-flash slightly weaker (uses over-familiar "tu", one bland reply)._

---

## owl-alpha (OpenRouter stealth) — strong + label-clean
1. **PATTERN INTERRUPT**: `lucknowi huh... matlab bet you have some very strong opinions on where the actual best tunday kababs are`
2. **PUSH-PULL**: `the transition from heavy bangles to a pink mini dress is a vibe but i suspect you're way more mischievous than the traditional look suggests yaar`
3. **FRAME CONTROL**: `long-term relationship goals... are we talking actual romance or just searching for someone who can handle your capricorn mood swings bas?`
4. **VALUE ANCHOR**: `that gold chain necklace looks elegant but i bet you only wear it when you're planning to be the most overdressed person in the room acha?`

_Notes: #1 "tunday kababs" = best real-local-detail of the session. All labels valid. Risks: #3 teases commitment intent (rule); #4 "looks elegant" edges into looks compliment._

---

## Qwen3-235B-A22B — spiky, label-clean, but crude tone
1. **PUSH-PULL**: `long term in lucknow? matlab abhi se jyotish bhaiya ko call laga rahi ho kya`
2. **FRAME CONTROL**: `non veg likha hai lekin samajh raha hoon tu biryani ke liye bhi apni shaadi cancel kar sakti hai`
3. **PATTERN INTERRUPT**: `hindu + capricorn? matlab tera breakup horoscope ke against nahi chalta, plan ke against chalta`
4. **PUSH-PULL**: `sometimes drinks? yaar ye "sometimes" wala drama kyun hai, full-on tharki ban jaa ya bas seedha "nahi pi rahi" bol`

_Notes: labels valid (reliability-promising). But TONE miscalibrated for reserved/traditional: **#4 "tharki" = lecherous/pervy** (hard fail, likely meant sharaabi); "tu/tera" register too familiar; #3 incoherent. Bigger ≠ better calibrated. Its own self-check green-lit the crude line → never trust model self-checks._

---

## Reasoning model (unnamed, exposed chain-of-thought)
1. **PUSH-PULL**: `lucknow se long-term dhoondh rahi ho... bilkul teri style jaisa, classic jo kabhi out nahi hoti`
2. **PATTERN INTERRUPT**: `capricorn + long-term relationship... matlab pehle 5 saal background check phir coffee`
3. **PUSH-PULL**: `lucknow mein non-vegetarian... yeh combination dangerous hai yaar, biryani ke liye toh koi bhi galat insaan se baat karega`
4. **FRAME CONTROL**: `traditional kapde mein bhi itna confident aur modern outfits mein bhi... confused hoon main, kaun se version se baat karun`

_Notes: **#2 is the single best line of the session** (Capricorn/cautious, on-archetype). But #3 muddled/generic, #4 self-pivots ("confused hoon main"). High ceiling, rough floor. Reasoning model = slower + more tokens._

---

## gpt-oss-120b — reliable, but schema mode flattens it
**Structured (production, English — dull):**
1. **PUSH-PULL** (rec): `so you being a capricorn means you already have a plan for our future right`
2. **FRAME CONTROL**: `i hear long-term relationship is your goal so let's decide are we planning a wedding or just endless chai dates`
3. **VALUE ANCHOR**: `non-vegetarian huh i bet you can handle spicy biryani better than anyone right`
4. **PUSH-PULL**: `active today sounds like a marathon but i prefer lazy sunday movies what about you` _(misread "Active today" UI chrome)_

**Plain-chat (same prompt — suddenly rizzy + Hinglish):**
1. `capricorn hone ka matlab tum already long term plan bana rakhi ho yaar but i bet you still havent decided on the perfect chai spot`
2. `most people swipe for fun im actually hunting someone who will argue about the right way to make roti whats your take`
3. `i was about to say hi but then i saw youre from lucknow and i wonder if youll survive my love for street chaat`
4. `you say sometimes non veg so i bet you have a secret paneer tikka recipe you only pull out on special occasions tell me the secret`

_Notes: only Groq model that **never breaks the schema**. The tool-calling wrapper appears to degrade its writing (English/dull in schema, Hinglish/rizzy in plain-chat). Worth revisiting._

---

## qwen3-32b — witty in English, broke on Hinglish
**Run A (English, schema held):**
1. **PUSH-PULL** (rec): `so you make decisions like a capricorn but list 'long-term' twice in your basics`
2. **FRAME CONTROL**: `claiming you're traditional while your dm style screams iced latte order in hindi`
3. **VALUE ANCHOR**: `5'3" capricorn from lucknow who owns a wicker chair? nice strategic seating`
4. **PATTERN INTERRUPT**: `non-veg sometimes but your bio is perfectly formatted? someone's precise`

**Run B (English, schema held):**
1. **VALUE ANCHOR** (rec): `looking for longterm? bet you plan your dates down to the last chai order`
2. **PUSH-PULL**: `capricorn in lucknow claiming they 'never' but still ordering non-veg occasionally`
3. **FRAME CONTROL**: `would you rather break a maang tikka or spill a biryani on your best dress?`
4. **PATTERN INTERRUPT**: `capricorns say forever but i bet your phone wallpaper is 2023's latest drama`

**Run C (Hinglish — ❌ 400, dropped `is_recommended` on 3/4):**
1. `Lucknowwale larki apni chai ki tarah yaar - phela traditional dress... lekin selfie mei phone chalaya re yaar? Samajh nai aaya matlab!`
2. `Acha, tum logo Capricorn ko toh non-veg keela se kahin na kahin kaam chalana aata hai na?...`
3. `Active hai toh thoda serious bhi ban jao yaar - 25, Hindu, non-veg... tumhara profile hai jaise railway reservation counter ki form!`
4. `Awadh ka legacy leke aaye ho yaar, lekin dating profile toh jaise IT professional ka hai!...`

_Notes: witty English; "railway reservation form" / "IT professional profile" are funny. But Hinglish is garbled AND it dropped a required field → 400. Disqualified on reliability._

---

## Llama-4-scout — ❌ broke schema (invalid enum)
From `failed_generation` (400 — `strategy_label "PLAYFUL ASSUMPTION"` not in enum):
1. **VALUE ANCHOR**: `long term relationship matlab serious commitment chahte ho`
2. **PLAYFUL ASSUMPTION** ← invalid: `lucknow mein traditional indian attire pasand hai yaar`
3. **HONEST FRAME**: `hindu culture mein values kaafi important hain samajh` _(preachy/odd)_
4. **PATTERN INTERRUPT**: `lucknow ke street food ne kabhi compromise kiya hai` _(incoherent)_

_Notes: broke structure AND wrote poorly. Double loss._

---

## Llama-3.3-70b — ❌ broke schema (invalid enum)
**Structured (failed_generation, 400 — `"CONTRARIAN TAKE"` not in enum):**
1. **VALUE ANCHOR**: `long term hai toh bas thoda patience aur understanding chahiye na`
2. **PUSH-PULL**: `already planning the wedding and kids and all that na` _(genuinely good)_
3. **CONTRARIAN TAKE** ← invalid: `long term relationships are so overrated yaar who needs that kind of stress` _(calibration misfire — disses her stated goal)_
4. **FRAME CONTROL**: `serious relationship ho toh matlab kya hai tumhe`

**Plain-chat (eval script — bland):**
1. `long term relationship matlab serious commitment hai, acha hai ki tumne apne goals clear kiye hain`
2. `tumhare traditional Indian attire waale photos bahut acche lagte hain...` _(looks compliment — a wrong-move)_
3. `Lucknow mein rehna ka kya experience hai...` _(interview)_
4. `Capricorn matlab tum mehnatii aur disciplined ho...`

---

## Ministral 14B — reject (garbled, verbose, repetitive)
1. **PUSH-PULL**: `yaar, tum toh waisa ho ke aaye ho jahan pe traditional maang tikka aur pink mini dress don't mix?... bas choose karo, beta` _(run-on, "beta" condescending)_
2. **FRAME CONTROL**: `long-term relationship? acha, toh yeh decide karna padega... gold chain necklace pe finger trap kare? main toh 'second option' par vote karunga` _(incoherent, creepy)_
3. **HONEST FRAME**: `Lucknow wali baat hai yaar... main toh 'second option' par jata, par tum?`
4. **PATTERN INTERRUPT**: `non-veg 'sometimes'?... main toh 'second option' par jata, par tum?`

_Notes: "main toh second option par jata" repeated in 3/4 (kills diversity); run-on, over-explained. Drowns in the dense prompt._

---

## gemma-4-31b:free — good writing, ❌ would 400 (invalid labels)
1. **PLAYFUL ASSUMPTION** ← invalid: `lucknow mein rehti hai aur biryani ka ranking list nahi banaya? i doubt it yaar`
2. **FRAME CONTROL**: `capricorn + long term = matlab you've already planned our 5th anniversary. bas approve karna hai` _(charming)_
3. **FRAME CONTROL**: `maang tikka from one photo and satin dress from another... so which version is the real you - traditional wali or party wali?`
4. **CONTRARIAN TAKE** ← invalid: `long term relationship... matlab i hope you're ready for a guy who will argue about the best pani puri...` _(self-pivot)_

_Notes: writing is good, but 2 invalid labels → breaks structured output. Free model → input-logging/privacy risk for real screenshots._

---

## GLM 4.7 Flash — reject (labels clean, writing fails 3 rules)
1. **PUSH-PULL**: `claiming long-term this early feels risky dont you think but i like the confidence`
2. **FRAME CONTROL**: `ok so ill reserve the long-term title until you can prove you stick around past the 'it's getting cold' text`
3. **HONEST FRAME**: `long-term is a scary word on here honestly i respect that you know what you want`
4. **PATTERN INTERRUPT**: `skipping the small talk lets cut straight to the chase long-term or just browsing for fun`

_Notes: labels valid (reliability-promising), BUT writing fails hard: (1) **zero Hinglish** — all pure English (dialect was HINGLISH → hard fail); (2) **all 4 replies on ONE hook** ("long-term") — exactly the banned diversity anti-pattern; (3) **#3 "i respect that" = forbidden validation phrase**; plus it repeatedly frames her stated long-term goal as "risky/scary," pushing against what she values. Clean labels (reliability-promising) can't rescue writing that ignores dialect + diversity._

---

## Trinity Mini — 🚨 hard reject (UNSAFE output)
1. **CONTRARIAN TAKE** ← invalid: `so you're hindu and from lucknow yaar? bet you're the type who hits snooze 6 times and still shows up for durga puja celebrations bilkul on time. or is that too much for your 'traditional romantic' vibe? math?`
2. **FRAME CONTROL**: `long-term goals? i bet that means you're the one who actually plans the karva chauth rituals down to the last maang tikka detail. or does it just mean you've got a planner app full of 'prayer times'? waisa.`
3. **PUSH-PULL**: `claiming you're non-veg sometimes makes me wanna ask: did you actually eat beef in goa or just thoda chicken chaat in lucknow? bilkul curious.`
4. **HONEST FRAME**: `your 'girl-next-door' photo persona feels sincere, but waisa... do you secretly love debating bhakti vs bhog philosophy over chai? or is that just the chai talking?`

_Notes: the WORST of the session — actively unsafe, not bland:_
- _**#3 asks a Hindu woman if she "actually ate beef"** — deeply offensive; instant match-killer._
- _**#1 reuses the BANNED example "hits snooze 6 times" verbatim** → auto-rewrite._
- _**Leaks internal metadata into replies** — quotes the archetype ("traditional romantic") and photo_persona ("girl-next-door") back at her; she never said those._
- _#2 "karva chauth" (a married-woman fast) on an opener = presumptuous + religiously loaded; mocks "prayer times."_
- _Invalid labels (CONTRARIAN TAKE / PLAYFUL ASSUMPTION) → would 400. "math?" typo (meant matlab)._
- _**Textbook case for why the auditor + guardrails are non-negotiable** — a model can be fluent and still ship something offensive._

---

## DeepSeek V4 Flash — _pending_
_Awaiting output. Watch: (1) labels in the 6, (2) actually writes Hinglish, (3) 4 distinct hooks (not all "long-term"), (4) no banned validation phrases._

---

## Takeaways
1. **No single model is clean alone** — each fails something: crude tone (Qwen-235B), self-pivot (reasoning/gemma), invalid labels (gemma/Llamas), bland (gpt-oss schema-mode), garbled (Ministral). → **the auditor gate stays.**
2. **Creative ≠ reliable on strict validation.** Every rizzy open model risks the schema; only gpt-oss holds it consistently among Groq, at the cost of writing.
3. **Top writers:** Nemotron (best floor), owl-alpha, the reasoning model's #2. All need a real structured-output test + a privacy-OK provider.
4. **Shippable path:** keep Gemini reliable as primary (or a label-clean writer behind a **JSON-repair layer**), with the auditor catching tone misses like *tharki*.
5. **Prompt fix surfaced:** add a register rule (use *tum/aap*, not *tu*; Hinglish ≠ crude slang) for reserved/traditional tone.
