# Prompt Improvement Plan: 6 Changes, Measured One by One

## How core_lore Reaches the LLM

Currently:
1. `get_match_context()` returns `core_lore` as a plain string of facts joined by `\n`
2. It's stored in `AgentState.core_lore` and passed through `shared_payload`
3. The LLM receives it as a field in the JSON payload alongside the system prompt
4. **No structure, no labels, no priority ordering** — just a blob of text

The prompt templates (`generator.py`) do NOT have `{core_lore}` or `{tier_1}` placeholders. The payload is sent as the user message content alongside the system prompt. So the LLM sees something like:

```
System: You are an award-winning screenwriter...
User: {
  "person_name": "Priya",
  "core_lore": "Priya is 26 years old from Mumbai\nPriya works as a software engineer...",
  "tier_1_raw_exchanges": "them: \"hey!\"\nyou: \"hey! how are you\"",
  ...
}
```

The LLM has to parse this itself. Our improvements will restructure how `core_lore` is formatted **before** it goes into the payload.

## Measurement Protocol

For each change:
```bash
make eval-before           # baseline with current prompt
# apply change 1
make eval-after            # after change 1
make eval-diff             # compare
```

We measure: **Avg Judge Score** (0-10), **Specificity**, **Human Voice**, **Usability**, **Auditor Pass Rate**, **RAG-Hit**, **RAG-Prec**.

## The 6 Changes (in Suggested Order)

### Change 1: Structured Section Labels

**What:** Instead of injecting core_lore as raw text, add clear section headers.

**Before:**
```
core_lore = "Priya is 26 years old from Mumbai\nPriya works as a software engineer..."
```

**After:**
```
core_lore = """
─── FACTS YOU KNOW ABOUT HER ───
• Priya is 26 years old from Mumbai (identity)
• Priya works as a software engineer at a fintech startup (identity)
• She is a vegetarian (preference)
"""
```

**File to change:** `backend/agent/nodes_v2/_generator.py` — add a formatting function that processes `core_lore` before putting it in `shared_payload`.

### Change 2: Importance-Weighted Sorting

**What:** Sort facts by importance_score descending before formatting. Critical identity facts (score 5) appear first, trivial opinions (score 2) last.

**Where:** Same formatting function — parse existing `core_lore` lines, reorder by importance.

### Change 3: Token-Budget Truncation

**What:** Cap total RAG context at a token budget (e.g., 600 tokens for core_lore, 300 for tier_1, 200 for tier_2). Drop lowest-importance facts first when over budget.

**Why:** Long context dilutes LLM attention. [`select_facts_within_budget()`](backend/app/services/rag_improvements.py:147) already exists in the codebase.

### Change 4: Confirmed vs Inferred Labels

**What:** Distinguish between "confirmed" facts (user explicitly stated or copied) and "inferred" facts (LLM guessed from profile). Currently all facts look equal.

**How:** Add a `fact_source` column to `conversation_memories` (or use a heuristic in the formatter). Prefix each fact with `[CONFIRMED]` or `[INFERRED]`.

### Change 5: Tier 1 + Tier 2 Formatting

**What:** Currently tier_1 and tier_2 are passed as raw strings. Add clear section headers and truncate to most recent 3 exchanges.

**After:**
```
─── RECENT CONVERSATION (TIER 1) ───
them: "hey! how r u?"
you: "hey! finally matched haha"

─── CONVERSATION ARC (TIER 2) ───
[opener] hook: first message | her: "hey!" | you: "hey! finally matched"
```

### Change 6: Category Grouping

**What:** Group facts by category, with category headers. This lets the LLM quickly find relevant facts.

**After:**
```
─── IDENTITY (confirmed facts about her) ───
• Priya is 26 years old from Mumbai
• Priya works as a software engineer

─── PREFERENCES ───
• She is a vegetarian
• She loves trekking

─── RECENT CHAT CONTEXT ───
[her last exchange] them: "im a backend dev..."
```

## Implementation Order

| # | Change | Effort | Expected Impact | Risk |
|---|--------|--------|----------------|------|
| 1 | Structured sections | 1h | Medium — helps LLM parse context | Low |
| 2 | Importance sorting | 0.5h | Medium — critical facts seen first | Low |
| 3 | Token budget | 1h | High — prevents attention dilution | Low |
| 4 | Confirmed/inferred | 2h | Medium — reduces hallucination risk | Medium (needs DB migration) |
| 5 | Tier 1/2 formatting | 1h | Low — marginal improvement | Low |
| 6 | Category grouping | 1.5h | High — most impactful | Low |

## Code Changes Needed

### New file: `backend/agent/nodes_v2/_context_formatter.py`

A single formatting function that takes `core_lore: str`, `tier_1: str`, `tier_2: str` and returns a structured, importance-weighted, token-budgeted string. Each improvement adds a step to this formatter.

### Modified file: `backend/agent/nodes_v2/_generator.py`

Replace the direct `shared_payload["core_lore"] = core_lore` with:
```python
from agent.nodes_v2._context_formatter import format_rag_context

formatted = format_rag_context(
    core_lore=core_lore,
    tier_1_raw=tier_1_raw,
    tier_2_summary=tier_2_summary,
    max_tokens=1200,
)
shared_payload["core_lore"] = formatted
```

## How to Test Each Change

```bash
# 1. Baseline
ENV_FILE=../.env.dev make eval-before

# 2. Apply Change 1 (structured sections)
# 3. Test
ENV_FILE=../.env.dev make eval-after
ENV_FILE=../.env.dev make eval-diff

# 4. Keep change 1, apply change 2 (importance sorting)
# 5. Test
ENV_FILE=../.env.dev make eval-after  # overwrites "after"
ENV_FILE=../.env.dev make eval-diff   # compares cumulative

# ... continue for all 6 changes
```

We'll track the cumulative improvement and also identify which single change had the biggest impact by reviewing individual eval diffs.
