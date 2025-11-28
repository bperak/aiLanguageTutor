from __future__ import annotations

from typing import Any, Dict, List, Optional
import re
from pydantic import BaseModel, Field, field_validator, ConfigDict


_JP_RE = re.compile(r"[\u3040-\u30FF\u4E00-\u9FFF]")


class TextTriplet(BaseModel):
    """Bilingual text with romaji transliteration.

    Ensures jp contains Japanese script and en does not, and romaji is non-empty when jp exists.
    """

    jp: str = Field(min_length=1)
    en: str = Field(min_length=1)
    romaji: str = Field(min_length=1)

    @field_validator("jp")
    @classmethod
    def _jp_has_japanese(cls, v: str) -> str:
        if not _JP_RE.search(v):
            raise ValueError("jp must contain Japanese characters")
        return v

    @field_validator("en")
    @classmethod
    def _en_no_japanese(cls, v: str) -> str:
        if _JP_RE.search(v):
            raise ValueError("en must not contain Japanese characters")
        return v

    @field_validator("romaji")
    @classmethod
    def _romaji_non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("romaji must be non-empty")
        return v


TitleTriplet = TextTriplet


class Metadata(BaseModel):
    model_config = ConfigDict(extra="allow")

    topic_ja: str = Field(min_length=1)
    topic_en: str = Field(min_length=1)
    topic_romaji: str = Field(min_length=1)
    languageCode: str = Field(default="ja")
    createdAt: int
    estimatedDurationMin: int
    tags: List[str] = Field(default_factory=list)

    @field_validator("topic_ja")
    @classmethod
    def _topic_ja_has_jp(cls, v: str) -> str:
        if not _JP_RE.search(v):
            raise ValueError("topic_ja must contain Japanese characters")
        return v

    @field_validator("topic_en")
    @classmethod
    def _topic_en_no_jp(cls, v: str) -> str:
        if _JP_RE.search(v):
            raise ValueError("topic_en must not contain Japanese characters")
        return v

    @field_validator("topic_romaji")
    @classmethod
    def _topic_romaji_non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("topic_romaji must be non-empty")
        return v


class VariantGuideline(BaseModel):
    model_config = ConfigDict(extra="allow")

    scaffolding: Optional[str] = None
    aids: List[str] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)
    notes_ja: List[str] = Field(default_factory=list)
    notes_romaji: Optional[List[str]] = None


class Exercise(BaseModel):
    id: str
    type: str
    stem: TextTriplet
    choices: Optional[List[TextTriplet]] = None
    answerKey: Any
    rationale: Optional[TextTriplet] = None
    levelTag: Optional[int] = None


class LessonMaster(BaseModel):
    model_config = ConfigDict(extra="allow")

    uiVersion: int
    lessonId: str
    canDoId: str
    originalLevel: Optional[int] = None
    metadata: Metadata
    learningObjectives: List[str] = Field(default_factory=list)
    learningObjectivesJa: Optional[List[str]] = None
    variantGuidelines: Dict[str, VariantGuideline] = Field(default_factory=dict)
    ui: Dict[str, Any]
    exercises: Optional[List[Exercise]] = None
    extractedEntities: Optional[Dict[str, Any]] = None


