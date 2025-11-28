"""
Profile schemas for API request/response validation and data extraction.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
import uuid


# Profile Data Extraction Schemas
class PreviousKnowledge(BaseModel):
    """Previous knowledge and experience with target language."""
    has_experience: bool = False
    experience_level: Optional[str] = None  # beginner, intermediate, advanced
    years_studying: Optional[float] = None
    formal_classes: bool = False
    self_study: bool = False
    specific_areas_known: List[str] = Field(default_factory=list)  # e.g., ["hiragana", "basic greetings"]
    specific_areas_unknown: List[str] = Field(default_factory=list)


class LearningExperience(BaseModel):
    """Past learning methods and preferences."""
    preferred_methods: List[str] = Field(default_factory=list)  # e.g., ["conversation", "flashcards", "reading"]
    methods_that_worked: List[str] = Field(default_factory=list)
    methods_that_didnt_work: List[str] = Field(default_factory=list)
    learning_style: Optional[str] = None  # visual, auditory, kinesthetic, reading/writing
    study_schedule: Optional[str] = None  # daily, weekly, irregular
    motivation_level: Optional[str] = None  # high, medium, low
    challenges_faced: List[str] = Field(default_factory=list)


class UsageContext(BaseModel):
    """Where and when user wants to use target language."""
    contexts: List[str] = Field(default_factory=list)  # e.g., ["travel", "work", "academic"]
    urgency: Optional[str] = None  # immediate, short-term, long-term
    specific_situations: List[str] = Field(default_factory=list)  # e.g., ["ordering food", "business meetings"]
    target_date: Optional[str] = None  # e.g., "in 3 months for trip"


class ProfileData(BaseModel):
    """Complete profile data extracted from conversation."""
    learning_goals: List[str] = Field(default_factory=list)
    previous_knowledge: PreviousKnowledge = Field(default_factory=PreviousKnowledge)
    learning_experiences: LearningExperience = Field(default_factory=LearningExperience)
    usage_context: UsageContext = Field(default_factory=UsageContext)
    current_level: Optional[str] = Field(
        None,
        description="Assessed learning stage: beginner_1, beginner_2, intermediate_1, intermediate_2, advanced_1, advanced_2"
    )
    additional_notes: Optional[str] = None
    
    class Config:
        from_attributes = True


# API Request/Response Schemas
class ProfileStatusResponse(BaseModel):
    """Profile completion status."""
    profile_completed: bool
    profile_skipped: bool
    profile_completed_at: Optional[datetime] = None
    has_profile_data: bool = False
    
    class Config:
        from_attributes = True


class ProfileDataResponse(BaseModel):
    """User profile data response."""
    user_id: uuid.UUID
    learning_goals: List[str]
    previous_knowledge: Dict[str, Any]
    learning_experiences: Dict[str, Any]
    usage_context: Dict[str, Any]
    additional_notes: Optional[str]
    profile_building_conversation_id: Optional[uuid.UUID]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ProfileCompleteRequest(BaseModel):
    """Request to mark profile as complete."""
    conversation_id: uuid.UUID
    profile_data: Optional[ProfileData] = None  # Optional - will be extracted from conversation if not provided


class ProfileSkipRequest(BaseModel):
    """Request to skip profile building."""
    pass  # No additional data needed


# Learning Path Schemas
class LearningPathStep(BaseModel):
    """A single step in a learning path."""
    step_id: str
    title: str
    description: str
    estimated_duration_days: int
    prerequisites: List[str] = Field(default_factory=list)  # step_ids
    learning_objectives: List[str] = Field(default_factory=list)
    can_do_descriptors: List[str] = Field(default_factory=list)  # CanDo descriptor IDs
    resources: List[str] = Field(default_factory=list)  # Resource IDs or URLs
    difficulty_level: Optional[str] = None  # beginner, intermediate, advanced


class LearningPathMilestone(BaseModel):
    """A milestone in a learning path."""
    milestone_id: str
    title: str
    description: str
    target_date: Optional[str] = None
    steps_required: List[str] = Field(default_factory=list)  # step_ids
    celebration_message: Optional[str] = None


class LearningPathData(BaseModel):
    """Complete learning path structure."""
    path_name: str
    description: str
    total_estimated_days: int
    steps: List[LearningPathStep]
    milestones: List[LearningPathMilestone] = Field(default_factory=list)
    starting_level: str
    target_level: str
    learning_goals: List[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class LearningPathProgress(BaseModel):
    """Progress tracking for learning path."""
    current_step_id: Optional[str] = None
    completed_step_ids: List[str] = Field(default_factory=list)
    current_milestone_id: Optional[str] = None
    completed_milestone_ids: List[str] = Field(default_factory=list)
    started_at: Optional[datetime] = None
    last_updated: Optional[datetime] = None
    progress_percentage: float = 0.0


class LearningPathResponse(BaseModel):
    """Learning path response with progress."""
    id: uuid.UUID
    user_id: uuid.UUID
    version: int
    path_name: str
    path_data: Dict[str, Any]
    progress_data: Dict[str, Any]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class LearningPathGenerateRequest(BaseModel):
    """Request to generate a new learning path."""
    force_regenerate: bool = False  # If true, create new version even if one exists

