-- Migration: Create user_profiles table for detailed profile information
-- Date: 2025-01-XX

-- Create user_profiles table
CREATE TABLE IF NOT EXISTS user_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    
    -- Profile data (structured JSONB)
    previous_knowledge JSONB DEFAULT '{}',
    learning_experiences JSONB DEFAULT '{}',
    usage_context JSONB DEFAULT '{}',
    learning_goals JSONB DEFAULT '[]',
    additional_notes TEXT,
    
    -- Link to conversation where profile was built
    profile_building_conversation_id UUID REFERENCES conversation_sessions(id) ON DELETE SET NULL,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_user_profiles_user_id ON user_profiles(user_id);
CREATE INDEX IF NOT EXISTS idx_user_profiles_created_at ON user_profiles(created_at DESC);

-- Add comments for documentation
COMMENT ON TABLE user_profiles IS 'Detailed profile information collected via chatbot conversation';
COMMENT ON COLUMN user_profiles.previous_knowledge IS 'Structured data about previous learning experiences';
COMMENT ON COLUMN user_profiles.learning_experiences IS 'Past learning methods and preferences';
COMMENT ON COLUMN user_profiles.usage_context IS 'Where and when user wants to use target language';
COMMENT ON COLUMN user_profiles.learning_goals IS 'Detailed learning goals extracted from conversation';

