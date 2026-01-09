# Interaction stage card models
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, ConfigDict

from ..base import LLMGenSpec

if TYPE_CHECKING:
    from .exercises import GuidedStage
else:
    # Import at runtime to avoid circular dependency
    from .exercises import GuidedStage


class InteractiveDialogueCard(BaseModel):
    """AI conversation partner for interaction stage"""

    model_config = ConfigDict(extra="forbid")
    type: Literal["InteractiveDialogueCard"] = "InteractiveDialogueCard"
    title: Dict[str, str]
    scenarios: List[Dict[str, Any]]  # Conversation scenarios
    stages: List[GuidedStage]  # Reuse GuidedStage structure
    gen: Optional[LLMGenSpec] = None


class InteractionActivityItem(BaseModel):
    """Activity item for interaction stage"""

    model_config = ConfigDict(extra="forbid")
    activity_type: Literal[
        "conversation_scenario",
        "information_gap",
        "negotiation",
        "collaborative_task",
        "simulation",
        "problem_solving",
        "opinion_exchange",
        "decision_making",
        "role_play",
        "free_conversation",
    ]
    id: str
    title: Dict[str, str]
    instructions: Dict[str, str]
    scenario: Optional[Dict[str, Any]] = None  # Scenario details
    roles: Optional[List[str]] = None  # For role_play
    goals: Optional[List[str]] = None  # Activity goals
    gen: Optional[LLMGenSpec] = None


class InteractionActivitiesCard(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["InteractionActivitiesCard"] = "InteractionActivitiesCard"
    title: Dict[str, str]
    items: List[InteractionActivityItem]
    gen: Optional[LLMGenSpec] = None


class AIScenarioStage(BaseModel):
    """Stage for AI scenario manager"""

    model_config = ConfigDict(extra="forbid")
    stage_id: str
    scenario_type: str
    goal_en: str
    context: Dict[str, str]  # Scenario context
    roles: List[Dict[str, str]]  # Role definitions
    conversation_flow: List[Dict[str, Any]]  # Expected conversation flow
    evaluation_criteria: Dict[str, Any]  # How to evaluate interaction quality
    cultural_notes: Optional[List[Dict[str, str]]] = None


class AIScenarioManagerCard(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["AIScenarioManagerCard"] = "AIScenarioManagerCard"
    title: Dict[str, str]
    stages: List[AIScenarioStage]
    gen: Optional[LLMGenSpec] = None

