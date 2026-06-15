-- Sticky photo_persona: the curated-aesthetic read from her photos, captured at
-- the opener (rich photos) and carried forward into later chat turns where photos
-- aren't visible, so the coach's tone stays matched to her vibe.
--
-- Idempotent. Apply (dev):
--   docker compose exec -T postgres psql -U cookd -d cookd \
--     < docker/migrations/004_photo_persona.sql

ALTER TABLE conversations
    ADD COLUMN IF NOT EXISTS photo_persona VARCHAR(64) NOT NULL DEFAULT '';
