# RAG Pipeline Assessment & Reply Quality Improvement

## 1. Is the RAG Pipeline Production-Ready?

**Short answer: Yes, the retrieval engine itself is solid.** Here's why:

### Strengths (what's already good)

| Component | Why it's production-grade |
|-----------|--------------------------|
| **Multi-strategy retrieval** | Vector (pgvector 768d) + Lexical (GIN tsvector) + Recency (14d half-life decay) + Importance boost — fused via RRF. Covers semantic gaps and matches real-world usage. |
| **Write-time LLM enrichment** | Each fact gets 3 LLM calls (importance score, lexical expansions, graph triples) — this amortizes cost once at write time rather than paying per query. |
| **Cross-encoder reranker** | FlashRank `ms-marco-MiniLM-L-12-v2` on CPU — reranks top 150 results for zero API cost. |
| **MMR diversity** | Prevents the top-8 from being 8 variations of the same fact. |
| **Graph RAG** | Recursive CTE up to 2 hops — adds relationship context that pure vector search misses. |
| **3-tier memory** | Raw exchanges (Tier 1) + narrative summary (Tier 2) + semantic facts (core_lore) — gives the LLM both recent chat context AND durable user knowledge. |
| **Graceful degradation** | Falls back to chronological load when no query is available. All failures logged, never crash. |

### Weaknesses (what could break at scale)

| Issue | Risk | Mitigation |
|-------|------|------------|
| **3 LLM calls per fact write** | Cost: ~$0.003/fact (Gemini Flash). At 100 facts/user = $0.30/user. At 10K users = $3K. | Batch writes, cache expansions. But acceptable for current scale. |
| **FlashRank on CPU** | `ms-marco-MiniLM-L-12-v2` takes ~200ms per 150 passages on CPU. At high concurrency this adds latency. | Already offloaded to thread (`asyncio.to_thread`). Consider GPU inference or skip rerank under load. |
| **No cache layer** | Every request hits Postgres for the multi-CTE query. No Redis/memcached. | Add a write-through cache keyed by (user_id, conversation_id, query_hash). |
| **Graph CTE performance** | The recursive CTE uses `similarity()` trigram comparison with `CAST(:seeds AS text[])` — on a conversation with 100+ entities this can be slow. | Add a GIN trgm index on `entity_name`, or limit seed count. |
| **No query rewriting** | The query variants are just string manipulation (name prefix, keyword extraction). No LLM-based query rewriting. | Add a lightweight query rewrite step (e.g., extract key nouns). |
| **No negative feedback loop** | If a user never uses a fact in their reply, the system doesn't learn to deprioritize it. | Already has `log_retrieval_feedback()` table — but nothing consumes it to adjust importance scores. |

## 2. Can Reply Quality Be Improved?

**Yes — but the RAG pipeline is not the bottleneck.** The reply quality ceiling is set by:

### A. Prompt quality (biggest lever)

The generator prompt at [`generator.py`](backend/app/prompts/generator.py) passes `core_lore`, `tier_1_raw_exchanges`, and `tier_2_summary` into the LLM context. But looking at how they're used:

```python
# generator_node state → prompt builder (generator.py:167-169)
"core_lore": core_lore,
"tier_1_raw_exchanges": tier_1_raw,
"tier_2_summary": tier_2_summary,
```

The prompt template references these as:
- `core_lore` → "WHAT YOU ALREADY KNOW ABOUT HER from past chats (durable facts). Sound like you remember her."
- `tier_1_raw_exchanges` → "VERBATIM recent thread — her actual words and exactly what you already sent."
- `tier_2_summary` → "Compressed narrative of the recent conversation arc."

**Issues:**
1. **Context is all concatenated** into a blob — the LLM has to figure out which parts are relevant
2. **No priority ordering** — a critical identity fact (importance=5) sits beside a trivial opinion (importance=2)
3. **No differentiation between "confirmed" vs "inferred" facts** — the model treats everything as equally true
4. **RAG context length is unbounded** — if there are 50 facts, they all get dumped in

### B. Missing: personalization from historical usage

The system tracks which strategies work per archetype ([`ArchetypeStrategyStat`](backend/app/infrastructure/database/models.py:174)) but **does not track which FACTS the user actually used in their copied replies**. This means:
- If a user always ignores "she likes trekking" facts, they still appear every time
- No per-user importance calibration

### C. Missing: time-sensitive weighting

The recency decay (14-day half-life) helps, but there's **no event-driven importance boost**. For example:
- If she mentions a new job, the "works as X" fact should get a temporary boost
- If she says she's moving cities, old location facts should decay faster

## 3. Recommended Improvements (Highest Impact → Lowest)

### High Impact

1. **Structured context injection** — Instead of dumping core_lore as a blob, format it with labeled sections:
   ```
   --- Identity Facts (always true) ---
   - She's 26, from Mumbai
   - Works as a software engineer

   --- Preferences ---
   - Vegetarian
   - Loves trekking

   --- Recent Conversation ---
   [tier_1_raw_exchanges]
   ```
   This lets the LLM easily distinguish stable facts from current context. Estimated effort: **2-3 hours**.

2. **Importance-weighted truncation** — Before injecting into prompt, sort facts by importance_score descending and truncate at a token budget (e.g., 800 tokens), keeping category labels. This ensures critical identity facts are never cut. [`select_facts_within_budget()`](backend/app/services/rag_improvements.py:147) already exists but isn't called in the prompt assembly path. Estimated effort: **1 hour**.

3. **Retrieval feedback loop** — The [`log_retrieval_feedback()`](backend/app/services/rag_improvements.py:363) table exists but nothing reads it. Add a background job that:
   - Reads facts that were retrieved but marked `was_used=false`
   - Decrements their effective importance by 1 (floor of 1)
   - Facts with `was_used=true` get +0.5 importance (ceiling of 5)
   Estimated effort: **4-6 hours**.

### Medium Impact

4. **Multi-hop graph queries** — The graph CTE currently only traverses 2 hops. For a conversation with rich entity data, 3-hop traversal could uncover useful connections (e.g., "she works at fintech" + "fintech is in Bangalore" → "she might be based in Bangalore"). Estimated effort: **2 hours**.

5. **Query-time LLM rewriting** — Use a lightweight Gemini call to rewrite the raw OCR text into 2-3 clean search queries before embedding. The Vision node already does this via `rag_search_queries` — but only when a screenshot is uploaded. For Tier 1/2 context queries, the fallback `generate_query_variants()` is simplistic. Estimated effort: **3-4 hours**.

6. **Add Redis cache** — Cache `get_match_context()` results keyed by `(user_id, conversation_id, query_hash)` with 5-minute TTL. Users often send multiple screenshots of the same chat within minutes. Estimated effort: **4-6 hours**.

### Low Impact / Future

7. **Per-user importance calibration** — Learn from which facts the user actually copies into replies. Track `fact_copied` events and adjust per-user importance weights. Requires frontend changes.

8. **BNSR / ColBERT late interaction** — Replace the single-vector embedding with ColBERT-style token-level late interaction for better semantic matching. This requires GPU infrastructure.

9. **Automatic contradiction detection** — The current approach is "ADD-only memory" (see comment at [memory_service.py:651](backend/app/services/memory_service.py:651)). A safer contradiction model could use attribute-scoped replacement (e.g., only one "current city" fact, only one "relationship status"). This prevents stale facts from ranking high via recency.

## 4. Recommendation

**Don't touch the RAG retrieval pipeline.** It's well-engineered with proper fallbacks, diversity handling, and instrumentation. The test results confirm all retrieval paths work correctly.

**Invest in:**
1. **Prompt engineering** — structured context injection + importance-weighted truncation (highest ROI, ~3-4 hours of work)
2. **Feedback loop** — consume the `retrieval_feedback` table to auto-adjust importance scores
3. **Caching** — Redis for `get_match_context()` to reduce DB load

These three changes will improve reply quality more than any retrieval algorithm change, because the bottleneck today is not *finding* the right facts — it's presenting them to the LLM in a way that the LLM can effectively use.

---

*Want me to write a detailed implementation plan for any of these improvements?*
