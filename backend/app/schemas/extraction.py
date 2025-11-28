from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field


class WordEntity(BaseModel):
    text: str = Field(min_length=1)
    standard_orthography: str = Field(min_length=1)
    hiragana: str = Field(min_length=0)
    romaji: str = Field(min_length=0)


class GrammarPatternEntity(BaseModel):
    pattern: str = Field(min_length=1)
    example: Optional[str] = None


class EntitiesExtractionResponse(BaseModel):
    words: List[WordEntity] = Field(default_factory=list, max_items=20)
    grammarPatterns: List[GrammarPatternEntity] = Field(default_factory=list, max_items=10)


