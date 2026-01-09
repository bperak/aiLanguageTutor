"""
Core enumerations for the application.

Centralized enum definitions for lesson phases and AI providers
to ensure type safety and prevent magic strings throughout the codebase.
"""

from enum import Enum


class LessonPhase(str, Enum):
    """Lesson progression phases for learner progression through material."""

    LEXICON_AND_PATTERNS = "lexicon_and_patterns"
    """Initial phase: learning vocabulary and grammar patterns."""

    GUIDED_DIALOGUE = "guided_dialogue"
    """Intermediate phase: guided conversation practice with correction."""

    OPEN_DIALOGUE = "open_dialogue"
    """Advanced phase: open-ended conversation with minimal scaffolding."""

    DONE = "done"
    """Lesson complete; no further progression."""

    def __str__(self) -> str:
        return self.value


class AIProvider(str, Enum):
    """Supported AI providers for content generation and analysis."""

    OPENAI = "openai"
    """OpenAI (GPT-4o, GPT-4o-mini)."""

    GEMINI = "gemini"
    """Google Gemini (Gemini 2.5 Pro, Gemini 2.5 Flash)."""

    def __str__(self) -> str:
        return self.value


# Convenience constants
PHASE_SEQUENCE = [
    LessonPhase.LEXICON_AND_PATTERNS,
    LessonPhase.GUIDED_DIALOGUE,
    LessonPhase.OPEN_DIALOGUE,
    LessonPhase.DONE,
]
"""Ordered list of lesson phases for phase progression."""

VALID_PROVIDERS = [AIProvider.OPENAI, AIProvider.GEMINI]
"""List of valid AI providers."""
