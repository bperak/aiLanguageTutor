"""
Pydantic Schemas for Lexical Network

Strongly-typed schemas for lexical relations, job configurations, and API responses.
"""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, validator


class RelationCandidate(BaseModel):
    """AI-generated relation candidate with full metadata."""
    
    source_word: str
    target_word: str  # Resolved canonical word key (set after resolution)
    target_orthography: Optional[str] = None  # Raw orthography from AI
    target_reading: Optional[str] = None  # Raw reading from AI
    relation_type: str
    relation_category: str
    weight: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    is_symmetric: bool
    
    # Explanatory fields
    shared_meaning_en: str
    distinction_en: str
    usage_context_en: str
    when_prefer_source_en: Optional[str] = None
    when_prefer_target_en: Optional[str] = None
    
    # Register
    register_source: Literal["neutral", "colloquial", "formal", "literary", "slang"]
    register_target: Literal["neutral", "colloquial", "formal", "literary", "slang"]
    formality_difference: Literal["same", "source_higher", "target_higher"]
    
    # Scalar (optional, for adjectives/adverbs)
    scale_dimension: Optional[str] = None
    scale_position_source: Optional[float] = Field(None, ge=0.0, le=1.0)
    scale_position_target: Optional[float] = Field(None, ge=0.0, le=1.0)
    
    # Verb-specific (optional)
    aspect_source: Optional[Literal["punctual", "durative", "stative"]] = None
    aspect_target: Optional[Literal["punctual", "durative", "stative"]] = None
    transitivity_source: Optional[Literal["transitive", "intransitive", "both"]] = None
    transitivity_target: Optional[Literal["transitive", "intransitive", "both"]] = None
    
    # Features
    domain_tags: List[str] = []
    domain_weights: List[float] = []
    context_tags: List[str] = []
    context_weights: List[float] = []
    
    # AI metadata (populated after generation)
    ai_provider: Optional[str] = None
    ai_model: Optional[str] = None
    ai_temperature: float = 0.0
    ai_request_id: Optional[str] = None
    
    # Resolution metadata (populated after target resolution)
    target_resolution_method: Optional[str] = None  # e.g., "ranked_match"
    target_resolution_confidence: Optional[float] = None  # 0.0-1.0
    
    @validator("domain_weights")
    def validate_domain_alignment(cls, v, values):
        """Ensure domain_weights aligns with domain_tags."""
        if "domain_tags" in values and len(v) != len(values["domain_tags"]):
            raise ValueError("domain_weights must align with domain_tags")
        return v
    
    @validator("context_weights")
    def validate_context_alignment(cls, v, values):
        """Ensure context_weights aligns with context_tags."""
        if "context_tags" in values and len(v) != len(values["context_tags"]):
            raise ValueError("context_weights must align with context_tags")
        return v
    
    @validator("domain_weights", "context_weights")
    def validate_weights_range(cls, v):
        """Ensure all weights are in [0.0, 1.0]."""
        for weight in v:
            if not (0.0 <= weight <= 1.0):
                raise ValueError("Weights must be in [0.0, 1.0]")
        return v


class JobConfig(BaseModel):
    """Configuration for a lexical network job."""
    
    job_type: Literal["relation_building", "dictionary_import", "cluster_analysis"]
    
    # Source mode: "database" for filtered DB query, "word_list" for manual list
    source: Literal["database", "word_list"] = "database"
    
    # For "database" source - combined filters (inclusive)
    pos_filter: Optional[str] = Field(None, description="POS filter (None = all POS)")
    filter_no_relations: bool = Field(False, description="Only words with zero relations")
    filter_few_relations: bool = Field(False, description="Only words with < max_relations")
    max_relations: Optional[int] = Field(None, ge=0, le=1000, description="Threshold for few_relations filter")
    
    # For "word_list" source
    word_list: Optional[List[str]] = None
    
    # Relation types to generate
    relation_types: List[str] = ["SYNONYM"]
    
    # AI Model Selection
    model: str = Field(
        default="gpt-4o-mini",
        description="AI model to use (gpt-4o-mini, gemini-2.5-flash, deepseek-chat, etc.)"
    )
    # Temperature is NOT configurable - always 0.0
    
    max_words: int = Field(100, ge=1, le=10000)
    batch_size: int = Field(10, ge=1, le=100)
    min_confidence: float = Field(0.7, ge=0.0, le=1.0)
    
    @validator("word_list")
    def validate_word_list(cls, v, values):
        """Ensure word_list is provided when source is word_list."""
        if values.get("source") == "word_list" and not v:
            raise ValueError("word_list required when source is 'word_list'")
        return v
    
    @validator("max_relations")
    def validate_max_relations(cls, v, values):
        """Ensure max_relations is provided when filter_few_relations is True."""
        if values.get("filter_few_relations") and v is None:
            raise ValueError("max_relations required when filter_few_relations is True")
        return v


class JobResult(BaseModel):
    """Job result with AI usage statistics."""
    
    processed: int
    relations_created: int
    relations_updated: int
    errors: int
    
    # AI usage stats
    total_tokens_input: int
    total_tokens_output: int
    total_cost_usd: float
    avg_latency_ms: float
    models_used: Dict[str, int]  # model -> count
    
    # Resolution statistics (aggregated from BuildResult)
    total_targets_attempted: int = 0
    total_targets_resolved: int = 0
    total_targets_dropped_not_found: int = 0
    total_targets_dropped_ambiguous: int = 0
    resolution_rate: float = 0.0  # resolved / attempted


class WordProcessingResult(BaseModel):
    """Result of processing a single word."""
    word: str
    relations_created: int = 0
    relations_updated: int = 0
    targets_found: int = 0
    targets_resolved: int = 0
    error: Optional[str] = None
    timestamp: datetime


class JobStatus(BaseModel):
    """Job status response."""
    
    id: str
    job_type: str
    status: Literal["pending", "running", "completed", "failed", "cancelled"]
    progress: float = Field(ge=0.0, le=1.0)
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    result: Optional[JobResult] = None
    source_words: Optional[List[str]] = None
    config: Optional[Dict] = None
    
    # Real-time progress tracking
    current_word: Optional[str] = None
    current_word_index: int = 0
    total_words: int = 0
    recent_results: List[WordProcessingResult] = []  # Last N processed words


class ModelInfo(BaseModel):
    """Available model information for UI."""
    
    model_key: str
    provider: str
    display_name: str
    input_cost_per_1k: float
    output_cost_per_1k: float
    max_tokens: int
    supports_json_mode: bool
    recommended_for: List[str]


class NetworkStats(BaseModel):
    """Network statistics response."""
    
    total_words: int
    total_relations: int
    
    # Lexical relations (what we're building)
    lexical_relations: Dict[str, int]  # SYNONYM_OF, SIMILAR_TO, LEXICAL_RELATION
    relations_by_pos: Dict[str, Dict[str, int]]  # pos -> {rel_type: count}
    
    # ALL relationship types in Neo4j (for context)
    all_relations_by_type: Dict[str, int]  # Every relationship type
    relations_by_category: Dict[str, int]  # Grouped: lexical, learning, semantic, other
    
    # Word distributions
    pos_distribution: Dict[str, int]
    difficulty_distribution: Dict[str, int]  # N5, N4, N3, N2, N1, etc.
    
    # Connectivity stats
    avg_relations_per_word: float
    words_without_relations: int  # Without any lexical relations
    most_connected_words: List[Dict[str, Any]]
    
    # Legacy (keep for compatibility)
    relations_by_type: Dict[str, int]


class BuildResult(BaseModel):
    """Result from building relations for a word."""
    
    word: str
    candidates_found: int
    relations_created: int
    relations_updated: int
    errors: int
    tokens_input: int
    tokens_output: int
    cost_usd: float
    latency_ms: int
    model_used: str
    
    # Resolution statistics
    targets_attempted: int = 0
    targets_resolved: int = 0
    targets_dropped_not_found: int = 0
    targets_dropped_ambiguous: int = 0
    dropped_not_found_samples: List[str] = []  # Bounded list, e.g. ["綺麗|きれい", ...]
    dropped_ambiguous_samples: List[str] = []  # Bounded list


class RelationStats(BaseModel):
    """Statistics for a specific relation type."""
    
    relation_type: str
    count: int
    avg_weight: float
    avg_confidence: float
    providers: Dict[str, int]  # provider -> count
    models: Dict[str, int]  # model -> count
