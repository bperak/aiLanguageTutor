-- Enable pgvector extension if not already enabled
CREATE EXTENSION IF NOT EXISTS vector;

-- Add textsearch column for hybrid search (materialized tsvector for better performance)
ALTER TABLE conversation_messages 
ADD COLUMN IF NOT EXISTS textsearch tsvector;

-- Create GIN index on textsearch column for full-text search
CREATE INDEX IF NOT EXISTS idx_conversation_messages_textsearch 
ON conversation_messages USING gin(textsearch);

-- Create HNSW index on content_embedding (better performance than ivfflat)
-- Try HNSW first, fallback to ivfflat if HNSW not available
DO $$ 
BEGIN
    -- Try to create HNSW index
    EXECUTE 'CREATE INDEX IF NOT EXISTS idx_conversation_messages_embedding_hnsw 
             ON conversation_messages USING hnsw (content_embedding vector_cosine_ops)';
EXCEPTION WHEN OTHERS THEN
    -- Fallback: keep existing ivfflat index or create if doesn't exist
    BEGIN
        -- Only create ivfflat if HNSW failed and index doesn't exist
        IF NOT EXISTS (
            SELECT 1 FROM pg_indexes 
            WHERE indexname = 'idx_conversation_messages_embedding'
        ) THEN
            EXECUTE 'CREATE INDEX idx_conversation_messages_embedding 
                     ON conversation_messages USING ivfflat (content_embedding vector_cosine_ops)
                     WITH (lists = 100)';
        END IF;
    EXCEPTION WHEN OTHERS THEN
        -- Ignore if index creation fails
        NULL;
    END;
END $$;

-- Create function to update textsearch column
CREATE OR REPLACE FUNCTION update_conversation_message_textsearch()
RETURNS TRIGGER AS $$
BEGIN
    NEW.textsearch := to_tsvector('english', COALESCE(NEW.content, ''));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to automatically update textsearch on insert/update
DROP TRIGGER IF EXISTS trigger_update_conversation_message_textsearch ON conversation_messages;
CREATE TRIGGER trigger_update_conversation_message_textsearch
    BEFORE INSERT OR UPDATE OF content ON conversation_messages
    FOR EACH ROW
    EXECUTE FUNCTION update_conversation_message_textsearch();

-- Backfill textsearch for existing messages (if any)
UPDATE conversation_messages 
SET textsearch = to_tsvector('english', COALESCE(content, ''))
WHERE textsearch IS NULL;

