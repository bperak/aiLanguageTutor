# DomainPlan and related models
from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field, ConfigDict


class PlanRole(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label: str  # free label, e.g., "Guide", "Friend", "Clerk"
    register: Literal["plain", "polite", "neutral"] = "polite"


class PlanScenario(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    setting: str  # e.g., "outdoors", "classroom"
    roles: List[PlanRole]


class PlanLexBucket(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str  # e.g., "places", "specialties", "actions", "connectors"
    items: List[str]  # JP surface forms (std only). No furigana/romaji here.


class PlanGrammarFunction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str  # stable id for cross-refs, e.g., "gf_001"
    label: str  # e.g., "fame/reason", "existence/location"
    pattern_ja: str  # JP skeleton (std), e.g., "XはYで有名です"
    slots: List[str]  # e.g., ["X:place", "Y:feature"]
    notes_en: Optional[str] = None


class PlanEvaluation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    success_criteria: List[str]
    discourse_markers: List[
        str
    ]  # e.g., ["まず","次に","最後に"] or others per function


class DomainPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")
    uid: str
    level: Literal["A1", "A2", "B1", "B2", "C1", "C2"]
    communicative_function_en: str
    communicative_function_ja: str
    scenarios: List[PlanScenario]
    lex_buckets: List[PlanLexBucket]
    grammar_functions: List[PlanGrammarFunction]
    evaluation: PlanEvaluation
    cultural_themes_en: List[str]
    cultural_themes_ja: List[str]

