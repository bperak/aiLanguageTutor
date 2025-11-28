-- Migration: Add profile completion tracking to users table
-- Date: 2025-01-XX

-- Add profile completion fields to users table
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS profile_completed BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS profile_completed_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS profile_skipped BOOLEAN DEFAULT FALSE;

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_users_profile_completed ON users(profile_completed);

-- Add comment for documentation
COMMENT ON COLUMN users.profile_completed IS 'Whether the user has completed the profile building process';
COMMENT ON COLUMN users.profile_completed_at IS 'Timestamp when profile was completed';
COMMENT ON COLUMN users.profile_skipped IS 'Whether the user skipped profile building for now';

