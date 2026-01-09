# Meta and graph models
from __future__ import annotations

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field, ConfigDict

from .base import LLMGenSpec


class CanDoMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")
    uid: str
    level: Literal["A1", "A2", "B1", "B2", "C1", "C2"]
    primaryTopic_ja: str
    primaryTopic_en: str
    skillDomain_ja: str
    type_ja: str
    description: Dict[str, str]  # {"en": "...", "ja": "..."}
    source: str  # from Neo4j CanDoDescriptor.source
    titleEn: Optional[str] = None  # AI-generated title in English
    titleJa: Optional[str] = None  # AI-generated title in Japanese


class LessonMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")
    lesson_id: str
    metalanguage: Literal["en", "hr", "ja", "de", "fr", "it", "es"]
    can_do: CanDoMeta  # Injected directly from Neo4j CanDoDescriptor + metalanguage


class LookupSpec(BaseModel):
    """
    Relation-agnostic binding:
      - by_cypher: provide explicit Cypher (optional)
      - by_keys: business keys to resolve later (optional)
      - resolve_label / resolve_property: optional hints to build Cypher outside LLM
    """

    model_config = ConfigDict(extra="forbid")
    by_cypher: Optional[str] = None
    by_keys: List[str] = Field(default_factory=list)
    resolve_label: Optional[str] = None
    resolve_property: Optional[str] = None


class GraphBindings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    words: LookupSpec = Field(default_factory=LookupSpec)
    grammar_patterns: LookupSpec = Field(default_factory=LookupSpec)


class TextLayerPrefs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    std: bool = True
    furigana: bool = True
    romaji: bool = False
    translation: bool = True


class UIPrefs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text_layers_default: TextLayerPrefs = Field(default_factory=TextLayerPrefs)

