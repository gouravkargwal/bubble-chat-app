# RAG Pipeline Seed & Test Script — Plan

## Goal

Create a standalone Python script that:

1. **Seeds** the database with realistic test data (user, conversation, facts with embeddings, interactions, graph entities/edges)
2. **Runs the RAG read pipeline** (`get_match_context()`) with a test query and verifies retrieval
3. **Runs the RAG write pipeline** (`upsert_conversation_memory()`) with a new fact and verifies persistence
4. Reports results clearly so we can validate the pipeline works end-to-end

## Script Location

`backend/scripts/seed_and_test_rag.py` — runnable as `python -m scripts.seed_and_test_rag`

## Seed Data

### 1. Base entities

| Table | Data |
|-------|------|
| `users` | 1 test user (static UUID: `test-user-rag-0000-0000-000000000001`) |
| `conversations` | 1 test conversation linked to the user, person_name="Priya" |
| `interactions` | 3-5 mock chat interactions with `transcript_json` showing back-and-forth Hinglish chat |

### 2. Conversation memories (facts with embeddings)

10 facts covering identity, preferences, opinions, and factual details:

| Fact text | Category | Importance |
|-----------|----------|------------|
| "Priya is 26 years old from Mumbai" | identity | 5 |
| "Priya works as a software engineer at a fintech startup" | identity | 5 |
| "She is a vegetarian" | preference | 4 |
| "She loves trekking and has been to Himachal 3 times" | opinion | 3 |
| "She has a younger sister who is studying in Delhi" | identity | 4 |
| "She speaks Marathi, Hindi, and English fluently" | factual | 3 |
| "She is looking for a serious relationship" | opinion | 4 |
| "She enjoys trying new cafes in Bandra" | opinion | 3 |
| "She recently adopted a stray puppy named Chiku" | factual | 3 |
| "She studied at NMIMS Mumbai" | identity | 4 |

Each fact gets a real embedding via `embed_text()` (or a mock 768-dim vector if API is unavailable).

### 3. Graph entities and edges

Entities extracted from the facts:
- `Priya` (person), `Mumbai` (location), `Software Engineer` (profession), `Fintech` (organization)
- `Himachal` (location), `NMIMS Mumbai` (organization), `Chiku` (pet)
- `Marathi`, `Hindi`, `English` (languages)

Edges:
- `(Priya) -[LIVES_IN]-> (Mumbai)`
- `(Priya) -[WORKS_AS]-> (Software Engineer)`
- `(Priya) -[STUDIED_AT]-> (NMIMS Mumbai)`
- `(Priya) -[SPEAKS]-> (Marathi)`, etc.

## Test Flow

### Phase 1: Seed Database

```
seed_user_and_conversation()
seed_interactions()
seed_conversation_memories()    # parallel: embed + insert 10 facts
seed_graph_entities_and_edges()
```

### Phase 2: Test Read Pipeline

Run `get_match_context()` with different query types:

| Test | Query | Expected |
|------|-------|----------|
| Identity query | "what does priya do and where is she from" | Returns city + profession facts |
| Preference query | "does she like trekking" | Returns trekking fact |
| Null/empty query | "" | Falls back to chronological load |
| Exact match | "works as a software engineer" | Finds exact match via vector search |
| Semantic match | "job in tech" | Finds profession via vector similarity |

Verify:
- `core_lore` is non-empty and contains relevant facts
- `tier_1_raw_exchanges` is non-empty (from seeded interactions)
- `tier_2_summary` is non-empty
- `person_name` matches "Priya"
- Graph context is appended when available

### Phase 3: Test Write Pipeline

1. Generate a new durable fact: "Priya is planning a trip to Goa next month"
2. Call `upsert_conversation_memory()` with it
3. Verify:
   - Fact is inserted into `conversation_memories`
   - Embedding is stored
   - Importance score + category are set (from LLM or fallback)
   - Lexical expansion is generated
   - Graph entities (Goa, etc.) are inserted
4. Call `get_match_context()` with "goa trip next month"
5. Verify the new fact is retrieved

### Phase 4: Report

Print a structured report like:

```
=== RAG PIPELINE TEST REPORT =================================

[SEED]      ✓ User created (test-user-rag-...)
[SEED]      ✓ Conversation created (conv-rag-test-...)
[SEED]      ✓ 5 interactions seeded
[SEED]      ✓ 10 facts + embeddings stored
[SEED]      ✓ 6 entities + 8 edges stored

[READ]      ✓ Identity query: 3 facts retrieved (expected ≥ 1)
[READ]      ✓ Preference query: 1 fact retrieved (expected ≥ 1)
[READ]      ✓ Empty query: fell back to chronological (5 facts)
[READ]      ✓ Exact match: found via vector search
[READ]      ✓ Semantic match: found via similarity
[READ]      ✓ Tier 1 raw exchanges: non-empty (5 exchanges)
[READ]      ✓ Tier 2 summary: non-empty
[READ]      ✓ Graph context: 2 triples found

[WRITE]     ✓ Fact inserted: "Priya is planning a trip to Goa..."
[WRITE]     ✓ Importance: 4 (preference)
[WRITE]     ✓ Lexical expansion generated
[WRITE]     ✓ Entity "Goa" created
[WRITE]     ✓ Re-query returns new fact

================================================================
RESULT: 15/15 tests PASSED
================================================================
```

## Edge Cases & Error Handling

| Scenario | Handling |
|----------|----------|
| No Gemini API key | Skip LLM-dependent tests; use heuristic fallback for importance |
| Embedding API fails | Use mock 768-dim vector; log warning |
| DB connection fails | Print clear error; exit with code 1 |
| Missing `lexical_expansion` column | Graceful skip (some migrations may not be applied) |
| Missing graph tables | Graceful skip |
| Script run multiple times | `ON CONFLICT DO NOTHING` / idempotent inserts |

## Dependencies

All already in `pyproject.toml`:
- `sqlalchemy[asyncio]`, `asyncpg`, `pgvector` — DB
- `google-genai` — embeddings (fallback to mock)
- `structlog` — logging
- `pydantic` — schemas

No new dependencies needed.

## How to Run

```bash
# Ensure PostgreSQL is running (via docker compose)
docker compose up -d postgres

# Copy .env.example to .env.dev and set GEMINI_API_KEY
cp .env.example .env.dev  # then edit GEMINI_API_KEY

# Run the seed + test script
ENV_FILE=.env.dev python -m scripts.seed_and_test_rag

# Or skip LLM-dependent tests (mock embeddings + heuristic fallback):
ENV_FILE=.env.dev python -m scripts.seed_and_test_rag --no-llm
```

## Files to Create

1. `backend/scripts/__init__.py` — empty init (if it doesn't exist)
2. `backend/scripts/seed_and_test_rag.py` — the main script (~400-500 lines)

## Files to Read (already done)

- `backend/app/services/memory_service.py` — `get_match_context()`, `upsert_conversation_memory()`
- `backend/app/core/embeddings.py` — `embed_text()`
- `backend/app/core/reranker.py` — `rerank_passages()`
- `backend/app/services/rag_improvements.py` — utilities
- `backend/app/infrastructure/database/engine.py` — `async_session`
- `backend/app/infrastructure/database/models.py` — ORM models
- `backend/scripts/eval_rag.py` — existing evaluation script (reference for patterns)
- `backend/app/config.py` — `Settings`
