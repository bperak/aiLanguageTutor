-- Enable pgvector and extend lessons schema for versioned master + chunks

CREATE EXTENSION IF NOT EXISTS vector;

-- Add metadata columns to lesson_versions if not present
ALTER TABLE IF EXISTS lesson_versions
    ADD COLUMN IF NOT EXISTS master JSONB,
    ADD COLUMN IF NOT EXISTS entities JSONB,
    ADD COLUMN IF NOT EXISTS timings JSONB,
    ADD COLUMN IF NOT EXISTS pdf_path TEXT,
    ADD COLUMN IF NOT EXISTS source TEXT,
    ADD COLUMN IF NOT EXISTS context JSONB,
    ADD COLUMN IF NOT EXISTS parent_version INTEGER;

-- Create lesson_chunks table for vectorized retrieval
CREATE TABLE IF NOT EXISTS lesson_chunks (
    id BIGSERIAL PRIMARY KEY,
    lesson_id BIGINT NOT NULL REFERENCES lessons(id) ON DELETE CASCADE,
    version INTEGER NOT NULL,
    can_do_id TEXT NOT NULL,
    section TEXT NOT NULL,
    card_id TEXT,
    position INTEGER NOT NULL DEFAULT 0,
    lang TEXT NOT NULL,
    text TEXT NOT NULL,
    tokens INTEGER,
    embedding VECTOR(1536),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_lesson_chunks_lesson_ver ON lesson_chunks (lesson_id, version);
CREATE INDEX IF NOT EXISTS idx_lesson_chunks_cando ON lesson_chunks (can_do_id);
CREATE INDEX IF NOT EXISTS idx_lesson_chunks_section ON lesson_chunks (section);
-- HNSW index for pgvector (requires pgvector >= 0.5.0)
DO $$ BEGIN
    EXECUTE 'CREATE INDEX IF NOT EXISTS idx_lesson_chunks_embedding ON lesson_chunks USING hnsw (embedding vector_l2_ops)';
EXCEPTION WHEN OTHERS THEN
    -- fallback if hnsw not available; standard ivfflat
    BEGIN
        EXECUTE 'CREATE INDEX IF NOT EXISTS idx_lesson_chunks_embedding_ivf ON lesson_chunks USING ivfflat (embedding vector_l2_ops)';
    EXCEPTION WHEN OTHERS THEN
        -- ignore if vector index creation fails; can be created later
        NULL;
    END;
END $$;


