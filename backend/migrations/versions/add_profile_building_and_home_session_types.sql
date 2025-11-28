-- Migration: Add profile_building and home session types
-- Date: 2025-11-05

-- Drop the existing constraint
ALTER TABLE conversation_sessions DROP CONSTRAINT IF EXISTS valid_session_type;

-- Add the new constraint with profile_building and home session types
ALTER TABLE conversation_sessions 
ADD CONSTRAINT valid_session_type CHECK (
    session_type IN ('chat', 'lesson', 'practice', 'quiz', 'review', 'profile_building', 'home')
);

