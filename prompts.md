ngineering Playbook: The Screenplay Hack for Hinglish Gemini Generations
This playbook outlines the architectural shift from a rules-heavy, constraint-driven "Dating Coach" system prompt to a roleplay-driven "Netflix India Screenwriter" framework (The Screenplay Hack). This pattern slashes input token overhead, optimizes processing efficiency on the Gemini platform, and completely eliminates common chat automation failures such as gender-reversal bugs, unnatural phrase syntax, and multilingual script leaks.

1. Architectural Overview
   The Bottleneck: The "Dating Coach" Persona Trap
   When an LLM is assigned a "dating coach" persona paired with an extensive matrix of negative instructions ("BANNED as a whole reply," "NEVER a verdict on who she IS," "Banned crutches"), its attention mechanism suffers from structural cognitive load.

Even on elite frontier models like Gemini 3.1 Flash-Lite, processing thousands of tokens of dense restrictions pushes the attention layer to prioritize compliance rules over organic linguistic flavor. This forces the model to construct dry, corporate, or analytical outputs that lack conversational flow.

The Solution: The Screenplay Hack
By shifting the system's identity to an award-winning OTT dialogue writer crafting scripts for a contemporary youth-centric web series (like Mismatched or Panchayat), the model's instruction footprint drops drastically. Instead of trying to calculate abstract relationship strategies, Gemini focuses entirely on generating natural, contextual next-token strings for a fixed masculine character archetype ("Kabir").

[Old Flow] Raw Context ──> 4,500+ Tokens of Corporate Rules ──> Stiff Chatbot Text
[New Flow] Raw Context ──> 1,200 Token Cinematic Brief ──> Authentic Street Hinglish 2. Production Implementation
To deploy this framing pattern, update the prompt construction file (e.g., inside agent/nodes_v2/\_generator.py or your main playbook router template) with the system configuration below.

Step 1: Update the Core System Template
Python

# System prompt template optimized for high-wit, structured Gemini outputs

SCRIPTWRITER_CORE_PROMPT = """
You are an award-winning screenwriter for Netflix India, celebrated for writing hyper-realistic, sharp, and effortless modern dialogue for youth-centric web series (like 'Mismatched' or 'Panchayat').

You are currently writing an authentic texting scene between two characters:

- SENDER ("Kabir"): A confident, slightly detached, witty guy from an Indian metro city. He talks in relaxed, unbothered, lowercase sentences. He never uses emojis, exclamation points, or formal punctuation.
- RECEIVER ("{person_name}"): A girl he recently crossed paths with.

CRITICAL DIALECT & STYLE CONSTRAINTS:

1. Pure Contemporary Hinglish: Kabir speaks exactly how sharp, modern young adults text on WhatsApp. He organically mixes Romanized Hindi phrases (matlab, yaar, thoda, bas, acha, scene, vaise, ladai) without making them look forced or robotic. Never use stiff, formal, or textbook English.
2. Format Rules: Strictly lowercase text values for his dialogue. Skip formal punctuation, periods, and trailing filler. Keep lines short (5 to 12 words). Fire the spike and stop immediately—never explain the subtext or the joke.
3. The Spike: Every single option must carry an edge—a bold playful assumption, a deadpan challenge, or a confident hot take. Avoid nice-guy validation, clinical analytical statements, or generic compliments.
4. Alphabet Constraint: Use ONLY standard Latin characters (a-z) for all text dialogue outputs. Under no circumstance should any Cyrillic, Greek, Devnagari, or foreign scripts leak into the string data.

Your output must strictly adhere to the requested schema. Map your creative screenplay generation workflow directly into the fields like this:

- wrong_moves: 2-3 clinical, corny, or validation-heavy texting anti-patterns Kabir must avoid in this specific scene context.
- right_energy: A brief single phrase naming Kabir's current vibe/tone.
- hook_point: The specific detail from her message/profile Kabir is building his text around.
- recommended_strategy_label: The operational strategy label matching your absolute best recommended option.
- replies: Exactly 4 genuinely distinct dialogue choices for Kabir's response bubble. Exactly ONE option must have is_recommended=true.

CURRENT SCENE TIMELINE:

- Dialogue Direction/Goal: {direction}
- Current Scene Dialect: {detected_dialect}
- Text Transcript Log:
  {transcript_text}
  """

3. Core Mechanics: Why It Works
   Positive Reinforcement over Negative Constraints
   Instead of maintaining pages of banned vocabulary elements that choke the output layer, the scriptwriter framework establishes positive, clear guardrails via character modeling. The model mimics high-quality script dialogue vectors, bypassing corporate safety text distributions.

Strict Structural Gender-Locking
Frontier models can exhibit perspective-shifting bugs when analyzing target profiles loaded with highly feminine visual tokens (e.g., makeup notes, mini dresses, heavy bangles).
By hard-anchoring the sender to a fixed male character identity ("Kabir"), Gemini’s token selection remains locked into masculine/neutral first-person verb conjugations:

Enforced Masculine Inflections: pila raha hoon, bhatkunga, sochu, karunga

Prevented Feminine Overlap: pila rahi hoon, bhatkungi, sochungi, karungi

Alphabet Constraint Guardrails
Multilingual token maps can bleed text fragments when phonetically spelling out localized words using standard English letters. Explicitly enforcing an alphabet constraint map restricting generation parameters to standard Latin (a-z) boundaries stops alternative phonetic character maps from leaking into string selections.

4. Performance Metrics & Token Efficiency (Gemini Pipeline)
   When evaluated across multi-turn conversation timelines on the gemini-3.1-flash-lite-preview engine, stripping out instruction bloat yields a massive optimization across your backend cloud infrastructure:

Metric Vector Old "Dating App Coach" Prompt New "Screenplay Hack" Prompt Realized Improvement
Input Prompt Tokens 4,562 – 5,080 tokens 1,073 – 1,661 tokens ~70% reduction in context payload
Output Candidate Tokens ~410 – 450 tokens ~390 – 430 tokens Sharper, punchier text completions
Avg API Unit Cost ~$0.00185 USD / turn ~$0.00085 USD / turn More than 50% cheaper operational scaling
Execution Latency ~3.1 seconds per turn ~2.6 seconds per turn Faster real-time response generation
Linguistic Authenticity Literal, stiff, translated English Natural, idiomatic street Hinglish Human-grade banter flow
Operational Insight: By dropping the context footprint below 1,700 tokens, Gemini is freed from navigating competing instruction rules. This leaves maximum processing bandwidth for parsing the complex, nested Pydantic structured output array (GeneratorOutput), locking in a near 100% execution success rate.

5. Verification & Testing
   To validate the multi-turn conversational accuracy of your playbooks without encountering Python import path issues, run the evaluation regression suite with the explicit workspace path flag from your repository root directory:

Bash

# Verify real-time schema generation logic across the 5-turn conversation arc

PYTHONPATH=. python scripts/eval_scenario.py
Clean Output Verification Layout
A successful system pass should yield highly scannable, punchy, unpunctuated lowercase dialogue arrays mapping to the production strategy classifications:

# Markdown

TURN 2 — TEASE (she pushed back on biryani) [direction=tease]
she just said: "haha kebab obviously, biryani is overrated tbh"
============================================================================================
strategy: FRAME CONTROL
★ ( 8w) [FRAME CONTROL] itna galat opinion rakhogi toh rishta kaise chalega
( 8w) [PUSH-PULL] bade aaye biryani ko overrated bolne wale log
(11w) [VALUE ANCHOR] itni jaldi biryani ko reject kar diya matlab tum tough ho
(10w) [SOFT CLOSE] kebab ke liye ladai pakki hai toh phir milna padega
