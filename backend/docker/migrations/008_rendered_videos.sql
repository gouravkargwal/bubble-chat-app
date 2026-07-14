-- Rendered videos CRUD table for admin video pipeline.
-- Tracks video exports with status, file path, and source interaction.

CREATE TABLE IF NOT EXISTS rendered_videos (
    id VARCHAR(36) PRIMARY KEY,
    interaction_id VARCHAR(36) REFERENCES interactions(id) ON DELETE SET NULL,
    person_name VARCHAR(128) NOT NULL DEFAULT 'Someone',
    winning_line TEXT NOT NULL DEFAULT '',
    strategy_label VARCHAR(64) NOT NULL DEFAULT 'COOKD_AI',
    hook_style VARCHAR(32) NOT NULL DEFAULT 'strategy',
    viral_score INTEGER NOT NULL DEFAULT 0,
    file_path VARCHAR(512) NOT NULL DEFAULT '',
    file_size_bytes INTEGER NOT NULL DEFAULT 0,
    content_type VARCHAR(64) NOT NULL DEFAULT 'video/mp4',
    status VARCHAR(20) NOT NULL DEFAULT 'completed',
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_rendered_videos_interaction_id ON rendered_videos(interaction_id);
CREATE INDEX idx_rendered_videos_status ON rendered_videos(status);
CREATE INDEX idx_rendered_videos_created_at ON rendered_videos(created_at DESC);
