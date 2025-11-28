-- Migration: Add lesson_sessions table for CanDo lesson session persistence
-- Purpose: Replace in-memory sessions with Postgres backend; track user progress across restarts

CREATE TABLE IF NOT EXISTS lesson_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    can_do_id TEXT NOT NULL,
    phase TEXT NOT NULL DEFAULT 'lexicon_and_patterns',
    completed_count INTEGER NOT NULL DEFAULT 0,
    scenario_json JSONB,
    master_json JSONB,
    variant_json JSONB,
    package_json JSONB,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP + INTERVAL '2 hours',
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Index for efficient session lookup and TTL cleanup
CREATE INDEX IF NOT EXISTS idx_lesson_sessions_can_do_id ON lesson_sessions(can_do_id);
CREATE INDEX IF NOT EXISTS idx_lesson_sessions_expires_at ON lesson_sessions(expires_at);
CREATE INDEX IF NOT EXISTS idx_lesson_sessions_created_at ON lesson_sessions(created_at);

-- Add comment for documentation
COMMENT ON TABLE lesson_sessions IS 'Persists active CanDo lesson sessions; sessions auto-expire after 2 hours (see expires_at).';
COMMENT ON COLUMN lesson_sessions.expires_at IS 'Session TTL: cleanup should delete records where expires_at < NOW().';
COMMENT ON COLUMN lesson_sessions.variant_json IS 'Sparse map of generated variants by level {level: variant_data}. Variants generated on-demand when requested.';
