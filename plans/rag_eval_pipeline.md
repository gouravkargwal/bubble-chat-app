# RAG Evaluation Pipeline — Assessment & Proposal

## What Exists Today

### 1. End-to-End Prompt Eval (`make eval`)

**Location:** [`backend/app/testing/`](backend/app/testing/)

A comprehensive prompt evaluation suite that:
- Runs **generator_node + auditor_node** against ~50 curated scenarios in [`scenarios.json`](backend/app/testing/scenarios/scenarios.json)
- Evaluates replies via an **LLM Judge** (Groq `llama-3.3-70b`) on 4 axes: specificity, human voice, usability, and overall score
- Tracks **auditor pass rate** (did the auditor approve the reply?)
- Supports **variants** — run "before" vs "after" prompt changes and compare scores
- Has a **SQLite cache** to avoid re-running unchanged scenarios

**Usage:**
```bash
make eval-before    # run baseline → cached as "before"
# ... edit prompts ...
make eval-after     # run new → cached as "after"
make eval-diff      # show before vs after side by side
```

**What it tests:** Reply quality, not RAG quality. The scenarios don't include pre-seeded database context — they build mock `AnalystOutput` from scenario fields and pass empty `core_lore` / `tier_1` / `tier_2`.

### 2. Ragas Evaluation Script (`eval_rag.py`)

**Location:** [`backend/scripts/eval_rag.py`](backend/scripts/eval_rag.py)

A Ragas-based evaluation that:
- Fetches real interactions from the production database
- Generates a **synthetic test set** (20 questions) using Ragas `TestsetGenerator`
- Runs **get_match_context()** for each question
- Feeds context + question into **generator_node** to produce an answer
- Runs **RAG Triad** metrics: `faithfulness`, `answer_relevancy`, `context_precision`
- Logs retrieval feedback to the `retrieval_feedback` table

**What it tests:** RAG retrieval quality, but only works against production data (real conversations in DB). No ground-truth dataset for repeatable regression testing.

### 3. Seed + Test Script (this task)

**Location:** [`backend/scripts/seed_and_test_rag.py`](backend/scripts/seed_and_test_rag.py)

Our newly created script that:
- Seeds synthetic test data (fixed, deterministic)
- Tests read pipeline: 6 queries × multi-metric validation
- Tests write pipeline: fact insertion + metadata + re-retrieval
- Tests dedup and graph integrity

**What it tests:** The RAG pipeline works end-to-end. Not a quality evaluation — just pass/fail.

## What's Missing

| Capability | Missing? | Impact |
|-----------|----------|--------|
| **Regression dataset** — fixed ground-truth Q&A pairs for RAG | ❌ | Can't measure if a change improves or regresses retrieval quality |
| **Automated RAG metrics** — precision, recall, MRR, NDCG | ❌ | No quantitative score for retrieval quality |
| **Variant comparison for RAG** — before/after for RAG changes | ❌ | Can't A/B test RAG changes the way prompt eval A/B tests prompts |
| **Continuous integration** — runs on every PR | ❌ | RAG regressions go undetected |
| **Production telemetry consumption** | Partial | `retrieval_feedback` table exists but nothing reads it to score retrieval |

## Proposed RAG Evaluation Pipeline

### Architecture

```
┌─────────────────────────────┐
│  RAG Test Dataset           │
│  (scenarios_rag.json)       │
│                             │
│  Each scenario:             │
│  - facts: [fact_text,...]   │
│  - query: str               │
│  - expected_facts: [str]    │
│  - expected_entities: [str] │
│  - difficulty: str          │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│  RAGEvaluator               │
│                             │
│  For each scenario:         │
│  1. Seed facts into DB      │
│  2. Run get_match_context() │
│  3. Score results:          │
│     a. HitRate@K            │
│     b. MRR (Mean Recip. Rank)│
│     c. Precision@K          │
│     d. Entity Recall        │
│  4. Collect metrics         │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│  Report Generator           │
│                             │
│  - Variant comparison       │
│  - Per-difficulty breakdown │
│  - Historical tracking      │
└─────────────────────────────┘
```

### Dataset Format

```json
[
  {
    "id": "identity_city_profession",
    "difficulty": "easy",
    "description": "Query for identity facts — city and profession",
    "facts": [
      "Priya is 26 years old from Mumbai",
      "Priya works as a software engineer at a fintech startup",
      "She loves trekking and has been to Himachal 3 times",
      "She is a vegetarian"
    ],
    "query": "what does priya do and where is she from",
    "expected_facts": [
      "Priya is 26 years old from Mumbai",
      "Priya works as a software engineer at a fintech startup"
    ],
    "expected_graph_entities": ["mumbai", "software engineer"]
  },
  {
    "id": "semantic_job_query",
    "difficulty": "hard",
    "description": "Query uses synonyms — no overlap with fact text",
    "facts": [
      "Priya works as a software engineer at a fintech startup"
    ],
    "query": "what is her profession in the tech industry",
    "expected_facts": [
      "Priya works as a software engineer at a fintech startup"
    ]
  },
  {
    "id": "mixing_signal_weak",
    "difficulty": "hard",
    "description": "Similar but irrelevant facts should not be retrieved",
    "facts": [
      "Priya works as a software engineer at a fintech startup",
      "Priya's sister is studying engineering in Delhi",
      "She loves engineering challenges in trekking"
    ],
    "query": "what is her job",
    "expected_facts": [
      "Priya works as a software engineer at a fintech startup"
    ],
    "expected_not_facts": [
      "Priya's sister is studying engineering in Delhi",
      "She loves engineering challenges in trekking"
    ]
  }
]
```

### Metrics

| Metric | What it measures | Formula |
|--------|-----------------|---------|
| **HitRate@K** | Was at least one expected fact in top-K? | `1 if any(expected) in results else 0` |
| **MRR** | How high was the first relevant result? | `1/rank_first_relevant` |
| **Precision@K** | What fraction of results are relevant? | `relevant_in_top_k / k` |
| **Recall@K** | What fraction of relevant facts were found? | `relevant_in_top_k / total_relevant` |
| **Entity Recall** | Were expected graph entities retrieved? | `matched_entities / expected_entities` |
| **Not-Retrieved Rate** | Were irrelevant facts wrongly returned? | `wrongly_retrieved / total_retrieved` |

### Implementation Plan

**Phase 1: Dataset + Script (4-5 hours)**

1. Create [`backend/app/testing/scenarios/scenarios_rag.json`] with 20-30 RAG-specific scenarios across difficulty levels
2. Create [`backend/app/testing/evaluators/rag.py`] — `RAGEvaluator` class that:
   - Seeds facts into DB (reusing our seed helpers)
   - Runs `get_match_context()` 
   - Scores results against expected facts
   - Returns structured metrics
3. Create [`backend/scripts/eval_rag_quality.py`] — CLI entry point:
   ```bash
   python -m scripts.eval_rag_quality
   python -m scripts.eval_rag_quality --variants before after  # compare
   python -m scripts.eval_rag_quality --difficulty hard        # filter
   ```
4. Add to `Makefile`:
   ```makefile
   eval-rag: python -m scripts.eval_rag_quality
   eval-rag-diff: python -m scripts.eval_rag_quality --variants before after
   ```

**Phase 2: Integration with Existing Eval (2-3 hours)**

5. Add `core_lore`, `tier_1`, `tier_2` seeding to the existing prompt eval scenarios so reply quality tests also exercise the RAG context path
6. Add a **RAG context quality score** to the existing `TestRunner` report

**Phase 3: CI Integration (1-2 hours)**

7. Add a GitHub Actions workflow (`.github/workflows/rag-eval.yml`) that:
   - Starts Postgres with pgvector
   - Runs `eval_rag_quality --variants baseline`
   - Fails if any metric drops below threshold

### Output Report Example

```
=== RAG QUALITY EVALUATION =======================================

Variant: baseline  |  Date: 2026-07-19
──────────────────────────────────────────────────────────────
Scenario                     Difficulty   HitRate  MRR    P@5   R@5  
──────────────────────────────────────────────────────────────
identity_city_profession     easy         1.000    1.000  1.000 1.000
semantic_job_query           hard         1.000    0.500  0.800 1.000
mixing_signal_weak           hard         1.000    1.000  0.600 1.000
──────────────────────────────────────────────────────────────
AVERAGE                      ─            1.000    0.833  0.800 1.000

BEST SCENARIO:  identity_city_profession (MRR=1.000)
WORST SCENARIO: semantic_job_query (MRR=0.500)

ENTITY RECALL: 0.857 (6/7 entities matched)
NOT-RETRIEVED RATE: 0.033 (1/30 facts wrongly retrieved)

══ VARIANT COMPARISON (before vs after) ═══════════════════════

Metric         Before  After   Δ       
──────────────────────────────────────
Avg MRR        0.720   0.833   +0.113  ↑
Avg Precision  0.650   0.800   +0.150  ↑
Avg Recall     0.920   1.000   +0.080  ↑
Entity Recall  0.714   0.857   +0.143  ↑

VERDICT: CHANGE IS AN IMPROVEMENT ✓
══════════════════════════════════════════════════════════════════
```

## Recommendation

**Do this.** It's the missing piece to close the loop between "I made a change" and "I know if it helped."

The seed + test script we just built is the foundation — it proves the facts can be loaded, queried, and scored. The next step is to:
1. Define the ground-truth dataset (20-30 query/fact pairs)
2. Build the evaluator that scores retrieval against it
3. Add the Makefile target

The existing `make eval` (prompt quality) and this proposed `make eval-rag` (retrieval quality) would form a comprehensive quality framework — one tests the replies, the other tests whether the LLM got the right context to begin with.
