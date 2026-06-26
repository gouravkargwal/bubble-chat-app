-- Learned Sparse Retrieval: write-time lexical token expansion column + GIN index.
--
-- The lexical_expansion column stores LLM-generated synonyms, cross-lingual
-- translations (English ↔ Hinglish), and conceptual expansions that feed into
-- PostgreSQL's full-text search.  This solves dialect-blindness without a
-- dedicated SPLADE GPU service.
--
-- Idempotent. Apply (dev):
--   docker compose exec -T postgres psql -U cookd -d cookd \
--     < docker/migrations/006_lexical_expansion.sql

ALTER TABLE conversation_memories
    ADD COLUMN IF NOT EXISTS lexical_expansion TEXT DEFAULT '';

-- Combined GIN index: queries now search both raw fact_text AND the semantic
-- expansions in a single FTS scan.
CREATE INDEX IF NOT EXISTS idx_memories_expanded_fts
    ON conversation_memories
    USING gin(to_tsvector(
        'simple',
        fact_text || ' ' || COALESCE(lexical_expansion, '')
    ));
