-- Graph RAG: Entity nodes and directional edges for multi-hop knowledge retrieval.
--
-- Entities store concrete nouns (person, profession, location, hobby, etc.)
-- extracted by Gemini structured outputs from conversational facts.
-- Edges store directional relationships (WORKS_AS, PLAYS, LIVES_IN, etc.)
-- between entities within the same conversation.
--
-- Recursive CTE traversals on these tables resolve multi-hop graph paths
-- (e.g., name → college → profession) in a single DB round-trip.
--
-- Idempotent. Apply (dev):
--   docker compose exec -T postgres psql -U cookd -d cookd \
--     < docker/migrations/005_graph_rag.sql

CREATE TABLE IF NOT EXISTS conversation_memory_entities (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id),
    conversation_id VARCHAR(36) NOT NULL REFERENCES conversations(id),
    entity_name VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    CONSTRAINT unique_conversation_entity UNIQUE (conversation_id, entity_name)
);

CREATE INDEX IF NOT EXISTS ix_graph_entities_lookup
    ON conversation_memory_entities (conversation_id, entity_name);

CREATE TABLE IF NOT EXISTS conversation_memory_edges (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id),
    conversation_id VARCHAR(36) NOT NULL REFERENCES conversations(id),
    source_entity_id VARCHAR(36) NOT NULL
        REFERENCES conversation_memory_entities(id) ON DELETE CASCADE,
    target_entity_id VARCHAR(36) NOT NULL
        REFERENCES conversation_memory_entities(id) ON DELETE CASCADE,
    relationship_type VARCHAR(50) NOT NULL,
    weight FLOAT DEFAULT 1.0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    CONSTRAINT unique_conversation_edge
        UNIQUE (conversation_id, source_entity_id, target_entity_id, relationship_type)
);

CREATE INDEX IF NOT EXISTS ix_graph_edges_lookup
    ON conversation_memory_edges (conversation_id, source_entity_id);
