"""
AI Provider Configuration

Defines available AI models with their configurations, costs, and capabilities.
"""

from dataclasses import dataclass
from typing import Dict, List


@dataclass
class AIModelConfig:
    """Configuration for an AI model."""
    
    provider: str  # openai, gemini, deepseek
    model_id: str  # gpt-4o-mini, gemini-2.5-flash, etc.
    display_name: str  # Human-readable name
    input_cost_per_1k: float  # USD per 1K input tokens
    output_cost_per_1k: float  # USD per 1K output tokens
    max_tokens: int  # Maximum output tokens
    supports_json_mode: bool  # Native JSON output support
    recommended_for: List[str]  # ["batch", "realtime", "low_cost"]


# ===============================================
# Available Models Configuration
# ===============================================

AVAILABLE_MODELS: Dict[str, AIModelConfig] = {
    # === OpenAI Models ===
    "gpt-4o-mini": AIModelConfig(
        provider="openai",
        model_id="gpt-4o-mini",
        display_name="GPT-4o Mini (Recommended)",
        input_cost_per_1k=0.00015,
        output_cost_per_1k=0.0006,
        max_tokens=16384,
        supports_json_mode=True,
        recommended_for=["batch", "low_cost"],
    ),
    "gpt-4o": AIModelConfig(
        provider="openai",
        model_id="gpt-4o",
        display_name="GPT-4o",
        input_cost_per_1k=0.0025,
        output_cost_per_1k=0.01,
        max_tokens=16384,
        supports_json_mode=True,
        recommended_for=["quality"],
    ),
    
    # === Gemini Models ===
    "gemini-2.5-flash": AIModelConfig(
        provider="gemini",
        model_id="gemini-2.5-flash",
        display_name="Gemini 2.5 Flash",
        input_cost_per_1k=0.000075,
        output_cost_per_1k=0.0003,
        max_tokens=8192,
        supports_json_mode=True,
        recommended_for=["batch", "low_cost"],
    ),
    "gemini-2.0-flash-exp": AIModelConfig(
        provider="gemini",
        model_id="gemini-2.0-flash-exp",
        display_name="Gemini 2.0 Flash (Free)",
        input_cost_per_1k=0.0,
        output_cost_per_1k=0.0,
        max_tokens=8192,
        supports_json_mode=True,
        recommended_for=["free_tier"],
    ),
    
    # === DeepSeek Models ===
    "deepseek-chat": AIModelConfig(
        provider="deepseek",
        model_id="deepseek-chat",
        display_name="DeepSeek Chat (Very Cheap)",
        input_cost_per_1k=0.00014,
        output_cost_per_1k=0.00028,
        max_tokens=8192,
        supports_json_mode=True,
        recommended_for=["batch", "lowest_cost"],
    ),
    "deepseek-reasoner": AIModelConfig(
        provider="deepseek",
        model_id="deepseek-reasoner",
        display_name="DeepSeek Reasoner",
        input_cost_per_1k=0.00055,
        output_cost_per_1k=0.00219,
        max_tokens=8192,
        supports_json_mode=True,
        recommended_for=["quality"],
    ),
}


def get_model_config(model_key: str) -> AIModelConfig:
    """Get configuration for a model."""
    if model_key not in AVAILABLE_MODELS:
        raise ValueError(f"Unknown model: {model_key}")
    return AVAILABLE_MODELS[model_key]


def list_available_models() -> List[AIModelConfig]:
    """List all available models."""
    return list(AVAILABLE_MODELS.values())


def get_recommended_model(use_case: str = "batch") -> str:
    """Get recommended model for use case."""
    for key, config in AVAILABLE_MODELS.items():
        if use_case in config.recommended_for:
            return key
    return "gpt-4o-mini"  # Default fallback
