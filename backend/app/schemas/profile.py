"""
Profile schemas for API request/response validation and data extraction.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator
import uuid


# Profile Data Extraction Schemas
class PreviousKnowledge(BaseModel):
    """Previous knowledge and experience with target language."""
    has_experience: bool = False
    experience_level: Optional[str] = None  # beginner, intermediate, advanced
    years_studying: Optional[float] = None
    formal_classes: bool = Field(default=False)
    self_study: bool = Field(default=False)
    specific_areas_known: List[str] = Field(default_factory=list)  # e.g., ["hiragana", "basic greetings"]
    specific_areas_unknown: List[str] = Field(default_factory=list)
    
    @field_validator('formal_classes', 'self_study', mode='before')
    @classmethod
    def convert_none_to_false(cls, v):
        """Convert None to False for boolean fields."""
        if v is None:
            return False
        return bool(v)


class LearningExperience(BaseModel):
    """Past learning methods and preferences."""
    preferred_methods: List[str] = Field(default_factory=list)  # e.g., ["conversation", "flashcards", "reading"]
    methods_that_worked: List[str] = Field(default_factory=list)
    methods_that_didnt_work: List[str] = Field(default_factory=list)
    learning_style: Optional[str] = None  # visual, auditory, kinesthetic, reading/writing
    study_schedule: Optional[str] = None  # daily, weekly, irregular
    motivation_level: Optional[str] = None  # high, medium, low
    challenges_faced: List[str] = Field(default_factory=list)
    
    @field_validator('learning_style', 'study_schedule', 'motivation_level', mode='before')
    @classmethod
    def convert_list_to_string(cls, v):
        """Convert lists to comma-separated strings for string fields."""
        if isinstance(v, list):
            # Join list items with comma and space
            return ', '.join(str(item) for item in v if item)
        if v is None or v == '':
            return None
        return v
    # Priority 2: 4-Stage Personalization
    grammar_focus_areas: List[str] = Field(default_factory=list)  # ["particles", "verb forms", "keigo"]
    grammar_challenges: List[str] = Field(default_factory=list)
    preferred_exercise_types: Dict[str, List[str]] = Field(default_factory=dict)  # {"comprehension": ["matching", "q&a"], "production": ["translation", "writing"]}
    interaction_preferences: Dict[str, Any] = Field(default_factory=dict)  # {"style": "structured", "role_play": True, "ai_partner": True}
    # Priority 3: Nice to Have
    feedback_preferences: Dict[str, Any] = Field(default_factory=dict)  # {"style": "encouraging", "detail_level": "moderate"}
    error_tolerance: Optional[str] = None  # "high", "medium", "low"
    
    @field_validator('preferred_exercise_types', 'interaction_preferences', 'feedback_preferences', mode='before')
    @classmethod
    def convert_list_to_dict(cls, v):
        """Convert empty lists, empty strings, or None to empty dicts for dictionary fields."""
        if isinstance(v, list):
            return {}
        if v is None or v == '':
            return {}
        if isinstance(v, str) and v.strip() == '':
            return {}
        return v


class UsageContext(BaseModel):
    """Where and when user wants to use target language."""
    contexts: List[str] = Field(default_factory=list)  # e.g., ["travel", "work", "academic"]
    urgency: Optional[str] = None  # immediate, short-term, long-term
    specific_situations: List[str] = Field(default_factory=list)  # e.g., ["ordering food", "business meetings"]
    target_date: Optional[str] = None  # e.g., "in 3 months for trip"
    # Priority 1: DomainPlan Quality
    register_preferences: List[str] = Field(default_factory=list)  # ["formal", "casual", "neutral"]
    formality_contexts: Dict[str, str] = Field(default_factory=dict)  # {"work": "formal", "social": "casual"}
    scenario_details: Dict[str, List[str]] = Field(default_factory=dict)  # {"travel": ["airport", "hotel"], "work": ["meetings"]}
    
    @field_validator('register_preferences', 'contexts', 'specific_situations', mode='before')
    @classmethod
    def convert_string_to_list(cls, v):
        """Convert empty strings to empty lists for list fields."""
        if v is None or v == '':
            return []
        if isinstance(v, str) and v.strip() == '':
            return []
        return v
    
    @field_validator('formality_contexts', 'scenario_details', mode='before')
    @classmethod
    def convert_to_dict(cls, v):
        """Convert empty lists, empty strings, or None to empty dicts for dictionary fields."""
        if isinstance(v, list):
            return {}
        if v is None or v == '':
            return {}
        if isinstance(v, str) and v.strip() == '':
            return {}
        return v


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
    # Priority 0: Learning Loop (Path-Level Structures)
    vocabulary_domain_goals: List[str] = Field(default_factory=list)  # ["travel", "business", "daily_life"]
    vocabulary_known: List[Dict[str, Any]] = Field(default_factory=list)  # [{"word": "こんにちは", "domain": "greetings", "level": "beginner_1", "mastery": 4}, ...]
    vocabulary_learning_target: Optional[int] = None  # Target words per milestone
    vocabulary_level_preference: Optional[str] = None  # "current", "slightly_above", "challenging"
    grammar_progression_goals: List[str] = Field(default_factory=list)  # ["particles", "verb_forms", "keigo"]
    grammar_known: List[Dict[str, Any]] = Field(default_factory=list)  # [{"pattern": "〜です", "level": "beginner_1", "mastery": 5, "area": "copula"}, ...]
    grammar_learning_target: Optional[int] = None  # Target patterns per milestone
    grammar_level_preference: Optional[str] = None  # "current", "slightly_above", "challenging"
    formulaic_expression_goals: List[str] = Field(default_factory=list)  # ["greetings", "requests", "apologies"]
    expressions_known: List[Dict[str, Any]] = Field(default_factory=list)  # [{"expression": "よろしく", "context": "greetings", "level": "beginner_1", "register": "casual", "mastery": 4}, ...]
    expression_learning_target: Optional[int] = None  # Target expressions per milestone
    expression_level_preference: Optional[str] = None  # "current", "slightly_above", "challenging"
    # Priority 1: DomainPlan Quality
    cultural_interests: List[str] = Field(default_factory=list)  # ["etiquette", "history", "pop culture"]
    cultural_background: Optional[str] = None  # User's cultural background
    
    class Config:
        from_attributes = True


# API Request/Response Schemas
class ProfileStatusResponse(BaseModel):
    """Profile completion status."""
    profile_completed: bool
    profile_skipped: bool
    profile_completed_at: Optional[datetime] = None
    has_profile_data: bool = False
    completion_percentage: Optional[float] = None  # 0.0 to 1.0
    missing_fields: List[str] = Field(default_factory=list)  # Fields that are missing or incomplete
    suggestions: List[str] = Field(default_factory=list)  # Suggestions for completing profile
    
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
    extraction_response: Optional[Dict[str, Any]] = Field(
        default=None,
        description="AI extraction response and assessment showing how profile data was extracted"
    )
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
class CanDoContext(BaseModel):
    """Situational context and pragmatic communication act for a CanDo descriptor.
    
    This represents component (0) of the lesson: the CanDo itself with its
    situational context and pragmatic communication act.
    """
    situation: str = Field(
        description="Short scenario description of the conversational situation"
    )
    pragmatic_act: str = Field(
        description="Pragmatic communication act (e.g., request/offer/apology/decline/ask-info) with politeness/register"
    )
    notes: Optional[str] = Field(
        default=None,
        description="Optional additional context or cultural notes"
    )
    
    class Config:
        from_attributes = True


class PreLessonKit(BaseModel):
    """Pre-lesson preparation kit with necessary words, grammar, and fixed phrases.
    
    Generated before lesson creation to help learners prepare for the conversational
    situation. All content is level-appropriate and situation-specific.
    
    Contains 4 components:
    - (0) CanDo: situational context + pragmatic communication act
    - (1) Words: appropriate for this level
    - (2) Grammar patterns: appropriate for this level
    - (3) Common phrases/formulaic expressions: appropriate for this level
    """
    can_do_context: Optional[CanDoContext] = Field(
        default=None,
        description="Component (0): CanDo situational context and pragmatic communication act"
    )
    necessary_words: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Component (1): List of vocabulary entries (VocabularyEntry format: surface, reading, pos, translation)"
    )
    necessary_grammar_patterns: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Component (2): List of grammar patterns (GrammarPoint format: pattern, explanation, examples)"
    )
    necessary_fixed_phrases: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Component (3): List of fixed phrases/motifs (FixedPhrase format: phrase, usage_note, register)"
    )
    
    class Config:
        from_attributes = True


class LearningPathStep(BaseModel):
    """A single step in a learning path."""
    step_id: str
    title: str
    description: str
    estimated_duration_days: int
    prerequisites: List[str] = Field(default_factory=list)  # step_ids
    learning_objectives: List[str] = Field(default_factory=list)
    vocabulary: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Vocabulary items for this step (word, reading, pos, translation)"
    )
    grammar: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Grammar patterns for this step (pattern, explanation, examples)"
    )
    formulaic_expressions: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Formulaic expressions for this step (phrase, usage_note, register)"
    )
    can_do_descriptors: List[str] = Field(default_factory=list)  # CanDo descriptor IDs (validated)
    resources: List[str] = Field(default_factory=list)  # Resource IDs or URLs
    difficulty_level: Optional[str] = None  # beginner, intermediate, advanced
    prelesson_kit: Optional[PreLessonKit] = Field(
        default=None,
        description="Optional pre-lesson preparation kit (generated on-demand or during path creation)"
    )


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
    # Path-level structures for evaluation tracking
    path_structures: Dict[str, Any] = Field(default_factory=dict)  # {
    #   "vocabulary": [
    #     {"word": "...", "domain": "...", "milestone": "...", "level": "beginner_1", "cefr_level": "A1", "validated": True},
    #     ...
    #   ],
    #   "grammar": [
    #     {"pattern": "...", "level": "beginner_1", "cefr_level": "A1", "milestone": "...", "validated": True, "prerequisites": [...]},
    #     ...
    #   ],
    #   "expressions": [
    #     {"expression": "...", "context": "...", "level": "beginner_1", "cefr_level": "A1", "register": "polite", "milestone": "...", "validated": True},
    #     ...
    #   ]
    # }
    
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

