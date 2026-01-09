"""
Configuration settings for the AI Language Tutor Backend API.

This module uses Pydantic Settings to load and validate configuration
from environment variables with sensible defaults.
"""

from pathlib import Path
from typing import Any

from pydantic import Field, validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _find_env_file() -> str | None:
    """
    Find the nearest `.env` file by walking up parent directories.

    Reason: the backend runs in two common layouts:
    - repo checkout: `<repo>/backend/app/core/config.py`  -> `.env` is at `<repo>/.env`
    - Docker image: `/app/app/core/config.py`             -> `.env` may be at `/app/.env`
    """
    for parent in Path(__file__).resolve().parents:
        candidate = parent / ".env"
        if candidate.exists():
            return str(candidate)
    return None


_ENV_FILE = _find_env_file()


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    All settings are loaded from environment variables with the specified
    prefixes and defaults. Sensitive values like API keys should be
    provided via environment variables.
    """
    
    # Application Settings
    DEBUG: bool = Field(default=False, description="Enable debug mode")
    ENVIRONMENT: str = Field(default="development", description="Environment name")
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    
    # Neo4j Graph Database
    NEO4J_URI: str = Field(..., description="Neo4j database URI")
    NEO4J_USERNAME: str = Field(default="neo4j", description="Neo4j username")
    NEO4J_PASSWORD: str = Field(..., description="Neo4j password")
    NEO4J_MAX_CONNECTION_POOL_SIZE: int = Field(
        default=50, description="Maximum Neo4j connection pool size"
    )
    
    # PostgreSQL Database
    DATABASE_URL: str = Field(..., description="PostgreSQL database URL")
    PGVECTOR_ENABLED: bool = Field(default=True, description="Enable pgvector extension")
    EMBEDDING_DIMENSIONS: int = Field(default=1536, description="Vector embedding dimensions")
    NEO4J_VECTOR_ENABLED: bool = Field(default=True, description="Enable Neo4j vector indexes")
    
    # OpenAI API Configuration
    OPENAI_API_KEY: str = Field(..., description="OpenAI API key")
    OPENAI_ORGANIZATION_ID: str | None = Field(
        default=None, description="OpenAI organization ID"
    )
    
    # Google Gemini API Configuration
    GEMINI_API_KEY: str = Field(..., description="Google Gemini API key")
    GOOGLE_CLOUD_PROJECT_ID: str = Field(..., description="Google Cloud project ID")
    
    # Google Cloud Services
    GOOGLE_APPLICATION_CREDENTIALS: str | None = Field(
        default=None, description="Path to Google Cloud service account key"
    )
    
    # DeepSeek API Configuration
    DEEPSEEK_API_KEY: str = Field(default="", description="DeepSeek API key")
    DEEPSEEK_BASE_URL: str = Field(
        default="https://api.deepseek.com/v1",
        description="DeepSeek API base URL"
    )
    
    # Lexical Network Default Settings
    LEXICAL_DEFAULT_MODEL: str = Field(
        default="gpt-4o-mini",
        description="Default model for lexical relation building"
    )
    LEXICAL_DEFAULT_TEMPERATURE: float = Field(
        default=0.0,
        description="Temperature for AI calls (0.0 for reproducibility)"
    )
    
    # JWT Authentication
    JWT_SECRET_KEY: str = Field(..., description="JWT secret key")
    JWT_ALGORITHM: str = Field(default="HS256", description="JWT algorithm")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=30, description="JWT access token expiration in minutes"
    )
    
    # AI Routing Configuration
    AI_ROUTING_CONFIG_DEFAULT_PROVIDER: str = Field(
        default="openai", description="Default AI provider"
    )
    AI_ROUTING_CONFIG_FALLBACK_ENABLED: bool = Field(
        default=True, description="Enable AI provider fallback"
    )
    AI_ROUTING_CONFIG_COST_OPTIMIZATION: bool = Field(
        default=True, description="Enable cost optimization"
    )
    AI_ROUTING_CONFIG_PERFORMANCE_MONITORING: bool = Field(
        default=True, description="Enable performance monitoring"
    )
    
    # Content Analysis Settings
    CONTENT_ANALYSIS_CONFIDENCE_THRESHOLD: float = Field(
        default=0.8, description="Content analysis confidence threshold"
    )
    CONTENT_ANALYSIS_MAX_FILE_SIZE_MB: int = Field(
        default=10, description="Maximum file size for content analysis in MB"
    )
    CONTENT_ANALYSIS_SUPPORTED_FORMATS: str = Field(
        default="pdf,txt,docx", description="Supported file formats for analysis"
    )
    
    # Voice Services Configuration
    VOICE_STT_LANGUAGE_CODE: str = Field(
        default="ja-JP", description="Speech-to-Text language code"
    )
    VOICE_TTS_VOICE_NAME: str = Field(
        default="ja-JP-Wavenet-B", description="Text-to-Speech voice name"
    )
    VOICE_AUDIO_ENCODING: str = Field(
        default="MP3", description="Audio encoding format"
    )
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = Field(
        default=60, description="Rate limit per minute"
    )
    RATE_LIMIT_BURST: int = Field(default=10, description="Rate limit burst")
    
    # Security Settings
    CORS_ORIGINS: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:3001"],
        description="Allowed CORS origins"
    )
    ALLOWED_HOSTS: list[str] = Field(
        default=["localhost", "127.0.0.1"], description="Allowed hosts"
    )
    
    # Multi-Language Support
    DEFAULT_LANGUAGE: str = Field(default="ja", description="Default language")
    SUPPORTED_LANGUAGES: list[str] = Field(
        default=["ja", "ko", "zh", "hr", "sr", "es", "fr", "de"],
        description="Supported languages"
    )

    # Lesson Orchestration Flags
    LESSON_SOURCE_PRECEDENCE: str = Field(
        default="graph_first",
        description="Source precedence for ActivateCanDo: graph_first | compiled_first | strict_merge"
    )
    GATING_MODE: str = Field(
        default="completion",
        description="Exercise phase gating: completion | score"
    )
    GATING_N: int = Field(
        default=2,
        description="Number of exercises required to complete a phase when GATING_MODE=completion"
    )

    # Available AI Models (as of 2025)
    AVAILABLE_OPENAI_MODELS: list = Field(
        default=[
            {"id": "gpt-5.1", "name": "GPT-5.1", "description": "🌟 Latest flagship model", "recommended": True, "speed": "medium"},
            {"id": "gpt-5", "name": "GPT-5", "description": "🔥 Next-gen advanced", "recommended": False, "speed": "medium"},
            {"id": "gpt-5-mini", "name": "GPT-5 Mini", "description": "⚡ Fast next-gen model", "recommended": False, "speed": "fast"},
            {"id": "gpt-4.1", "name": "GPT-4.1", "description": "🚀 1M context, best JSON", "recommended": False, "speed": "medium"},
            {"id": "gpt-4o", "name": "GPT-4o", "description": "🏆 Excellent multilingual", "recommended": False, "speed": "medium"},
            {"id": "gpt-4o-mini", "name": "GPT-4o Mini", "description": "⚡ Fastest and cheapest", "recommended": False, "speed": "fast"},
            {"id": "gpt-4-turbo", "name": "GPT-4 Turbo", "description": "⚙️ Balanced option", "recommended": False, "speed": "medium"},
            {"id": "o1-preview", "name": "O1 Preview", "description": "🧠 Extended reasoning", "recommended": False, "speed": "slow"},
            {"id": "o1-mini", "name": "O1 Mini", "description": "💡 Fast reasoning", "recommended": False, "speed": "fast"},
        ],
        description="Available OpenAI models"
    )
    
    AVAILABLE_GEMINI_MODELS: list = Field(
        default=[
            {"id": "gemini-2.5-flash", "name": "Gemini 2.5 Flash", "description": "⚡ Fast balanced (120s+ timeout)", "recommended": True, "speed": "fast", "min_timeout": 120},
            {"id": "gemini-2.0-flash-exp", "name": "Gemini 2.0 Flash Exp", "description": "💨 Fastest experimental", "recommended": False, "speed": "fastest", "min_timeout": 90},
            {"id": "gemini-2.0-flash-thinking-exp", "name": "Gemini 2.0 Flash Thinking", "description": "🧠 With reasoning", "recommended": False, "speed": "medium", "min_timeout": 150},
            {"id": "gemini-1.5-pro", "name": "Gemini 1.5 Pro", "description": "📊 Balanced", "recommended": False, "speed": "medium", "min_timeout": 120},
            {"id": "gemini-1.5-flash", "name": "Gemini 1.5 Flash", "description": "💨 Fast efficient", "recommended": False, "speed": "fast", "min_timeout": 90},
            {"id": "gemini-2.5-pro", "name": "Gemini 2.5 Pro", "description": "🎯 Most capable", "recommended": False, "speed": "slow", "min_timeout": 150},
        ],
        description="Available Gemini models"
    )

    # CanDo AI Generation Settings (Legacy Single-Stage)
    CANDO_AI_PROVIDER: str = Field(
        default="openai", description="AI provider for CanDo generation (openai|gemini)"
    )
    CANDO_AI_MODEL: str = Field(
        default="gpt-4o", description="Primary model for CanDo generation"
    )
    CANDO_AI_FALLBACK_MODEL: str = Field(
        default="gpt-4o-mini", description="Fallback model if primary fails"
    )
    
    # CanDo Two-Stage Generation Settings (Recommended)
    CANDO_AI_STAGE1_PROVIDER: str = Field(
        default="openai",
        description="Stage 1 provider for content generation (openai recommended)"
    )
    CANDO_AI_STAGE1_MODEL: str = Field(
        default="gpt-4o",
        description="Stage 1 model for creative content (gpt-4o proven reliable)"
    )
    CANDO_AI_STAGE2_PROVIDER: str = Field(
        default="openai",
        description="Stage 2 provider for structuring (openai recommended)"
    )
    CANDO_AI_STAGE2_MODEL: str = Field(
        default="gpt-4o-mini",
        description="Stage 2 model for JSON structuring (fast and reliable)"
    )
    
    # Feature Flag for Two-Stage Generation
    USE_TWOSTAGE_GENERATION: bool = Field(
        default=True,
        description="Use two-stage generation (Stage 1: content, Stage 2: structure)"
    )
    
    # CanDo Embedding Similarity Settings
    CANDO_SIMILARITY_THRESHOLD: float = Field(
        default=0.65,
        description="Minimum similarity score for creating SEMANTICALLY_SIMILAR relationships (default: 0.65)"
    )
    
    # User Path Generation Settings
    PATH_MAX_STEPS: int = Field(
        default=20,
        description="Maximum steps in learning path (default: 20)"
    )
    PATH_COMPLEXITY_INCREMENT: float = Field(
        default=0.15,
        description="Maximum complexity jump per step (default: 0.15)"
    )
    PATH_SEMANTIC_THRESHOLD: float = Field(
        default=0.7,
        description="Minimum similarity for path continuity (default: 0.7)"
    )
    PATH_COMPLEXITY_MODEL: str = Field(
        default="gpt-4o-mini",
        description="AI model for complexity assessment (default: gpt-4o-mini)"
    )
    PRELESSON_KIT_PREFETCH_N: int = Field(
        default=5,
        description="Number of pre-lesson kits to prefetch during learning path generation (default: 5)"
    )

    # Timeout Settings
    AI_REQUEST_TIMEOUT_SECONDS: int = Field(
        default=90, description="Default timeout in seconds"
    )
    AI_REQUEST_MIN_TIMEOUT: int = Field(
        default=60, description="Minimum allowed timeout"
    )
    AI_REQUEST_MAX_TIMEOUT: int = Field(
        default=300, description="Maximum allowed timeout (5 minutes)"
    )
    
    # Two-Stage Timeout Settings
    AI_STAGE1_TIMEOUT_SECONDS: int = Field(
        default=180,
        description="Stage 1 timeout for content generation (allow more time for creativity)"
    )
    AI_STAGE2_TIMEOUT_SECONDS: int = Field(
        default=60,
        description="Stage 2 timeout per section for structuring (faster, predictable)"
    )
    
    @validator("CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: Any) -> list[str] | str:
        """Parse CORS origins from string or list."""
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)
    
    @validator("ALLOWED_HOSTS", pre=True)
    def assemble_allowed_hosts(cls, v: Any) -> list[str] | str:
        """Parse allowed hosts from string or list."""
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)
    
    @validator("SUPPORTED_LANGUAGES", pre=True)
    def assemble_supported_languages(cls, v: Any) -> list[str] | str:
        """Parse supported languages from string or list."""
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # Pydantic v2 / pydantic-settings v2 configuration.
    #
    # Reason: the repo stores a single `.env` at the repository root. Using a
    # computed absolute path avoids surprises when the working directory differs
    # (tests, uvicorn, Docker).
    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",  # Ignore extra environment variables like NEXT_PUBLIC_*
        case_sensitive=True,
    )


# Global settings instance
settings = Settings()