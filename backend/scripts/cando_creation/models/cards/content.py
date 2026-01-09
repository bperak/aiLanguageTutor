# Content stage card models
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, ConfigDict, field_validator

from ..base import ImageSpec, JPText, LLMGenSpec
from ..meta import TextLayerPrefs


class ObjectiveCard(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["ObjectiveCard"] = "ObjectiveCard"
    title: Dict[str, str]
    body: Dict[str, str]
    success_criteria: List[str]
    outcomes: List[str] = Field(default_factory=list)
    gen: Optional[LLMGenSpec] = None


class WordItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    neo4j_id: Optional[str] = None
    jp: JPText
    tags: List[str] = Field(default_factory=list)
    image: Optional[ImageSpec] = None


class WordsCard(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["WordsCard"] = "WordsCard"
    items: List[WordItem]
    ui_layers_override: Optional[TextLayerPrefs] = None
    gen: Optional[LLMGenSpec] = None


class PatternExample(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ja: JPText
    audio_ref: Optional[str] = None


class PatternForm(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ja: JPText


class GrammarPatternItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str  # MUST match a DomainPlan.grammar_functions[i].id
    neo4j_id: Optional[str] = None
    form: PatternForm
    explanation: Dict[str, str] = Field(
        description="Explanation as a dictionary with language codes as keys. Example: {'en': 'This pattern...', 'ja': 'このパターンは...'}. Must be a dict, NOT a string."
    )
    slots: List[str]
    examples: List[PatternExample]
    image: Optional[ImageSpec] = None

    @field_validator("explanation", mode="before")
    @classmethod
    def validate_explanation_is_dict(cls, v: Any) -> Dict[str, str]:
        """Ensure explanation is a Dict[str, str], not a string."""
        if isinstance(v, str):
            raise ValueError(
                f"GrammarPatternItem.explanation must be a Dict[str, str] with language codes as keys (e.g., {{'en': 'Explanation'}}), "
                f"not a string. Received string: {v[:50]}..."
            )
        return v


class GrammarPatternsCard(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["GrammarPatternsCard"] = "GrammarPatternsCard"
    patterns: List[GrammarPatternItem]
    gen: Optional[LLMGenSpec] = None


class DialogueTurn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    speaker: str  # free label from plan.scenarios[*].roles
    ja: JPText
    audio_ref: Optional[str] = None


class DialogueCard(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["DialogueCard"] = "DialogueCard"
    title: Dict[str, str]
    setting: Optional[str] = None  # Contextual opening paragraph for the dialogue scene
    characters: Optional[List[str]] = None  # Optional list of character names
    turns: List[DialogueTurn]
    notes_en: Optional[str] = None
    image: Optional[ImageSpec] = None
    gen: Optional[LLMGenSpec] = None


class ComprehensionQA(BaseModel):
    model_config = ConfigDict(extra="forbid")
    q: JPText  # Question in Japanese
    a: JPText  # Answer in Japanese
    evidenceSpan: Optional[str] = None  # Text span in reading that supports answer


class ReadingSection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: JPText  # Title of the reading passage
    content: JPText  # Full reading text (200+ words)
    comprehension: List[ComprehensionQA]  # 5-7 comprehension questions


class ReadingCard(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["ReadingCard"] = "ReadingCard"
    title: Dict[str, str] = Field(
        description="Multilingual title as a dictionary with language codes as keys (e.g., {'en': 'Title', 'ja': 'タイトル'}). Must be a plain dict, NOT a JPText object."
    )
    reading: ReadingSection  # Contains title, content (JPText), comprehension (List[ComprehensionQA])
    notes_en: Optional[str] = None
    image: Optional[ImageSpec] = None
    gen: Optional[LLMGenSpec] = None

    @field_validator("title", mode="before")
    @classmethod
    def validate_title_not_jptext(cls, v: Any) -> Dict[str, str]:
        """Ensure title is a Dict[str, str], not a JPText object."""
        if isinstance(v, dict):
            # Check if it looks like a JPText object (has 'std', 'furigana', 'romaji', or 'translation' keys)
            if any(key in v for key in ["std", "furigana", "romaji", "translation"]):
                raise ValueError(
                    f"ReadingCard.title must be a Dict[str, str] with language codes as keys (e.g., {{'en': 'Title', 'ja': 'タイトル'}}), "
                    f"not a JPText object. Received: {v}"
                )
            # Ensure all values are strings
            for key, value in v.items():
                if not isinstance(value, str):
                    raise ValueError(
                        f"ReadingCard.title values must be strings. Key '{key}' has value of type {type(value).__name__}: {value}"
                    )
        return v

