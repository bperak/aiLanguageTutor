"""
Quality assessment and reporting for CanDo lesson generation.

This module provides pure functions to evaluate lesson quality based on:
- PreLessonKit coverage (words, grammar, phrases)
- Topic/descriptor alignment
- Prompt/template leak detection
- Minimum structure validation
"""

from enum import Enum
from typing import Dict, Any, List, Optional, Set
from pydantic import BaseModel, Field
import re


class QualityMode(str, Enum):
    """Quality enforcement mode."""
    OFF = "off"
    WARN = "warn"
    ENFORCE = "enforce"


class QualityIssue(BaseModel):
    """A single quality issue detected in a lesson."""
    severity: str = Field(..., description="blocking|warning|info")
    category: str = Field(..., description="kit_coverage|topic_mismatch|prompt_leak|structure|other")
    message: str = Field(..., description="Human-readable description")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Additional context")


class KitCoverage(BaseModel):
    """Coverage metrics for PreLessonKit components."""
    words_total: int = 0
    words_hit: int = 0
    words_ratio: float = 0.0
    grammar_total: int = 0
    grammar_hit: int = 0
    grammar_ratio: float = 0.0
    phrases_total: int = 0
    phrases_hit: int = 0
    phrases_ratio: float = 0.0


class QualityReport(BaseModel):
    """Complete quality assessment report for a lesson."""
    overall_score: float = Field(..., ge=0.0, le=1.0, description="Overall quality score 0-1")
    issues: List[QualityIssue] = Field(default_factory=list)
    kit_coverage: Optional[KitCoverage] = None
    has_blocking_issues: bool = False
    passed: bool = Field(..., description="True if lesson passes quality gates")


def flatten_lesson_text(master: Dict[str, Any]) -> str:
    """
    Extract all text content from a lesson master for analysis.
    
    Reuses logic similar to _flatten_ui_text but handles both Stage1 and Stage2 formats.
    
    Args:
        master: Lesson master dict (can be Stage1 or merged Stage2 format)
        
    Returns:
        Flattened text string (truncated to 12000 chars for efficiency)
    """
    lines: List[str] = []
    
    # Handle Stage1 format (simple content)
    if "lessonPlan" in master:
        for step in master.get("lessonPlan", []):
            if isinstance(step, dict):
                if step.get("title"):
                    lines.append(str(step["title"]))
                if step.get("contentJP"):
                    lines.append(str(step["contentJP"]))
                if step.get("goalsJP"):
                    lines.append(str(step["goalsJP"]))
        
        reading = master.get("reading")
        if reading and isinstance(reading, dict):
            if reading.get("title"):
                lines.append(str(reading["title"]))
            if reading.get("text"):
                lines.append(str(reading["text"]))
        
        dialogue = master.get("dialogue", [])
        for turn in dialogue:
            if isinstance(turn, dict):
                if turn.get("text"):
                    lines.append(str(turn["text"]))
        
        grammar = master.get("grammar", [])
        for gp in grammar:
            if isinstance(gp, dict):
                if gp.get("pattern"):
                    lines.append(str(gp["pattern"]))
                if gp.get("explanation"):
                    lines.append(str(gp["explanation"]))
                for ex in gp.get("examples", []):
                    if isinstance(ex, str):
                        lines.append(ex)
    
    # Handle Stage2/merged format (UI structure)
    ui = master.get("ui", {}) or {}
    header = ui.get("header") or {}
    if header.get("title"):
        title_val = header.get("title")
        if isinstance(title_val, dict):
            lines.append(str(title_val.get("jp", "")))
            lines.append(str(title_val.get("en", "")))
        else:
            lines.append(str(title_val))
    if header.get("subtitle"):
        subtitle_val = header.get("subtitle")
        if isinstance(subtitle_val, dict):
            lines.append(str(subtitle_val.get("jp", "")))
            lines.append(str(subtitle_val.get("en", "")))
        else:
            lines.append(str(subtitle_val))
    
    for sec in ui.get("sections", []) or []:
        title = sec.get("title")
        if title:
            if isinstance(title, dict):
                lines.append(str(title.get("jp", "")))
                lines.append(str(title.get("en", "")))
            else:
                lines.append(str(title))
        
        for card in sec.get("cards", []) or []:
            if card.get("title"):
                title_val = card.get("title")
                if isinstance(title_val, dict):
                    lines.append(str(title_val.get("jp", "")))
                    lines.append(str(title_val.get("en", "")))
                else:
                    lines.append(str(title_val))
            
            body = card.get("body") or {}
            if isinstance(body, dict):
                jp = body.get("jp")
                en = body.get("en")
                if jp:
                    lines.append(str(jp))
                if en:
                    lines.append(str(en))
            
            # Dialogue turns
            turns = card.get("turns") or []
            for turn in turns:
                if isinstance(turn, dict):
                    jp = turn.get("jp")
                    en = turn.get("en")
                    if jp:
                        lines.append(str(jp))
                    if en:
                        lines.append(str(en))
            
            # Bullets
            for b in card.get("bullets", []) or []:
                lines.append(str(b))
    
    # Exercises
    exercises = master.get("exercises", [])
    for ex in exercises:
        if isinstance(ex, dict):
            stem = ex.get("stem")
            if isinstance(stem, dict):
                if stem.get("jp"):
                    lines.append(str(stem["jp"]))
                if stem.get("en"):
                    lines.append(str(stem["en"]))
            for choice in ex.get("choices", []):
                if isinstance(choice, dict):
                    if choice.get("jp"):
                        lines.append(str(choice["jp"]))
                    if choice.get("en"):
                        lines.append(str(choice["en"]))
    
    return "\n".join(lines)[:12000]


def compute_kit_coverage(text: str, kit: Optional[Dict[str, Any]]) -> KitCoverage:
    """
    Compute how well the lesson text uses PreLessonKit components.
    
    Args:
        text: Flattened lesson text
        kit: PreLessonKit dict (or None)
        
    Returns:
        KitCoverage with hit counts and ratios
    """
    if not kit:
        return KitCoverage()
    
    text_lower = text.lower()
    words_total = 0
    words_hit = 0
    grammar_total = 0
    grammar_hit = 0
    phrases_total = 0
    phrases_hit = 0
    
    # Check words (component 1)
    words = kit.get("necessary_words", [])
    words_total = len(words)
    for word in words:
        if not isinstance(word, dict):
            continue
        # Check surface, reading, translation
        surface = str(word.get("surface", "")).strip()
        reading = str(word.get("reading", "")).strip()
        translation = str(word.get("translation", "")).strip()
        
        if surface and (surface in text or surface.lower() in text_lower):
            words_hit += 1
        elif reading and (reading in text or reading.lower() in text_lower):
            words_hit += 1
        elif translation and translation.lower() in text_lower:
            words_hit += 1
    
    # Check grammar patterns (component 2)
    grammar = kit.get("necessary_grammar_patterns", [])
    grammar_total = len(grammar)
    for gp in grammar:
        if not isinstance(gp, dict):
            continue
        pattern = str(gp.get("pattern", "")).strip()
        if pattern and pattern in text:
            grammar_hit += 1
    
    # Check fixed phrases (component 3)
    phrases = kit.get("necessary_fixed_phrases", [])
    phrases_total = len(phrases)
    for phrase_obj in phrases:
        if not isinstance(phrase_obj, dict):
            continue
        phrase = phrase_obj.get("phrase")
        if isinstance(phrase, dict):
            # Check kanji, romaji, translation
            kanji = str(phrase.get("kanji", "")).strip()
            romaji = str(phrase.get("romaji", "")).strip()
            translation = str(phrase.get("translation", "")).strip()
            
            if kanji and kanji in text:
                phrases_hit += 1
            elif romaji and romaji.lower() in text_lower:
                phrases_hit += 1
            elif translation and translation.lower() in text_lower:
                phrases_hit += 1
        elif isinstance(phrase, str) and phrase in text:
            phrases_hit += 1
    
    # Compute ratios
    words_ratio = words_hit / words_total if words_total > 0 else 0.0
    grammar_ratio = grammar_hit / grammar_total if grammar_total > 0 else 0.0
    phrases_ratio = phrases_hit / phrases_total if phrases_total > 0 else 0.0
    
    return KitCoverage(
        words_total=words_total,
        words_hit=words_hit,
        words_ratio=words_ratio,
        grammar_total=grammar_total,
        grammar_hit=grammar_hit,
        grammar_ratio=grammar_ratio,
        phrases_total=phrases_total,
        phrases_hit=phrases_hit,
        phrases_ratio=phrases_ratio,
    )


def detect_prompt_leak(text: str) -> List[QualityIssue]:
    """
    Detect prompt instructions or template artifacts leaked into lesson content.
    
    Args:
        text: Flattened lesson text
        
    Returns:
        List of QualityIssue objects
    """
    issues: List[QualityIssue] = []
    
    # Common prompt leak indicators
    leak_patterns = [
        (r"Output JSON schema:", "blocking"),
        (r"Return exactly this structure", "blocking"),
        (r"Authoring rules:", "blocking"),
        (r"Task: Compile a complete", "blocking"),
        (r"\{\{lessonId\}\}", "blocking"),  # Template placeholder
        (r"STRICT JSON SCHEMA", "blocking"),
        (r"Return ONLY JSON", "blocking"),
        (r"JSON shape:", "blocking"),
        (r"min_length", "warning"),  # Schema constraint
        (r"max_length", "warning"),
        (r"Field\(\.\.\.", "warning"),  # Pydantic field syntax
    ]
    
    for pattern, severity in leak_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            issues.append(QualityIssue(
                severity=severity,
                category="prompt_leak",
                message=f"Detected prompt/template artifact: {pattern}",
                details={"pattern": pattern}
            ))
    
    return issues


def detect_topic_mismatch(text: str, meta: Optional[Dict[str, Any]]) -> List[QualityIssue]:
    """
    Detect if lesson content doesn't match the CanDo topic/descriptor.
    
    Generalizes beyond travel-only heuristics to check for generic content.
    
    Args:
        text: Flattened lesson text
        meta: CanDo metadata (primaryTopic, description, type, skillDomain)
        
    Returns:
        List of QualityIssue objects
    """
    issues: List[QualityIssue] = []
    
    if not meta:
        return issues
    
    topic = str(meta.get("primaryTopic", "")).lower()
    description = str(meta.get("description", "")).lower()
    description_en = str(meta.get("descriptionEn", "")).lower()
    description_ja = str(meta.get("descriptionJa", "")).lower()
    skill_domain = str(meta.get("skillDomain", "")).lower()
    can_do_type = str(meta.get("type", "")).lower()
    
    text_lower = text.lower()
    
    # Generic station/travel indicators (only problematic if topic isn't travel)
    generic_travel_indicators = [
        "駅での案内所",
        "道を聞く",
        "乗り換えの説明",
        "駅",
        "切符",
        "改札",
    ]
    
    travel_keywords = ["旅行", "交通", "travel", "transportation", "transport"]
    topic_is_travel = any(kw in topic or kw in description or kw in description_en for kw in travel_keywords)
    
    if not topic_is_travel:
        for indicator in generic_travel_indicators:
            if indicator in text:
                issues.append(QualityIssue(
                    severity="blocking",
                    category="topic_mismatch",
                    message=f"Generic travel/station content detected but topic is not travel-related",
                    details={
                        "indicator": indicator,
                        "topic": topic,
                        "description": description
                    }
                ))
                break  # One issue is enough
    
    # Check if topic keywords appear in text (positive signal)
    topic_words = set()
    if topic:
        topic_words.update(topic.split())
    if description:
        topic_words.update(description.split()[:5])  # First few words
    if description_en:
        topic_words.update(description_en.split()[:5])
    
    # If topic is very specific but none of its keywords appear, that's suspicious
    if topic_words and len(topic_words) > 0:
        topic_found = any(word.lower() in text_lower for word in topic_words if len(word) > 3)
        if not topic_found and len(topic) > 5:
            issues.append(QualityIssue(
                severity="warning",
                category="topic_mismatch",
                message="Topic keywords not found in lesson content",
                details={"topic": topic, "topic_words": list(topic_words)[:5]}
            ))
    
    return issues


def validate_minimum_structure(master: Dict[str, Any]) -> List[QualityIssue]:
    """
    Validate that lesson has minimum required structure.
    
    Args:
        master: Lesson master dict
        
    Returns:
        List of QualityIssue objects
    """
    issues: List[QualityIssue] = []
    
    # Check for UI structure (Stage2 format)
    if "ui" in master:
        ui = master.get("ui", {})
        if not ui.get("sections"):
            issues.append(QualityIssue(
                severity="blocking",
                category="structure",
                message="Lesson missing UI sections",
                details={}
            ))
        else:
            sections = ui.get("sections", [])
            if len(sections) < 2:
                issues.append(QualityIssue(
                    severity="warning",
                    category="structure",
                    message=f"Lesson has only {len(sections)} section(s), expected at least 2",
                    details={"section_count": len(sections)}
                ))
    
    # Check for Stage1 format
    elif "lessonPlan" in master:
        lesson_plan = master.get("lessonPlan", [])
        if len(lesson_plan) < 4:
            issues.append(QualityIssue(
                severity="blocking",
                category="structure",
                message=f"Lesson plan has only {len(lesson_plan)} step(s), expected 4",
                details={"step_count": len(lesson_plan)}
            ))
        
        reading = master.get("reading")
        if not reading:
            issues.append(QualityIssue(
                severity="blocking",
                category="structure",
                message="Lesson missing reading section",
                details={}
            ))
        
        dialogue = master.get("dialogue", [])
        if len(dialogue) < 6:
            issues.append(QualityIssue(
                severity="warning",
                category="structure",
                message=f"Dialogue has only {len(dialogue)} turn(s), expected at least 6",
                details={"turn_count": len(dialogue)}
            ))
        
        grammar = master.get("grammar", [])
        if len(grammar) < 3:
            issues.append(QualityIssue(
                severity="warning",
                category="structure",
                message=f"Grammar section has only {len(grammar)} point(s), expected at least 3",
                details={"grammar_count": len(grammar)}
            ))
    else:
        # Neither format detected
        issues.append(QualityIssue(
            severity="blocking",
            category="structure",
            message="Lesson missing both UI and lessonPlan structure",
            details={}
        ))
    
    return issues


def compute_quality_report(
    master: Dict[str, Any],
    kit: Optional[Dict[str, Any]] = None,
    meta: Optional[Dict[str, Any]] = None,
    quality_mode: QualityMode = QualityMode.WARN,
) -> QualityReport:
    """
    Compute complete quality report for a lesson.
    
    Args:
        master: Lesson master dict
        kit: Optional PreLessonKit dict
        meta: Optional CanDo metadata
        quality_mode: Quality enforcement mode
        
    Returns:
        QualityReport with overall score and issues
    """
    issues: List[QualityIssue] = []
    
    # Flatten text for analysis
    text = flatten_lesson_text(master)
    
    # Check structure
    structure_issues = validate_minimum_structure(master)
    issues.extend(structure_issues)
    
    # Check prompt leaks
    leak_issues = detect_prompt_leak(text)
    issues.extend(leak_issues)
    
    # Check topic alignment
    topic_issues = detect_topic_mismatch(text, meta)
    issues.extend(topic_issues)
    
    # Compute kit coverage
    kit_coverage = None
    if kit:
        kit_coverage = compute_kit_coverage(text, kit)
        
        # Add coverage issues if below thresholds
        if kit_coverage.words_total > 0:
            if kit_coverage.words_ratio < 0.3:  # Less than 30% of words used
                issues.append(QualityIssue(
                    severity="warning" if quality_mode != QualityMode.ENFORCE else "blocking",
                    category="kit_coverage",
                    message=f"Only {kit_coverage.words_hit}/{kit_coverage.words_total} kit words used ({kit_coverage.words_ratio:.1%})",
                    details={"words_hit": kit_coverage.words_hit, "words_total": kit_coverage.words_total}
                ))
        
        if kit_coverage.grammar_total > 0:
            if kit_coverage.grammar_ratio < 0.2:  # Less than 20% of grammar used
                issues.append(QualityIssue(
                    severity="warning" if quality_mode != QualityMode.ENFORCE else "blocking",
                    category="kit_coverage",
                    message=f"Only {kit_coverage.grammar_hit}/{kit_coverage.grammar_total} kit grammar patterns used ({kit_coverage.grammar_ratio:.1%})",
                    details={"grammar_hit": kit_coverage.grammar_hit, "grammar_total": kit_coverage.grammar_total}
                ))
        
        if kit_coverage.phrases_total > 0:
            if kit_coverage.phrases_ratio < 0.2:  # Less than 20% of phrases used
                issues.append(QualityIssue(
                    severity="warning" if quality_mode != QualityMode.ENFORCE else "blocking",
                    category="kit_coverage",
                    message=f"Only {kit_coverage.phrases_hit}/{kit_coverage.phrases_total} kit phrases used ({kit_coverage.phrases_ratio:.1%})",
                    details={"phrases_hit": kit_coverage.phrases_hit, "phrases_total": kit_coverage.phrases_total}
                ))
    
    # Determine blocking issues
    blocking_issues = [i for i in issues if i.severity == "blocking"]
    has_blocking = len(blocking_issues) > 0
    
    # Compute overall score (0-1)
    # Start at 1.0, deduct for issues
    score = 1.0
    for issue in issues:
        if issue.severity == "blocking":
            score -= 0.3
        elif issue.severity == "warning":
            score -= 0.1
        elif issue.severity == "info":
            score -= 0.05
    score = max(0.0, min(1.0, score))
    
    # Adjust score based on kit coverage if available
    if kit_coverage:
        coverage_score = (
            kit_coverage.words_ratio * 0.4 +
            kit_coverage.grammar_ratio * 0.3 +
            kit_coverage.phrases_ratio * 0.3
        )
        score = (score * 0.6 + coverage_score * 0.4)  # Weighted average
    
    # Determine if passed (no blocking issues, or mode is OFF/WARN)
    passed = not has_blocking or quality_mode in (QualityMode.OFF, QualityMode.WARN)
    
    return QualityReport(
        overall_score=score,
        issues=issues,
        kit_coverage=kit_coverage,
        has_blocking_issues=has_blocking,
        passed=passed,
    )

