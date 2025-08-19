-- AI Language Tutor - Initial Database Schema
-- PostgreSQL initialization script for conversation and user data

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Enable vector extension for semantic search
CREATE EXTENSION IF NOT EXISTS vector;

-- Users table (extends basic auth with conversation preferences)
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Conversation preferences
    preferred_ai_provider VARCHAR(20) DEFAULT 'openai',
    conversation_style VARCHAR(20) DEFAULT 'balanced', -- casual, formal, balanced
    max_conversation_length INTEGER DEFAULT 50,
    auto_save_conversations BOOLEAN DEFAULT TRUE,
    
    -- Learning preferences
    target_languages TEXT[] DEFAULT ARRAY['ja'], -- ISO language codes
    proficiency_levels JSONB DEFAULT '{"ja": "beginner"}', -- language -> level mapping
    learning_goals TEXT[] DEFAULT ARRAY['conversation'], -- conversation, reading, writing, etc.
    daily_goal_minutes INTEGER DEFAULT 30,
    
    -- Privacy settings
    data_sharing_consent BOOLEAN DEFAULT FALSE,
    analytics_consent BOOLEAN DEFAULT TRUE,
    marketing_consent BOOLEAN DEFAULT FALSE,
    
    CONSTRAINT valid_conversation_style CHECK (conversation_style IN ('casual', 'formal', 'balanced')),
    CONSTRAINT valid_max_length CHECK (max_conversation_length > 0 AND max_conversation_length <= 200)
);

-- Conversation sessions
CREATE TABLE conversation_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255),
    language_code VARCHAR(10) NOT NULL DEFAULT 'ja', -- ISO language code
    session_type VARCHAR(20) NOT NULL DEFAULT 'chat', -- chat, lesson, practice, quiz
    status VARCHAR(20) DEFAULT 'active', -- active, completed, archived, deleted
    
    -- AI Configuration
    ai_provider VARCHAR(20) NOT NULL,
    ai_model VARCHAR(50) NOT NULL,
    system_prompt TEXT,
    conversation_context JSONB, -- Stores context like current lesson, difficulty level
    
    -- Learning context
    difficulty_level INTEGER DEFAULT 1 CHECK (difficulty_level >= 1 AND difficulty_level <= 5),
    topic_focus VARCHAR(100), -- grammar, vocabulary, culture, etc.
    learning_objectives TEXT[], -- Array of learning objectives for this session
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    
    -- Statistics
    total_messages INTEGER DEFAULT 0,
    user_messages INTEGER DEFAULT 0,
    ai_messages INTEGER DEFAULT 0,
    session_duration_seconds INTEGER DEFAULT 0,
    
    -- Privacy and retention
    anonymized BOOLEAN DEFAULT FALSE,
    retention_date DATE DEFAULT (CURRENT_DATE + INTERVAL '3 years'),
    
    -- Semantic search embeddings
    session_summary_embedding vector(1536), -- OpenAI embedding dimension
    session_summary TEXT, -- Summary for embedding generation
    
    CONSTRAINT valid_session_type CHECK (session_type IN ('chat', 'lesson', 'practice', 'quiz', 'review')),
    CONSTRAINT valid_status CHECK (status IN ('active', 'completed', 'archived', 'deleted')),
    CONSTRAINT valid_ai_provider CHECK (ai_provider IN ('openai', 'gemini', 'anthropic'))
);

-- Individual conversation messages
CREATE TABLE conversation_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES conversation_sessions(id) ON DELETE CASCADE,
    
    -- Message content
    role VARCHAR(20) NOT NULL, -- user, assistant, system
    content TEXT NOT NULL,
    content_type VARCHAR(20) DEFAULT 'text', -- text, audio, image, file
    original_content TEXT, -- Store original before any processing
    
    -- AI Generation metadata (for assistant messages)
    ai_provider VARCHAR(20),
    ai_model VARCHAR(50),
    tokens_used INTEGER,
    generation_time_ms INTEGER,
    confidence_score DECIMAL(3,2),
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    
    -- Learning analytics
    contains_correction BOOLEAN DEFAULT FALSE,
    grammar_points_mentioned TEXT[], -- Array of grammar point IDs from Neo4j
    vocabulary_introduced TEXT[], -- Array of new vocabulary
    difficulty_level INTEGER, -- 1-5 scale
    cultural_context_provided BOOLEAN DEFAULT FALSE,
    
    -- Language analysis
    detected_language VARCHAR(10),
    language_confidence DECIMAL(3,2),
    sentiment_score DECIMAL(3,2), -- -1 to 1
    formality_level VARCHAR(20), -- casual, neutral, formal
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    message_order INTEGER NOT NULL, -- Order within session
    edited BOOLEAN DEFAULT FALSE,
    edit_history JSONB, -- Store edit history
    
    -- Privacy
    anonymized BOOLEAN DEFAULT FALSE,
    anonymized_content TEXT, -- Anonymized version of content
    
    -- Semantic search
    content_embedding vector(1536), -- Content embedding for similarity search
    
    -- Constraints
    UNIQUE(session_id, message_order),
    CONSTRAINT valid_role CHECK (role IN ('user', 'assistant', 'system')),
    CONSTRAINT valid_content_type CHECK (content_type IN ('text', 'audio', 'image', 'file')),
    CONSTRAINT valid_confidence_score CHECK (confidence_score >= 0 AND confidence_score <= 1),
    CONSTRAINT valid_difficulty_level CHECK (difficulty_level >= 1 AND difficulty_level <= 5)
);

-- User learning interactions within conversations
CREATE TABLE conversation_interactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id UUID NOT NULL REFERENCES conversation_messages(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_id UUID NOT NULL REFERENCES conversation_sessions(id) ON DELETE CASCADE,
    
    -- Interaction type
    interaction_type VARCHAR(30) NOT NULL, -- question_asked, correction_received, concept_explained, practice_completed
    
    -- Learning data
    concept_id VARCHAR(100), -- Reference to Neo4j node ID
    concept_type VARCHAR(20), -- grammar_point, vocabulary, cultural_note, pronunciation
    user_response TEXT,
    is_correct BOOLEAN,
    attempts_count INTEGER DEFAULT 1,
    hint_used BOOLEAN DEFAULT FALSE,
    
    -- Spaced repetition integration
    ease_factor DECIMAL(3,2) DEFAULT 2.5,
    interval_days INTEGER DEFAULT 1,
    next_review_date DATE,
    mastery_level INTEGER DEFAULT 1 CHECK (mastery_level >= 1 AND mastery_level <= 5),
    
    -- Performance tracking
    response_time_seconds INTEGER,
    confidence_self_reported INTEGER CHECK (confidence_self_reported >= 1 AND confidence_self_reported <= 5),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT valid_interaction_type CHECK (interaction_type IN (
        'question_asked', 'correction_received', 'concept_explained', 
        'practice_completed', 'vocabulary_learned', 'grammar_practiced',
        'pronunciation_corrected', 'cultural_insight_shared'
    )),
    CONSTRAINT valid_concept_type CHECK (concept_type IN (
        'grammar_point', 'vocabulary', 'cultural_note', 'pronunciation', 
        'sentence_pattern', 'idiom', 'honorifics'
    ))
);

-- Conversation analytics and insights
CREATE TABLE conversation_analytics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES conversation_sessions(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Performance metrics
    words_per_minute DECIMAL(5,2),
    grammar_accuracy_percentage DECIMAL(5,2),
    vocabulary_usage_diversity INTEGER,
    conversation_flow_score DECIMAL(3,2),
    response_coherence_score DECIMAL(3,2),
    
    -- Learning progress
    new_concepts_learned INTEGER DEFAULT 0,
    concepts_reviewed INTEGER DEFAULT 0,
    mistakes_corrected INTEGER DEFAULT 0,
    cultural_insights_gained INTEGER DEFAULT 0,
    vocabulary_words_used INTEGER DEFAULT 0,
    grammar_patterns_practiced INTEGER DEFAULT 0,
    
    -- Engagement metrics
    session_engagement_score DECIMAL(3,2),
    user_initiative_count INTEGER, -- How often user started topics
    question_asking_frequency DECIMAL(3,2),
    average_response_time_seconds INTEGER,
    
    -- Language analysis
    language_complexity_level DECIMAL(3,2),
    formality_consistency_score DECIMAL(3,2),
    cultural_appropriateness_score DECIMAL(3,2),
    
    -- AI Performance metrics
    ai_response_relevance_score DECIMAL(3,2),
    ai_correction_accuracy_score DECIMAL(3,2),
    ai_explanation_clarity_score DECIMAL(3,2),
    
    analyzed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    analysis_version VARCHAR(10) DEFAULT '1.0', -- Track analytics algorithm version
    
    CONSTRAINT valid_percentage CHECK (
        grammar_accuracy_percentage >= 0 AND grammar_accuracy_percentage <= 100
    ),
    CONSTRAINT valid_scores CHECK (
        conversation_flow_score >= 0 AND conversation_flow_score <= 1 AND
        session_engagement_score >= 0 AND session_engagement_score <= 1 AND
        response_coherence_score >= 0 AND response_coherence_score <= 1
    )
);

-- User learning progress summary (aggregated data)
CREATE TABLE user_learning_progress (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    language_code VARCHAR(10) NOT NULL,
    
    -- Overall progress
    current_level VARCHAR(20) DEFAULT 'beginner', -- beginner, intermediate, advanced
    total_study_time_minutes INTEGER DEFAULT 0,
    total_conversations INTEGER DEFAULT 0,
    streak_days INTEGER DEFAULT 0,
    longest_streak_days INTEGER DEFAULT 0,
    
    -- Skill breakdown
    conversation_skill_level INTEGER DEFAULT 1 CHECK (conversation_skill_level >= 1 AND conversation_skill_level <= 10),
    grammar_skill_level INTEGER DEFAULT 1 CHECK (grammar_skill_level >= 1 AND grammar_skill_level <= 10),
    vocabulary_skill_level INTEGER DEFAULT 1 CHECK (vocabulary_skill_level >= 1 AND vocabulary_skill_level <= 10),
    pronunciation_skill_level INTEGER DEFAULT 1 CHECK (pronunciation_skill_level >= 1 AND pronunciation_skill_level <= 10),
    cultural_knowledge_level INTEGER DEFAULT 1 CHECK (cultural_knowledge_level >= 1 AND cultural_knowledge_level <= 10),
    
    -- Recent activity
    last_conversation_date DATE,
    last_study_session_date DATE,
    weekly_goal_minutes INTEGER DEFAULT 210, -- 30 min * 7 days
    weekly_progress_minutes INTEGER DEFAULT 0,
    
    -- Achievements
    achievements_earned TEXT[] DEFAULT ARRAY[]::TEXT[],
    badges_earned TEXT[] DEFAULT ARRAY[]::TEXT[],
    milestones_reached TEXT[] DEFAULT ARRAY[]::TEXT[],
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(user_id, language_code)
);

-- Indexes for optimal query performance
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_active ON users(is_active) WHERE is_active = TRUE;

CREATE INDEX idx_conversation_sessions_user_id ON conversation_sessions(user_id);
CREATE INDEX idx_conversation_sessions_language ON conversation_sessions(language_code);
CREATE INDEX idx_conversation_sessions_status ON conversation_sessions(status);
CREATE INDEX idx_conversation_sessions_created_at ON conversation_sessions(created_at DESC);
CREATE INDEX idx_conversation_sessions_user_active ON conversation_sessions(user_id, status) WHERE status = 'active';

CREATE INDEX idx_conversation_messages_session_id ON conversation_messages(session_id);
CREATE INDEX idx_conversation_messages_order ON conversation_messages(session_id, message_order);
CREATE INDEX idx_conversation_messages_role ON conversation_messages(role);
CREATE INDEX idx_conversation_messages_created_at ON conversation_messages(created_at DESC);
CREATE INDEX idx_conversation_messages_content_search ON conversation_messages USING gin(to_tsvector('english', content));

CREATE INDEX idx_conversation_interactions_user_id ON conversation_interactions(user_id);
CREATE INDEX idx_conversation_interactions_message_id ON conversation_interactions(message_id);
CREATE INDEX idx_conversation_interactions_concept ON conversation_interactions(concept_id, concept_type);
CREATE INDEX idx_conversation_interactions_review_date ON conversation_interactions(next_review_date) WHERE next_review_date IS NOT NULL;
CREATE INDEX idx_conversation_interactions_session_id ON conversation_interactions(session_id);

CREATE INDEX idx_conversation_analytics_user_id ON conversation_analytics(user_id);
CREATE INDEX idx_conversation_analytics_session_id ON conversation_analytics(session_id);
CREATE INDEX idx_conversation_analytics_analyzed_at ON conversation_analytics(analyzed_at DESC);

CREATE INDEX idx_user_learning_progress_user_id ON user_learning_progress(user_id);
CREATE INDEX idx_user_learning_progress_language ON user_learning_progress(language_code);
CREATE INDEX idx_user_learning_progress_last_activity ON user_learning_progress(last_conversation_date DESC);

-- Vector similarity indexes for semantic search
CREATE INDEX idx_conversation_sessions_embedding ON conversation_sessions 
USING ivfflat (session_summary_embedding vector_cosine_ops)
WITH (lists = 100);

CREATE INDEX idx_conversation_messages_embedding ON conversation_messages 
USING ivfflat (content_embedding vector_cosine_ops)
WITH (lists = 100);

-- Triggers for automatic timestamp updates
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_users_updated_at 
    BEFORE UPDATE ON users 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_conversation_sessions_updated_at 
    BEFORE UPDATE ON conversation_sessions 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_learning_progress_updated_at 
    BEFORE UPDATE ON user_learning_progress 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Function to automatically update conversation session statistics
CREATE OR REPLACE FUNCTION update_conversation_session_stats()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE conversation_sessions 
        SET 
            total_messages = total_messages + 1,
            user_messages = CASE WHEN NEW.role = 'user' THEN user_messages + 1 ELSE user_messages END,
            ai_messages = CASE WHEN NEW.role = 'assistant' THEN ai_messages + 1 ELSE ai_messages END,
            updated_at = NOW()
        WHERE id = NEW.session_id;
        RETURN NEW;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_session_stats_trigger
    AFTER INSERT ON conversation_messages
    FOR EACH ROW
    EXECUTE FUNCTION update_conversation_session_stats();

-- Create materialized view for user conversation summary
CREATE MATERIALIZED VIEW user_conversation_summary AS
SELECT 
    u.id as user_id,
    u.username,
    COUNT(DISTINCT cs.id) as total_sessions,
    COUNT(cm.id) as total_messages,
    COUNT(CASE WHEN cm.role = 'user' THEN 1 END) as user_messages,
    COUNT(CASE WHEN cm.role = 'assistant' THEN 1 END) as ai_messages,
    COUNT(DISTINCT cs.language_code) as languages_practiced,
    AVG(ca.session_engagement_score) as avg_engagement_score,
    MAX(cs.created_at) as last_conversation_date,
    SUM(cs.session_duration_seconds) as total_study_time_seconds
FROM users u
LEFT JOIN conversation_sessions cs ON u.id = cs.user_id
LEFT JOIN conversation_messages cm ON cs.id = cm.session_id
LEFT JOIN conversation_analytics ca ON cs.id = ca.session_id
WHERE u.is_active = TRUE
GROUP BY u.id, u.username;

-- Create unique index for materialized view
CREATE UNIQUE INDEX idx_user_conversation_summary_user_id ON user_conversation_summary(user_id);

-- Function to refresh materialized view
CREATE OR REPLACE FUNCTION refresh_user_conversation_summary()
RETURNS TRIGGER AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY user_conversation_summary;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Trigger to refresh summary when conversations are updated
CREATE TRIGGER refresh_conversation_summary_trigger
    AFTER INSERT OR UPDATE OR DELETE ON conversation_sessions
    FOR EACH STATEMENT
    EXECUTE FUNCTION refresh_user_conversation_summary();

-- Insert default admin user for testing
INSERT INTO users (username, email, hashed_password, is_verified) 
VALUES ('admin', 'admin@ailanguagetutor.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj1fq2LgNW6G', TRUE)
ON CONFLICT (email) DO NOTHING;

-- Insert sample data for development
INSERT INTO users (username, email, hashed_password, is_verified, target_languages, proficiency_levels) 
VALUES (
    'testuser', 
    'test@example.com', 
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj1fq2LgNW6G', 
    TRUE,
    ARRAY['ja', 'ko'],
    '{"ja": "intermediate", "ko": "beginner"}'::jsonb
)
ON CONFLICT (email) DO NOTHING;
