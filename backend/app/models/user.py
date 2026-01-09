"""
User models for the AI Language Tutor.
Integrates with the existing PostgreSQL schema.
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

# Import the shared Base from __init__.py to avoid circular imports
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()


class User(Base):
    """User model matching the PostgreSQL schema."""
    
    __tablename__ = "users"
    
    # Primary fields
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    
    # Profile information
    full_name = Column(String(255))
    native_language = Column(String(10), default='en')  # ISO language code
    target_languages = Column(ARRAY(String(10)), default=['ja'])  # Learning Japanese
    
    # Learning preferences
    current_level = Column(String(20), default='beginner')  # beginner, intermediate, advanced
    learning_goals = Column(ARRAY(String(100)), default=[])  # conversation, reading, business, etc.
    study_time_preference = Column(Integer, default=30)  # minutes per day
    difficulty_preference = Column(String(20), default='adaptive')  # easy, adaptive, challenging
    
    # Account status
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Conversation preferences
    preferred_ai_provider = Column(String(20), default='openai')
    conversation_style = Column(String(20), default='balanced')  # casual, formal, balanced
    max_conversation_length = Column(Integer, default=50)
    auto_save_conversations = Column(Boolean, default=True)
    
    # Relationships
    conversation_sessions = relationship("ConversationSession", back_populates="user", cascade="all, delete-orphan")
    learning_progress = relationship("UserLearningProgress", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, email={self.email})>"


class ConversationSession(Base):
    """Conversation session model."""
    
    __tablename__ = "conversation_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Session metadata
    title = Column(String(255))
    language_code = Column(String(10), nullable=False, default='ja')
    session_type = Column(String(20), nullable=False, default='chat')  # chat, lesson, practice, quiz
    status = Column(String(20), default='active')  # active, completed, archived
    
    # AI Configuration
    ai_provider = Column(String(20), nullable=False)
    ai_model = Column(String(50), nullable=False)
    system_prompt = Column(Text)
    conversation_context = Column(JSON)  # Current lesson, difficulty level, etc.
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True))
    
    # Statistics
    total_messages = Column(Integer, default=0)
    user_messages = Column(Integer, default=0)
    ai_messages = Column(Integer, default=0)
    session_duration_seconds = Column(Integer, default=0)
    
    # Relationships
    user = relationship("User", back_populates="conversation_sessions")
    messages = relationship("ConversationMessage", back_populates="session", cascade="all, delete-orphan")
    interactions = relationship("ConversationInteraction", back_populates="session", cascade="all, delete-orphan")
    analytics = relationship("ConversationAnalytics", back_populates="session", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<ConversationSession(id={self.id}, user_id={self.user_id}, type={self.session_type})>"


class ConversationMessage(Base):
    """Individual conversation message model."""
    
    __tablename__ = "conversation_messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("conversation_sessions.id"), nullable=False)
    
    # Message content
    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    content_type = Column(String(20), default='text')  # text, audio, image
    
    # AI Generation metadata (for assistant messages)
    ai_provider = Column(String(20))
    ai_model = Column(String(50))
    tokens_used = Column(Integer)
    generation_time_ms = Column(Integer)
    confidence_score = Column(String)  # Using String to handle DECIMAL
    
    # Learning analytics
    contains_correction = Column(Boolean, default=False)
    grammar_points_mentioned = Column(ARRAY(String))  # Grammar point IDs
    vocabulary_introduced = Column(ARRAY(String))  # New vocabulary
    difficulty_level = Column(Integer)  # 1-5 scale
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    message_order = Column(Integer, nullable=False)  # Order within session
    
    # Relationships
    session = relationship("ConversationSession", back_populates="messages")
    interactions = relationship("ConversationInteraction", back_populates="message", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<ConversationMessage(id={self.id}, role={self.role}, order={self.message_order})>"


class ConversationInteraction(Base):
    """User learning interactions within conversations."""
    
    __tablename__ = "conversation_interactions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id = Column(UUID(as_uuid=True), ForeignKey("conversation_messages.id"), nullable=False)
    session_id = Column(UUID(as_uuid=True), ForeignKey("conversation_sessions.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Interaction type
    interaction_type = Column(String(30), nullable=False)  # question_asked, correction_received, etc.
    
    # Learning data
    concept_id = Column(String(100))  # Reference to Neo4j node ID
    concept_type = Column(String(20))  # grammar_point, vocabulary, cultural_note
    user_response = Column(Text)
    is_correct = Column(Boolean)
    attempts_count = Column(Integer, default=1)
    
    # Spaced repetition integration
    ease_factor = Column(String, default='2.5')  # Using String to handle DECIMAL
    interval_days = Column(Integer, default=1)
    next_review_date = Column(DateTime(timezone=True))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    message = relationship("ConversationMessage", back_populates="interactions")
    session = relationship("ConversationSession", back_populates="interactions")
    
    def __repr__(self):
        return f"<ConversationInteraction(id={self.id}, type={self.interaction_type})>"


class ConversationAnalytics(Base):
    """Conversation analytics and insights."""
    
    __tablename__ = "conversation_analytics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("conversation_sessions.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Performance metrics
    words_per_minute = Column(String)  # Using String to handle DECIMAL
    grammar_accuracy_percentage = Column(String)  # Using String to handle DECIMAL
    vocabulary_usage_diversity = Column(Integer)
    conversation_flow_score = Column(String)  # Using String to handle DECIMAL
    
    # Learning progress
    new_concepts_learned = Column(Integer, default=0)
    concepts_reviewed = Column(Integer, default=0)
    mistakes_corrected = Column(Integer, default=0)
    cultural_insights_gained = Column(Integer, default=0)
    
    # Engagement metrics
    session_engagement_score = Column(String)  # Using String to handle DECIMAL
    user_initiative_count = Column(Integer)  # How often user started topics
    question_asking_frequency = Column(String)  # Using String to handle DECIMAL
    
    analyzed_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    session = relationship("ConversationSession", back_populates="analytics")
    
    def __repr__(self):
        return f"<ConversationAnalytics(id={self.id}, session_id={self.session_id})>"


class UserLearningProgress(Base):
    """User learning progress tracking."""
    
    __tablename__ = "user_learning_progress"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Progress metrics
    total_study_time_minutes = Column(Integer, default=0)
    total_conversations = Column(Integer, default=0)
    total_words_learned = Column(Integer, default=0)
    total_grammar_points_learned = Column(Integer, default=0)
    
    # Current level assessment
    assessed_level = Column(String(20))  # Based on performance
    confidence_score = Column(String)  # Using String to handle DECIMAL
    
    # Streak and engagement
    current_streak_days = Column(Integer, default=0)
    longest_streak_days = Column(Integer, default=0)
    last_study_date = Column(DateTime(timezone=True))
    
    # Learning velocity
    words_per_week = Column(String)  # Using String to handle DECIMAL
    improvement_rate = Column(String)  # Using String to handle DECIMAL
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="learning_progress")
    
    def __repr__(self):
        return f"<UserLearningProgress(id={self.id}, user_id={self.user_id})>"
