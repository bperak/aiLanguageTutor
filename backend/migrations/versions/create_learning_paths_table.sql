-- Migration: Create learning_paths table with versioning support
-- Date: 2025-01-XX

-- Create learning_paths table
CREATE TABLE IF NOT EXISTS learning_paths (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Versioning
    version INTEGER NOT NULL DEFAULT 1,
    path_name VARCHAR(255) NOT NULL DEFAULT 'Initial Path',
    
    -- Path data (structured JSONB)
    path_data JSONB NOT NULL DEFAULT '{}',
    progress_data JSONB DEFAULT '{}',
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    superseded_by UUID REFERENCES learning_paths(id) ON DELETE SET NULL,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT unique_user_active_path UNIQUE (user_id, is_active) DEFERRABLE INITIALLY DEFERRED
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_learning_paths_user_id ON learning_paths(user_id);
CREATE INDEX IF NOT EXISTS idx_learning_paths_user_active ON learning_paths(user_id, is_active) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_learning_paths_created_at ON learning_paths(created_at DESC);

-- Function to ensure only one active path per user
CREATE OR REPLACE FUNCTION ensure_single_active_path()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.is_active = TRUE THEN
        -- Deactivate other active paths for this user
        UPDATE learning_paths
        SET is_active = FALSE, updated_at = NOW()
        WHERE user_id = NEW.user_id
          AND id != NEW.id
          AND is_active = TRUE;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to enforce single active path
DROP TRIGGER IF EXISTS trigger_ensure_single_active_path ON learning_paths;
CREATE TRIGGER trigger_ensure_single_active_path
    BEFORE INSERT OR UPDATE ON learning_paths
    FOR EACH ROW
    EXECUTE FUNCTION ensure_single_active_path();

-- Add comments for documentation
COMMENT ON TABLE learning_paths IS 'Personalized learning paths with versioning support';
COMMENT ON COLUMN learning_paths.version IS 'Version number, auto-incremented per user';
COMMENT ON COLUMN learning_paths.path_data IS 'Structured learning path with steps, milestones, estimated durations';
COMMENT ON COLUMN learning_paths.progress_data IS 'Track completed steps and current position';
COMMENT ON COLUMN learning_paths.superseded_by IS 'If this path was replaced by a newer version';

