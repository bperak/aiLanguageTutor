"""
AI Provider Implementations

Unified interface for multiple AI providers (OpenAI, Gemini, DeepSeek)
with temperature=0 for reproducibility and comprehensive metadata tracking.
"""

import asyncio
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional

import structlog

try:
    from google import genai
    from google.genai import types
    GOOGLE_GENAI_AVAILABLE = True
except ImportError:
    genai = None
    types = None
    GOOGLE_GENAI_AVAILABLE = False

try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    AsyncOpenAI = None
    OPENAI_AVAILABLE = False

from app.core.config import settings
from app.services.lexical_network.ai_provider_config import (
    AIModelConfig,
    AVAILABLE_MODELS,
    get_model_config,
)

logger = structlog.get_logger()

# CRITICAL: Temperature is always 0.0 for reproducibility
DEFAULT_TEMPERATURE: float = 0.0


@dataclass
class AIGenerationResult:
    """Result from AI generation with full metadata."""
    
    content: str
    provider: str
    model: str
    model_version: Optional[str]
    temperature: float  # Always 0.0
    tokens_input: int
    tokens_output: int
    cost_usd: float
    latency_ms: int
    request_id: str
    raw_response: Optional[Dict] = None  # For debugging


class LexicalAIProvider(ABC):
    """Abstract base for lexical relation AI providers."""
    
    # CRITICAL: Temperature is always 0 for reproducibility
    DEFAULT_TEMPERATURE: float = 0.0
    
    @abstractmethod
    async def generate_relations(
        self,
        prompt: str,
        system_prompt: str,
        max_tokens: int = 4096,
    ) -> AIGenerationResult:
        """
        Generate relation candidates from prompt.
        
        IMPORTANT: Temperature is always 0.0 for deterministic outputs.
        This ensures reproducibility and consistent relation quality.
        
        Args:
            prompt: User prompt with word data and candidates
            system_prompt: System instructions
            max_tokens: Maximum output tokens
            
        Returns:
            AIGenerationResult with content and full metadata
        """
        pass
    
    @abstractmethod
    def get_model_config(self) -> AIModelConfig:
        """Return model configuration."""
        pass
    
    def _calculate_cost(
        self, tokens_input: int, tokens_output: int
    ) -> float:
        """Calculate cost in USD based on model pricing."""
        config = self.get_model_config()
        input_cost = (tokens_input / 1000.0) * config.input_cost_per_1k
        output_cost = (tokens_output / 1000.0) * config.output_cost_per_1k
        return input_cost + output_cost


class OpenAIProvider(LexicalAIProvider):
    """OpenAI implementation with temperature=0."""
    
    def __init__(self, model: str = "gpt-4o-mini"):
        if not OPENAI_AVAILABLE:
            raise ImportError("openai package not available")
        self.model = model
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.config = get_model_config(model)
    
    async def generate_relations(
        self,
        prompt: str,
        system_prompt: str,
        max_tokens: int = 4096,
    ) -> AIGenerationResult:
        """Generate relations using OpenAI API."""
        start_time = time.time()
        request_id = str(uuid.uuid4())
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.0,  # CRITICAL: Always 0 for reproducibility
                max_tokens=max_tokens,
                response_format={"type": "json_object"}
                if self.config.supports_json_mode
                else None,
            )
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            tokens_input = response.usage.prompt_tokens
            tokens_output = response.usage.completion_tokens
            
            return AIGenerationResult(
                content=response.choices[0].message.content,
                provider="openai",
                model=self.model,
                model_version=response.model,
                temperature=0.0,
                tokens_input=tokens_input,
                tokens_output=tokens_output,
                cost_usd=self._calculate_cost(tokens_input, tokens_output),
                latency_ms=latency_ms,
                request_id=request_id,
                raw_response=response.model_dump() if hasattr(response, "model_dump") else None,
            )
        except Exception as e:
            logger.error(
                "OpenAI generation failed",
                model=self.model,
                error=str(e),
                request_id=request_id,
            )
            raise
    
    def get_model_config(self) -> AIModelConfig:
        """Return model configuration."""
        return self.config


class GeminiProvider(LexicalAIProvider):
    """Google Gemini implementation with temperature=0."""
    
    def __init__(self, model: str = "gemini-2.5-flash"):
        if not GOOGLE_GENAI_AVAILABLE:
            raise ImportError("google-genai package not available")
        self.model = model
        self.config = get_model_config(model)
        if not settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not configured")
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
    
    async def generate_relations(
        self,
        prompt: str,
        system_prompt: str,
        max_tokens: int = 4096,
    ) -> AIGenerationResult:
        """Generate relations using Gemini API."""
        start_time = time.time()
        request_id = str(uuid.uuid4())
        
        try:
            # Combine system and user prompts for Gemini
            full_prompt = f"{system_prompt}\n\n{prompt}"
            
            generation_config = types.GenerateContentConfig(
                temperature=0.0,  # CRITICAL: Always 0
                max_output_tokens=max_tokens,
                response_mime_type="application/json",
            )
            
            # Gemini API is synchronous, so we need to run it in a thread
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=f"models/{self.model}",
                contents=[
                    types.Content(
                        role="user",
                        parts=[types.Part.from_text(text=full_prompt)]
                    )
                ],
                config=generation_config,
            )
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            # Extract text from response
            text_content = ""
            try:
                text_content = response.text if response.text else ""
            except (AttributeError, ValueError):
                # Try alternate extraction
                if hasattr(response, 'candidates') and response.candidates:
                    candidate = response.candidates[0]
                    if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                        for part in candidate.content.parts:
                            if hasattr(part, 'text'):
                                text_content += part.text
            
            # Estimate tokens (Gemini doesn't always provide usage)
            # Rough estimate: 1 token ≈ 4 characters
            estimated_input_tokens = len(full_prompt) // 4
            estimated_output_tokens = len(text_content) // 4
            
            return AIGenerationResult(
                content=text_content,
                provider="gemini",
                model=self.model,
                model_version=self.model,
                temperature=0.0,
                tokens_input=estimated_input_tokens,
                tokens_output=estimated_output_tokens,
                cost_usd=self._calculate_cost(
                    estimated_input_tokens, estimated_output_tokens
                ),
                latency_ms=latency_ms,
                request_id=request_id,
                raw_response=None,
            )
        except Exception as e:
            logger.error(
                "Gemini generation failed",
                model=self.model,
                error=str(e),
                request_id=request_id,
            )
            raise
    
    def get_model_config(self) -> AIModelConfig:
        """Return model configuration."""
        return self.config


class DeepSeekProvider(LexicalAIProvider):
    """DeepSeek implementation with temperature=0."""
    
    def __init__(self, model: str = "deepseek-chat"):
        if not OPENAI_AVAILABLE:
            raise ImportError("openai package not available (DeepSeek uses OpenAI client)")
        self.model = model
        self.config = get_model_config(model)
        if not settings.DEEPSEEK_API_KEY:
            raise ValueError("DEEPSEEK_API_KEY not configured")
        self.client = AsyncOpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL,
        )
    
    async def generate_relations(
        self,
        prompt: str,
        system_prompt: str,
        max_tokens: int = 4096,
    ) -> AIGenerationResult:
        """Generate relations using DeepSeek API (OpenAI-compatible)."""
        start_time = time.time()
        request_id = str(uuid.uuid4())
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.0,  # CRITICAL: Always 0
                max_tokens=max_tokens,
                response_format={"type": "json_object"}
                if self.config.supports_json_mode
                else None,
            )
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            tokens_input = response.usage.prompt_tokens
            tokens_output = response.usage.completion_tokens
            
            return AIGenerationResult(
                content=response.choices[0].message.content,
                provider="deepseek",
                model=self.model,
                model_version=response.model,
                temperature=0.0,
                tokens_input=tokens_input,
                tokens_output=tokens_output,
                cost_usd=self._calculate_cost(tokens_input, tokens_output),
                latency_ms=latency_ms,
                request_id=request_id,
                raw_response=response.model_dump() if hasattr(response, "model_dump") else None,
            )
        except Exception as e:
            logger.error(
                "DeepSeek generation failed",
                model=self.model,
                error=str(e),
                request_id=request_id,
            )
            raise
    
    def get_model_config(self) -> AIModelConfig:
        """Return model configuration."""
        return self.config


class AIProviderManager:
    """Manager for AI provider selection and fallback."""
    
    def __init__(self):
        self.providers: Dict[str, LexicalAIProvider] = {}
    
    def get_provider(self, model_key: str) -> LexicalAIProvider:
        """
        Get provider for specified model.
        
        Args:
            model_key: Model identifier (e.g., "gpt-4o-mini")
            
        Returns:
            LexicalAIProvider instance
            
        Raises:
            ValueError: If model is unknown
        """
        if model_key not in self.providers:
            config = AVAILABLE_MODELS.get(model_key)
            if not config:
                raise ValueError(f"Unknown model: {model_key}")
            
            if config.provider == "openai":
                self.providers[model_key] = OpenAIProvider(model_key)
            elif config.provider == "gemini":
                self.providers[model_key] = GeminiProvider(model_key)
            elif config.provider == "deepseek":
                self.providers[model_key] = DeepSeekProvider(model_key)
            else:
                raise ValueError(f"Unknown provider: {config.provider}")
        
        return self.providers[model_key]
    
    def list_available_models(self) -> List[AIModelConfig]:
        """List all available models with their configs."""
        return list(AVAILABLE_MODELS.values())
    
    def get_recommended_model(self, use_case: str = "batch") -> str:
        """Get recommended model for use case."""
        for key, config in AVAILABLE_MODELS.items():
            if use_case in config.recommended_for:
                return key
        return "gpt-4o-mini"  # Default fallback
