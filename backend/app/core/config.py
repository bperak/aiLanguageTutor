"""
Configuration settings for the AI Language Tutor Backend API.

This module uses Pydantic Settings to load and validate configuration
from environment variables with sensible defaults.
"""

from typing import Any

from pydantic import Field, validator
from pydantic_settings import BaseSettings


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
    
    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()