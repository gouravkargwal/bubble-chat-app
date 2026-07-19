-- Fact source tracking for [CONFIRMED] vs [INFERRED] labels.
--
-- Tracks whether a fact was explicitly stated by the user ("explicit")
-- or inferred by the LLM from their profile/photos ("inferred").
-- This lets the generator prompt distinguish between confirmed knowledge
-- and educated guesses, reducing hallucination risk.
--
-- Idempotent. Apply (dev):
--   docker compose exec -T postgres psql -U cookd -d cookd \
--     < docker/migrations/012_fact_source.sql

ALTER TABLE conversation_memories
    ADD COLUMN IF NOT EXISTS fact_source VARCHAR(20)
        DEFAULT 'explicit'
        CHECK (fact_source IN ('explicit', 'inferred'));
