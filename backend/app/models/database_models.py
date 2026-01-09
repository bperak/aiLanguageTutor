"""
Working database models that match the existing PostgreSQL schema exactly.
This replaces the problematic user.py models.
"""

from datetime import datetime, date
from typing import Optional, List
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON, ForeignKey, MetaData, Numeric, Date
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import uuid

# Use explicit metadata to ensure we work with existing schema
metadata = MetaData()
Base = declarative_base(metadata=metadata)


class User(Base):
    """User model that exactly matches the existing PostgreSQL table."""
    
    __tablename__ = "users"
    __table_args__ = {'extend_existing': True}  # Work with existing table
    
    # Columns exactly as they exist in the database
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False)
    username = Column(String(50), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default='now()')
    updated_at = Column(DateTime(timezone=True), server_default='now()')
    preferred_ai_provider = Column(String(20), default='openai')
    conversation_style = Column(String(20), default='balanced')
    max_conversation_length = Column(Integer, default=50)
    auto_save_conversations = Column(Boolean, default=True)
    target_languages = Column(ARRAY(Text), default=['ja'])
    proficiency_levels = Column(JSON, default={'ja': 'beginner'})
    learning_goals = Column(ARRAY(Text), default=['conversation'])
    daily_goal_minutes = Column(Integer, default=30)
    data_sharing_consent = Column(Boolean, default=False)
    analytics_consent = Column(Boolean, default=True)
    marketing_consent = Column(Boolean, default=False)
    # Profile-derived level (populated during profile building)
    current_level = Column(String(50), default="beginner")
    
    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, email={self.email})>"


class ConversationSession(Base):
    """Conversation session model."""
    
    __tablename__ = "conversation_sessions"
    __table_args__ = {'extend_existing': True}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    title = Column(String(255))
    language_code = Column(String(10), nullable=False)
    session_type = Column(String(20), nullable=False)
    status = Column(String(20))
    ai_provider = Column(String(20), nullable=False)
    ai_model = Column(String(50), nullable=False)
    system_prompt = Column(Text)
    conversation_context = Column(JSON)
    created_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    total_messages = Column(Integer)
    user_messages = Column(Integer)
    ai_messages = Column(Integer)
    session_duration_seconds = Column(Integer)
    
    # Relationships
    user = relationship("User")
    
    def __repr__(self):
        return f"<ConversationSession(id={self.id}, user_id={self.user_id}, type={self.session_type})>"


class ConversationMessage(Base):
    """Conversation message model aligned with existing schema."""

    __tablename__ = "conversation_messages"
    __table_args__ = {'extend_existing': True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("conversation_sessions.id"), nullable=False)

    # Message content
    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    content_type = Column(String(20))  # defaults handled by DB
    original_content = Column(Text)

    # AI Generation metadata
    ai_provider = Column(String(20))
    ai_model = Column(String(50))
    tokens_used = Column(Integer)
    generation_time_ms = Column(Integer)
    confidence_score = Column(Numeric(3, 2))
    prompt_tokens = Column(Integer)
    completion_tokens = Column(Integer)

    # Learning analytics
    contains_correction = Column(Boolean)
    grammar_points_mentioned = Column(ARRAY(Text))
    vocabulary_introduced = Column(ARRAY(Text))
    difficulty_level = Column(Integer)
    cultural_context_provided = Column(Boolean)

    # Language analysis
    detected_language = Column(String(10))
    language_confidence = Column(Numeric(3, 2))
    sentiment_score = Column(Numeric(3, 2))
    formality_level = Column(String(20))

    # Metadata
    created_at = Column(DateTime(timezone=True))
    message_order = Column(Integer, nullable=False)
    edited = Column(Boolean)
    edit_history = Column(JSON)

    # Privacy
    anonymized = Column(Boolean)
    anonymized_content = Column(Text)

    # Embedding
    # content_embedding is vector(1536) in DB; not modeled here

    def __repr__(self):
        return f"<ConversationMessage(id={self.id}, session_id={self.session_id}, role={self.role}, order={self.message_order})>"


class ConversationInteraction(Base):
    """User learning interactions within conversations - stores evidence of learning."""
    
    __tablename__ = "conversation_interactions"
    __table_args__ = {'extend_existing': True}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id = Column(UUID(as_uuid=True), ForeignKey("conversation_messages.id"), nullable=False)
    session_id = Column(UUID(as_uuid=True), ForeignKey("conversation_sessions.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Interaction type
    interaction_type = Column(String(30), nullable=False)  # question_asked, correction_received, grammar_practiced, etc.
    
    # Learning data
    concept_id = Column(String(100))  # Reference to Neo4j node ID (e.g., grammar pattern ID)
    concept_type = Column(String(20))  # grammar_point, vocabulary, cultural_note, pronunciation
    user_response = Column(Text)
    is_correct = Column(Boolean)
    attempts_count = Column(Integer, default=1)
    hint_used = Column(Boolean, default=False)
    
    # Spaced repetition integration
    ease_factor = Column(Numeric(3, 2), default=2.5)
    interval_days = Column(Integer, default=1)
    next_review_date = Column(Date)  # DATE in schema, not DateTime
    mastery_level = Column(Integer, default=1)
    
    # Performance tracking
    response_time_seconds = Column(Integer)
    confidence_self_reported = Column(Integer)  # 1-5 scale
    
    # Rich metadata for rubric breakdown, error tags, stage info
    # Note: Using 'evidence_metadata' as Python attribute name to avoid conflict with SQLAlchemy's reserved 'metadata'
    evidence_metadata = Column('metadata', JSONB)  # Maps to 'metadata' column in DB
    
    created_at = Column(DateTime(timezone=True), server_default='now()')
    
    # Relationships
    message = relationship("ConversationMessage")
    session = relationship("ConversationSession")
    user = relationship("User")
    
    def __repr__(self):
        return f"<ConversationInteraction(id={self.id}, type={self.interaction_type}, concept={self.concept_id})>"


class UserProfile(Base):
    """User profile model for detailed profile information."""
    
    __tablename__ = "user_profiles"
    __table_args__ = {'extend_existing': True}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    
    # Profile data (JSONB)
    previous_knowledge = Column(JSON, default=dict)
    learning_experiences = Column(JSON, default=dict)
    usage_context = Column(JSON, default=dict)
    learning_goals = Column(JSON, default=list)
    additional_notes = Column(Text)
    
    # AI extraction response and assessment
    extraction_response = Column(JSON, default=None)  # Stores raw AI response showing how data was extracted
    
    # Link to conversation where profile was built
    profile_building_conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversation_sessions.id", ondelete="SET NULL"))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True))
    
    # Relationships
    user = relationship("User", backref="profile")
    
    def __repr__(self):
        return f"<UserProfile(id={self.id}, user_id={self.user_id})>"


class LearningPath(Base):
    """Learning path model with versioning support."""
    
    __tablename__ = "learning_paths"
    __table_args__ = {'extend_existing': True}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Versioning
    version = Column(Integer, nullable=False, default=1)
    path_name = Column(String(255), nullable=False, default="Initial Path")
    
    # Path data (JSONB)
    path_data = Column(JSON, nullable=False, default=dict)
    progress_data = Column(JSON, default=dict)
    
    # Status
    is_active = Column(Boolean, default=True)
    superseded_by = Column(UUID(as_uuid=True), ForeignKey("learning_paths.id", ondelete="SET NULL"))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True))
    
    # Relationships
    user = relationship("User", backref="learning_paths")
    superseded_path = relationship("LearningPath", remote_side=[id], backref="superseding_paths")
    
    def __repr__(self):
        return f"<LearningPath(id={self.id}, user_id={self.user_id}, version={self.version}, is_active={self.is_active})>"