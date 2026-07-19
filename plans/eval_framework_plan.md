# Eval Framework: Complete Measurement for RAG + Prompt Changes

## Overview

Two complementary evaluation systems that together measure every change in the RAG → prompt → reply chain:

```
RAG change (retrieval)  ──→  eval-rag  (MRR, HitRate, Precision)
                                  │
                                  ▼
                      Better context in prompt
                                  │
Prompt change (structure)  ──→  make eval  (LLM Judge scores)
                                  │
                                  ▼
                         Better reply quality
```

---

## Track 1: Add RAG Context to Existing `make eval`

**Goal:** Make the existing prompt evaluation actually exercise the RAG pipeline so prompt improvements are measured against real context.

### Current problem

Scenarios in [`scenarios.json`](backend/app/testing/scenarios/scenarios.json) define `their_last_message`, `direction`, `expected_tone` — but the runner passes **empty `core_lore`** to the generator. Changes to how context is formatted in the prompt have **zero effect** on eval scores.

### Changes needed

#### Step 1.1: Extend scenario schema

Add optional `facts` and `core_lore_facts` fields to [`Scenario`](backend/app/testing/scenarios/dataset.py:14):

```python
class Scenario(BaseModel):
    id: str
    category: str
    description: str
    their_last_message: str
    person_name: str = "unknown"
    direction: str
    expected_stage: str
    expected_tone: str
    detected_dialect: str = "ENGLISH"
    quality_criteria: QualityCriteria
    # NEW:
    facts: list[str] = []          # facts to seed into conversation_memories
    core_lore_facts: list[str] = []  # subset that should appear in core_lore
```

#### Step 1.2: Seed facts in TestRunner

Modify [`TestRunner._run_single()`](backend/app/testing/runner.py) to:
1. Before running the scenario, check if `scenario.facts` is non-empty
2. If so, seed them into the test DB using `upsert_conversation_memory()` (or direct SQL)
3. After seeding, call `get_match_context()` with the scenario's `their_last_message` as query
4. Pass the returned `core_lore` / `tier_1` / `tier_2` into the generator state

#### Step 1.3: Update scenarios with fact data

Add fact arrays to ~15 of the 50 existing scenarios. Example:

```json
{
  "id": "chemistry_pineapple_pizza_war_10",
  "facts": [
    "She is a graphic designer from Bangalore",
    "She has a dog named Olive",
    "She is a vegetarian who loves cooking Italian"
  ],
  "core_lore_facts": ["She is a vegetarian who loves cooking Italian"]
}
```

**Priority scenarios** (highest value for RAG testing):
- All `early_conversation` scenarios (6) — these benefit most from identity facts
- All `building_chemistry` scenarios (4) — these show whether RAG context helps maintain continuity
- A few `new_match` scenarios (3) — test opener context injection

#### Step 1.4: Add RAG quality score to report

Extend [`ScenarioResult`](backend/app/testing/runner.py:45) with:
```python
rag_hit_rate: float = 0.0   # was at least one core_lore_fact retrieved?
rag_precision: float = 0.0  # what fraction of retrieved facts are relevant?
```

Show in report:
```
  chemistry_pineapple_pizza_war_10  judge=3.8/5  audit=✓  RAG-hit=1.0  RAG-prec=0.6
```

### Files to modify

| File | Change |
|------|--------|
| [`backend/app/testing/scenarios/dataset.py`](backend/app/testing/scenarios/dataset.py) | Add `facts` + `core_lore_facts` fields to `Scenario` |
| [`backend/app/testing/scenarios/scenarios.json`](backend/app/testing/scenarios/scenarios.json) | Add fact data to ~15 scenarios |
| [`backend/app/testing/runner.py`](backend/app/testing/runner.py) | Seed facts + call `get_match_context()` before each run |
| [`backend/app/testing/reporter.py`](backend/app/testing/reporter.py) | Show RAG metrics in report |

**Estimated effort:** 4-5 hours

---

## Track 2: Build `make eval-rag` Pipeline

**Goal:** Measure retrieval quality independently of reply quality — so RAG engine changes (reranker, MMR, graph depth) can be A/B tested.

### Step 2.1: Create RAG-specific scenario dataset

New file: [`backend/app/testing/scenarios/scenarios_rag.json`](backend/app/testing/scenarios/scenarios_rag.json)

~25 scenarios across 3 difficulty levels:

| Difficulty | Count | Example |
|-----------|-------|---------|
| **easy** | 10 | Exact keyword match between query and fact text |
| **medium** | 8 | Semantic match — synonyms, different phrasing |
| **hard** | 7 | Multi-fact ranking — distractor facts present, must pick correct ones |

Each scenario:
```json
{
  "id": "semantic_job_query",
  "difficulty": "hard",
  "description": "Query uses synonyms with no word overlap to fact text",
  "facts": [
    "Priya works as a software engineer at a fintech startup"
  ],
  "query": "what is her profession",
  "expected_fact_texts": [
    "Priya works as a software engineer at a fintech startup"
  ]
}
```

### Step 2.2: Build RAGEvaluator

New file: [`backend/app/testing/evaluators/rag_evaluator.py`](backend/app/testing/evaluators/rag_evaluator.py)

```python
@dataclass
class RAGScenarioResult:
    scenario_id: str
    variant_id: str
    hit_rate: float          # 1.0 if any expected fact in top-K
    mrr: float               # reciprocal rank of first relevant fact
    precision_at_k: float    # relevant / total retrieved
    recall_at_k: float       # relevant / total relevant
    entity_recall: float     # expected graph entities found
    not_retrieved_rate: float # wrong facts / total retrieved

class RAGEvaluator:
    async def evaluate(
        self, scenarios: list[dict], variant_id: str
    ) -> list[RAGScenarioResult]:
        for scenario in scenarios:
            # 1. Seed facts into DB (reuse helpers from seed_and_test_rag.py)
            # 2. Call get_match_context(db, query=scenario.query, ...)
            # 3. Score core_lore against expected_fact_texts
            # 4. Yield RAGScenarioResult
```

### Step 2.3: CLI entry point

New file: [`backend/scripts/eval_rag_quality.py`](backend/scripts/eval_rag_quality.py)

```python
"""
python -m scripts.eval_rag_quality
python -m scripts.eval_rag_quality --variants before after
python -m scripts.eval_rag_quality --difficulty hard
"""
```

Output:
```
=== RAG QUALITY EVALUATION =======================================

Variant: baseline  |  Date: 2026-07-19
──────────────────────────────────────────────────────────────
Scenario                     Difficulty   HitRate  MRR    P@5   R@5  
──────────────────────────────────────────────────────────────
identity_city_profession     easy         1.000    1.000  1.000 1.000
semantic_job_query           hard         1.000    0.500  0.800 1.000
──────────────────────────────────────────────────────────────
AVERAGE                      ─            1.000    0.833  0.800 1.000

══ VARIANT COMPARISON ════════════════════════════════════════
Metric         Before  After   Δ       
──────────────────────────────────────
Avg MRR        0.720   0.833   +0.113  ↑
Avg Precision  0.650   0.800   +0.150  ↑
VERDICT: IMPROVEMENT ✓
```

### Step 2.4: Add to Makefile

```makefile
eval-rag:
	python -m scripts.eval_rag_quality

eval-rag-diff:
	python -m scripts.eval_rag_quality --variants before after

eval-rag-cache-clear:
	python -c "import sqlite3; c=sqlite3.connect('app/testing/eval_cache.db'); c.execute('DELETE FROM eval_results WHERE variant_id LIKE \"rag_%\"'); c.commit()"
```

### Step 2.5: Wire into seed_and_test_rag.py

The seed helpers we already built (`_seed_facts`, `_seed_graph`, `_seed_user_and_conversation`, `_seed_interactions`) can be moved to a shared module or directly imported by the RAG evaluator.

**Recommended:** Extract seed helpers into [`backend/app/testing/rag_seed_helpers.py`](backend/app/testing/rag_seed_helpers.py) so both the seed+test script and the evaluator can use them.

### Files to create

| File | Purpose |
|------|---------|
| [`backend/app/testing/scenarios/scenarios_rag.json`](backend/app/testing/scenarios/scenarios_rag.json) | 25 RAG-specific ground-truth scenarios |
| [`backend/app/testing/evaluators/rag_evaluator.py`](backend/app/testing/evaluators/rag_evaluator.py) | `RAGEvaluator` class with metric scoring |
| [`backend/scripts/eval_rag_quality.py`](backend/scripts/eval_rag_quality.py) | CLI entry point with variant support |
| [`backend/app/testing/rag_seed_helpers.py`](backend/app/testing/rag_seed_helpers.py) | Shared seed functions (extracted from seed_and_test_rag.py) |

### Files to modify

| File | Change |
|------|--------|
| [`backend/scripts/seed_and_test_rag.py`](backend/scripts/seed_and_test_rag.py) | Import shared seed helpers from `app.testing.rag_seed_helpers` |
| [`backend/Makefile`](backend/Makefile) | Add `eval-rag`, `eval-rag-diff`, `eval-rag-cache-clear` targets |

**Estimated effort:** 5-6 hours

---

## Combined Timeline

| Phase | Tasks | Effort | Depends on |
|-------|-------|--------|------------|
| **P0** | Extract seed helpers to shared module | 1h | — |
| **P1** | Build `eval-rag` pipeline (dataset + evaluator + CLI) | 5-6h | P0 |
| **P2** | Add RAG context to existing `make eval` | 4-5h | P0 |
| **Total** | | **10-12h** | |

## How to Run After Implementation

```bash
# --- Retrieval quality (RAG engine changes) ---
make eval-rag-before          # baseline
# ... tweak reranker lambda, graph depth, etc. ...
make eval-rag-after           # after changes
make eval-rag-diff            # compare → "MRR: 0.72 → 0.85 ↑"

# --- Reply quality (prompt changes) ---
make eval-before              # baseline
# ... restructure context formatting in prompt ...
make eval-after               # after changes
make eval-diff                # compare → "Judge score: 3.2 → 3.7 ↑"
```

Now you can objectively measure BOTH retrieval quality AND reply quality, and know which changes actually move the needle.
