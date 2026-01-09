"""
User schemas for API request/response validation.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr, Field, validator
import uuid


# Base schemas
class UserBase(BaseModel):
    """Base user schema."""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    full_name: Optional[str] = Field(None, max_length=255)
    native_language: str = Field(default='en', max_length=10)
    target_languages: List[str] = Field(default=['ja'])
    current_level: str = Field(default='beginner')
    learning_goals: List[str] = Field(default=[])
    study_time_preference: int = Field(default=30, ge=5, le=180)
    difficulty_preference: str = Field(default='adaptive')
    preferred_ai_provider: str = Field(default='openai')
    conversation_style: str = Field(default='balanced')
    max_conversation_length: int = Field(default=50, ge=10, le=200)
    auto_save_conversations: bool = Field(default=True)


class UserCreate(UserBase):
    """Schema for user creation."""
    password: str = Field(..., min_length=8, max_length=100)
    
    @validator('password')
    def validate_password(cls, v):
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v
    
    @validator('learning_goals')
    def validate_learning_goals(cls, v):
        """Validate learning goals."""
        valid_goals = [
            'conversation', 'reading', 'writing', 'listening', 
            'business', 'travel', 'culture', 'anime', 'academic'
        ]
        for goal in v:
            if goal not in valid_goals:
                raise ValueError(f'Invalid learning goal: {goal}')
        return v


class UserUpdate(BaseModel):
    """Schema for user updates."""
    full_name: Optional[str] = Field(None, max_length=255)
    native_language: Optional[str] = Field(None, max_length=10)
    target_languages: Optional[List[str]] = None
    current_level: Optional[str] = None
    learning_goals: Optional[List[str]] = None
    study_time_preference: Optional[int] = Field(None, ge=5, le=180)
    difficulty_preference: Optional[str] = None
    preferred_ai_provider: Optional[str] = None
    conversation_style: Optional[str] = None
    max_conversation_length: Optional[int] = Field(None, ge=10, le=200)
    auto_save_conversations: Optional[bool] = None


class UserResponse(UserBase):
    """Schema for user responses."""
    id: uuid.UUID
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class UserProfile(BaseModel):
    """Extended user profile with learning statistics."""
    id: uuid.UUID
    email: str
    username: str
    full_name: Optional[str]
    native_language: str
    target_languages: List[str]
    current_level: str
    learning_goals: List[str]
    study_time_preference: int
    difficulty_preference: str
    preferred_ai_provider: str
    conversation_style: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime
    
    # Learning statistics (populated separately)
    total_study_time_minutes: Optional[int] = 0
    total_conversations: Optional[int] = 0
    total_words_learned: Optional[int] = 0
    current_streak_days: Optional[int] = 0
    assessed_level: Optional[str] = None
    
    class Config:
        from_attributes = True


# Authentication schemas
class Token(BaseModel):
    """JWT token response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    user_id: uuid.UUID


class TokenData(BaseModel):
    """Token payload data."""
    user_id: Optional[uuid.UUID] = None
    username: Optional[str] = None


class UserLogin(BaseModel):
    """User login credentials."""
    username: str
    password: str


# Conversation schemas
class ConversationSessionBase(BaseModel):
    """Base conversation session schema."""
    title: Optional[str] = Field(None, max_length=255)
    language_code: str = Field(default='ja', max_length=10)
    session_type: str = Field(default='chat')
    ai_provider: str
    ai_model: str
    system_prompt: Optional[str] = None
    conversation_context: Optional[Dict[str, Any]] = Field(default_factory=dict)


class ConversationSessionCreate(ConversationSessionBase):
    """Schema for creating conversation sessions."""
    pass


class ConversationSessionResponse(ConversationSessionBase):
    """Schema for conversation session responses."""
    id: uuid.UUID
    user_id: uuid.UUID
    status: str
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]
    total_messages: int
    user_messages: int
    ai_messages: int
    session_duration_seconds: int
    
    class Config:
        from_attributes = True


class ConversationMessageBase(BaseModel):
    """Base conversation message schema."""
    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str
    content_type: str = Field(default='text')


class ConversationMessageCreate(ConversationMessageBase):
    """Schema for creating conversation messages."""
    pass


class ConversationMessageResponse(ConversationMessageBase):
    """Schema for conversation message responses."""
    id: uuid.UUID
    session_id: uuid.UUID
    message_order: int
    created_at: datetime
    
    # AI metadata (for assistant messages)
    ai_provider: Optional[str] = None
    ai_model: Optional[str] = None
    tokens_used: Optional[int] = None
    generation_time_ms: Optional[int] = None
    confidence_score: Optional[float] = None
    
    # Learning analytics
    contains_correction: bool = False
    grammar_points_mentioned: Optional[List[str]] = Field(default_factory=list)
    vocabulary_introduced: Optional[List[str]] = Field(default_factory=list)
    difficulty_level: Optional[int] = None
    
    class Config:
        from_attributes = True


# Learning progress schemas
class LearningProgressResponse(BaseModel):
    """User learning progress response."""
    id: uuid.UUID
    user_id: uuid.UUID
    total_study_time_minutes: int
    total_conversations: int
    total_words_learned: int
    total_grammar_points_learned: int
    assessed_level: Optional[str]
    confidence_score: Optional[float]
    current_streak_days: int
    longest_streak_days: int
    last_study_date: Optional[datetime]
    words_per_week: Optional[float]
    improvement_rate: Optional[float]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Analytics schemas
class ConversationAnalyticsResponse(BaseModel):
    """Conversation analytics response."""
    id: uuid.UUID
    session_id: uuid.UUID
    user_id: uuid.UUID
    words_per_minute: Optional[float]
    grammar_accuracy_percentage: Optional[float]
    vocabulary_usage_diversity: Optional[int]
    conversation_flow_score: Optional[float]
    new_concepts_learned: int
    concepts_reviewed: int
    mistakes_corrected: int
    cultural_insights_gained: int
    session_engagement_score: Optional[float]
    user_initiative_count: Optional[int]
    question_asking_frequency: Optional[float]
    analyzed_at: datetime
    
    class Config:
        from_attributes = True


# Diagnostic quiz schemas
class DiagnosticQuizQuestion(BaseModel):
    """Diagnostic quiz question."""
    id: str
    type: str  # multiple_choice, translation, listening
    question: str
    options: Optional[List[str]] = None
    correct_answer: str
    difficulty_level: str
    skill_area: str  # vocabulary, grammar, listening, reading


class DiagnosticQuizResponse(BaseModel):
    """User's response to diagnostic quiz."""
    question_id: str
    user_answer: str
    is_correct: bool
    time_taken_seconds: int


class DiagnosticQuizResult(BaseModel):
    """Diagnostic quiz results."""
    user_id: uuid.UUID
    assessed_level: str
    confidence_score: float
    skill_breakdown: Dict[str, float]  # skill_area -> proficiency_score
    recommendations: List[str]
    suggested_learning_path: List[str]
    completed_at: datetime


# Learning recommendations
class LearningRecommendation(BaseModel):
    """Personalized learning recommendation."""
    type: str  # vocabulary, grammar, conversation_topic
    title: str
    description: str
    difficulty_level: str
    estimated_time_minutes: int
    priority_score: float
    reason: str  # Why this is recommended
    content: Dict[str, Any]  # Specific content based on type


class PersonalizedDashboard(BaseModel):
    """User's personalized learning dashboard."""
    user_profile: UserProfile
    learning_progress: LearningProgressResponse
    daily_recommendations: List[LearningRecommendation]
    recent_conversations: List[ConversationSessionResponse]
    upcoming_reviews: List[Dict[str, Any]]  # SRS items due for review
    achievements: List[Dict[str, Any]]  # Recent achievements/milestones
    learning_streaks: Dict[str, int]  # Various streak counters
