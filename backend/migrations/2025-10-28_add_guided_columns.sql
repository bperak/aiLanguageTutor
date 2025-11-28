-- Migration: Add guided dialogue columns to lesson_sessions

ALTER TABLE lesson_sessions
    ADD COLUMN IF NOT EXISTS guided_stage_idx SMALLINT,
    ADD COLUMN IF NOT EXISTS guided_state JSONB,
    ADD COLUMN IF NOT EXISTS guided_flushed_at TIMESTAMPTZ;

COMMENT ON COLUMN lesson_sessions.guided_stage_idx IS 'Current guided stage index for GuidedDialogueCard progression';
COMMENT ON COLUMN lesson_sessions.guided_state IS 'JSON state for guided dialogue (history, rubric results)';
COMMENT ON COLUMN lesson_sessions.guided_flushed_at IS 'Timestamp when guided state was last flushed/reset';


