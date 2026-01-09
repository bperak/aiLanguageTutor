# Base models shared across the cando_creation package
from __future__ import annotations

from typing import Dict, List, Literal, Optional, Any

from pydantic import BaseModel, Field, ConfigDict, field_validator


class JPText(BaseModel):
    model_config = ConfigDict(extra="forbid")
    std: str
    furigana: str
    romaji: str
    translation: Dict[str, str] = Field(
        description="Translation as a dictionary with language codes as keys. Example: {'en': 'Hello', 'ja': 'こんにちは'}. Must be a dict, NOT a string."
    )

    @field_validator("translation", mode="before")
    @classmethod
    def validate_translation_is_dict(cls, v: Any) -> Dict[str, str]:
        """Ensure translation is a Dict[str, str], not a string. Auto-convert strings to dict with 'en' key."""
        if isinstance(v, str):
            # Auto-convert string to dict with 'en' key (most common metalanguage)
            return {"en": v}
        return v


class ImageSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    prompt: str
    style: Literal["flat-icon", "scene-illustration", "diagram", "infographic", "photo"]
    size: Literal["1024x1024", "1280x720", "1280x768", "2048x2048"]
    negative_prompt: Optional[str] = None
    seed: Optional[int] = None
    path: Optional[str] = None  # Relative path to generated image file


class LLMGenSpec(BaseModel):
    """Carry the exact prompts used to generate a card for traceability/repro."""

    model_config = ConfigDict(extra="forbid")
    system: str
    instruction: str
    constraints: List[str] = Field(default_factory=list)
    examples: Optional[str] = None

