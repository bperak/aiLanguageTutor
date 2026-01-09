from __future__ import annotations

import asyncio
import json
import os
import importlib.util
import uuid
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, List, Callable
import logging

from neo4j import AsyncSession
from sqlalchemy.ext.asyncio import AsyncSession as PgSession
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, OperationalError

from app.services.cando_image_service import ensure_image_paths_for_lesson


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


logger = logging.getLogger(__name__)


def _load_pipeline_module():
    """Dynamically load canDo_creation_new.py from backend/scripts to avoid duplication."""
    scripts_path = _project_root() / "scripts" / "canDo_creation_new.py"
    spec = importlib.util.spec_from_file_location("cando_pipeline_v2", scripts_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot_load_pipeline_module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[attr-defined]
    return module


def _make_llm_call_openai(model: str, timeout: int = 120):
    """Synchronous OpenAI chat completions adapter used inside server threadpool."""
    from openai import OpenAI

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY_missing")
    # Initialize client with timeout configuration
    import httpx
    timeout_config = httpx.Timeout(timeout, connect=10.0)
    client = OpenAI(
        api_key=api_key,
        timeout=timeout_config,
        max_retries=2,  # Retry transient failures
    )

    def llm_call(system: str, user: str) -> str:
        logger.debug(
            "LLM call START",
            extra={
                "model": model,
                "system_len": len(system),
                "user_len": len(user),
                "timeout": timeout,
            },
        )
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.0,
            response_format={"type": "json_object"},  # Force JSON output mode
        )
        _result = (resp.choices[0].message.content or "").strip()
        logger.debug(
            "LLM call END",
            extra={
                "result_len": len(_result),
                "model": model,
            },
        )
        return _result

    return llm_call


async def _fetch_cando_meta(neo: AsyncSession, can_do_id: str) -> Dict[str, Any]:
    q = (
        "MATCH (c:CanDoDescriptor {uid: $id})\n"
        "RETURN c.uid AS uid, toString(c.level) AS level, toString(c.primaryTopic) AS primaryTopic,\n"
        "coalesce(toString(c.primaryTopicEn), toString(c.primaryTopic)) AS primaryTopicEn,\n"
        "toString(c.skillDomain) AS skillDomain, toString(c.type) AS type,\n"
        "toString(c.descriptionEn) AS descriptionEn, toString(c.descriptionJa) AS descriptionJa,\n"
        "toString(c.titleEn) AS titleEn, toString(c.titleJa) AS titleJa,\n"
        "coalesce(toString(c.source), 'JFまるごと') AS source\n"
        "LIMIT 1"
    )
    result = await neo.run(q, id=can_do_id)
    rec = await result.single()
    if not rec:
        raise ValueError("cando_not_found")
    return dict(rec)


async def _enrich_grammar_neo4j_ids(neo: AsyncSession, lesson: Dict[str, Any]) -> None:
    """Post-process: set neo4j_id on grammar pattern items when exact pattern matches. Do not alter text."""
    try:
        patterns: List[Dict[str, Any]] = (
            (lesson.get("lesson") or {}).get("cards", {}).get("grammar_patterns", {}).get("patterns", [])
        )
        if not isinstance(patterns, list):
            return
        for item in patterns:
            try:
                std = (((item or {}).get("form") or {}).get("ja") or {}).get("std")
                if not std or not isinstance(std, str):
                    continue
                q = (
                    "MATCH (p:GrammarPattern) WHERE toString(p.pattern) = $p "
                    "RETURN p.id AS id LIMIT 2"
                )
                result = [dict(r) async for r in (await neo.run(q, p=std))]
                if len(result) == 1 and result[0].get("id"):
                    item["neo4j_id"] = result[0]["id"]
                # else: leave unmatched or ambiguous per user decision
            except Exception:
                continue
    except Exception:
        pass


async def _build_user_profile_context(
    pg: PgSession,
    user_id: uuid.UUID,
    can_do_id: Optional[str] = None,
    include_full_details: bool = True,
) -> str:
    """
    Build user profile context string for lesson personalization.
    
    Fetches user profile and user data, then formats it into a context string
    that can be included in LLM prompts during lesson generation.
    
    Args:
        pg: PostgreSQL async session
        user_id: User ID to fetch profile for
        can_do_id: Optional CanDo ID for logging context
        include_full_details: If True, includes all profile details (usage context,
            path-level structures, learning preferences). If False, includes only
            basic info (learning goals, previous knowledge).
    
    Returns:
        Formatted profile context string, or empty string if no profile data found.
        Format: "\n\n**User Profile Context (personalize lesson accordingly):**\n- ..."
    
    Example:
        ```python
        context = await _build_user_profile_context(pg, user_id, "JFまるごと:1")
        # Returns formatted string with all profile information
        ```
    """
    try:
        from sqlalchemy import select
        from app.models.database_models import UserProfile, User
        
        user_result = await pg.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        
        profile_result = await pg.execute(select(UserProfile).where(UserProfile.user_id == user_id))
        profile = profile_result.scalar_one_or_none()
        
        if not (profile or user):
            return ""
        
        profile_parts = []
        
        # Learning goals (handle both list and dict formats for backward compatibility)
        learning_goals_raw = profile.learning_goals if profile else (user.learning_goals if user else [])
        if learning_goals_raw:
            if isinstance(learning_goals_raw, dict):
                learning_goals = learning_goals_raw.get("goals", [])
                if learning_goals and len(learning_goals) > 0:
                    goals_text = ', '.join(learning_goals) if isinstance(learning_goals, list) else str(learning_goals)
                    profile_parts.append(f"Learning Goals: {goals_text}")
            elif isinstance(learning_goals_raw, list) and len(learning_goals_raw) > 0:
                goals_text = ', '.join(learning_goals_raw)
                profile_parts.append(f"Learning Goals: {goals_text}")
        
        # Previous knowledge
        if profile and profile.previous_knowledge:
            prev_knowledge = profile.previous_knowledge
            if isinstance(prev_knowledge, dict):
                knowledge_parts = []
                if prev_knowledge.get("languages"):
                    knowledge_parts.append(f"Languages: {prev_knowledge.get('languages')}")
                if prev_knowledge.get("japanese_experience"):
                    knowledge_parts.append(f"Japanese Experience: {prev_knowledge.get('japanese_experience')}")
                if knowledge_parts:
                    profile_parts.append("Previous Knowledge: " + "; ".join(knowledge_parts))
        
        # Full details only if requested
        if include_full_details:
            # Usage context (enhanced with register preferences and scenario details)
            if profile and profile.usage_context:
                usage_ctx = profile.usage_context
                if isinstance(usage_ctx, dict):
                    usage_parts = []
                    if usage_ctx.get("primary_use_case"):
                        usage_parts.append(f"Primary Use: {usage_ctx.get('primary_use_case')}")
                    if usage_ctx.get("frequency"):
                        usage_parts.append(f"Frequency: {usage_ctx.get('frequency')}")
                    if usage_ctx.get("register_preferences"):
                        reg_prefs = usage_ctx.get("register_preferences", [])
                        if isinstance(reg_prefs, list) and len(reg_prefs) > 0:
                            usage_parts.append(f"Register Preferences: {', '.join(reg_prefs)}")
                    if usage_ctx.get("formality_contexts"):
                        formality = usage_ctx.get("formality_contexts", {})
                        if isinstance(formality, dict) and len(formality) > 0:
                            formality_str = ", ".join([f"{k}: {v}" for k, v in formality.items()])
                            usage_parts.append(f"Formality Contexts: {formality_str}")
                    if usage_ctx.get("scenario_details"):
                        scenarios = usage_ctx.get("scenario_details", {})
                        if isinstance(scenarios, dict) and len(scenarios) > 0:
                            scenario_str = ", ".join([f"{k}: {', '.join(v) if isinstance(v, list) else str(v)}" for k, v in scenarios.items()])
                            usage_parts.append(f"Scenario Details: {scenario_str}")
                    if usage_parts:
                        profile_parts.append("Usage Context: " + "; ".join(usage_parts))
            
            # Current level
            if user and user.current_level:
                profile_parts.append(f"Current Level: {user.current_level}")
            
            # Path-level structures (Priority 0: Learning Loop)
            # Note: New fields are stored in learning_goals JSON field for backward compatibility
            if profile and profile.learning_goals:
                learning_goals_data = profile.learning_goals if isinstance(profile.learning_goals, dict) else {}
                if isinstance(learning_goals_data, dict) and len(learning_goals_data) > 0:
                    # Vocabulary domain goals
                    vocab_goals = learning_goals_data.get("vocabulary_domain_goals", [])
                    if vocab_goals and len(vocab_goals) > 0:
                        profile_parts.append(f"Vocabulary Domain Goals: {', '.join(vocab_goals) if isinstance(vocab_goals, list) else str(vocab_goals)}")
                    
                    # Grammar progression goals
                    grammar_goals = learning_goals_data.get("grammar_progression_goals", [])
                    if grammar_goals and len(grammar_goals) > 0:
                        profile_parts.append(f"Grammar Progression Goals: {', '.join(grammar_goals) if isinstance(grammar_goals, list) else str(grammar_goals)}")
                    
                    # Formulaic expression goals
                    expr_goals = learning_goals_data.get("formulaic_expression_goals", [])
                    if expr_goals and len(expr_goals) > 0:
                        profile_parts.append(f"Formulaic Expression Goals: {', '.join(expr_goals) if isinstance(expr_goals, list) else str(expr_goals)}")
                    
                    # Learning targets
                    vocab_target = learning_goals_data.get("vocabulary_learning_target")
                    grammar_target = learning_goals_data.get("grammar_learning_target")
                    expr_target = learning_goals_data.get("expression_learning_target")
                    if vocab_target or grammar_target or expr_target:
                        targets = []
                        if vocab_target:
                            targets.append(f"Vocabulary: {vocab_target} per milestone")
                        if grammar_target:
                            targets.append(f"Grammar: {grammar_target} per milestone")
                        if expr_target:
                            targets.append(f"Expressions: {expr_target} per milestone")
                        if targets:
                            profile_parts.append("Learning Targets: " + "; ".join(targets))
                    
                    # Known inventory (summary)
                    vocab_known = learning_goals_data.get("vocabulary_known", [])
                    grammar_known = learning_goals_data.get("grammar_known", [])
                    expr_known = learning_goals_data.get("expressions_known", [])
                    if vocab_known or grammar_known or expr_known:
                        known_summary = []
                        if vocab_known and len(vocab_known) > 0:
                            known_summary.append(f"Vocabulary Known: {len(vocab_known)} items")
                        if grammar_known and len(grammar_known) > 0:
                            known_summary.append(f"Grammar Known: {len(grammar_known)} patterns")
                        if expr_known and len(expr_known) > 0:
                            known_summary.append(f"Expressions Known: {len(expr_known)} expressions")
                        if known_summary:
                            profile_parts.append("Known Structures: " + "; ".join(known_summary))
                    
                    # Cultural interests
                    cultural_interests = learning_goals_data.get("cultural_interests", [])
                    cultural_background = learning_goals_data.get("cultural_background")
                    if cultural_interests and len(cultural_interests) > 0:
                        profile_parts.append(f"Cultural Interests: {', '.join(cultural_interests) if isinstance(cultural_interests, list) else str(cultural_interests)}")
                    if cultural_background:
                        profile_parts.append(f"Cultural Background: {cultural_background}")
            
            # Learning preferences (4-stage personalization)
            if profile and profile.learning_experiences:
                learning_exp = profile.learning_experiences
                if isinstance(learning_exp, dict):
                    pref_parts = []
                    if learning_exp.get("grammar_focus_areas"):
                        focus = learning_exp.get("grammar_focus_areas", [])
                        if isinstance(focus, list) and len(focus) > 0:
                            pref_parts.append(f"Grammar Focus: {', '.join(focus)}")
                    if learning_exp.get("preferred_exercise_types"):
                        exercises = learning_exp.get("preferred_exercise_types", {})
                        if isinstance(exercises, dict) and len(exercises) > 0:
                            exercise_str = ", ".join([f"{k}: {', '.join(v) if isinstance(v, list) else str(v)}" for k, v in exercises.items()])
                            pref_parts.append(f"Exercise Preferences: {exercise_str}")
                    if learning_exp.get("interaction_preferences"):
                        interaction = learning_exp.get("interaction_preferences", {})
                        if isinstance(interaction, dict) and len(interaction) > 0:
                            interaction_str = ", ".join([f"{k}: {v}" for k, v in interaction.items()])
                            pref_parts.append(f"Interaction Preferences: {interaction_str}")
                    if pref_parts:
                        profile_parts.append("Learning Preferences: " + "; ".join(pref_parts))
        
        if profile_parts:
            profile_context = "\n\n**User Profile Context (personalize lesson accordingly):**\n" + "\n".join(f"- {part}" for part in profile_parts)
            if can_do_id:
                logger.info("profile_context_fetched", extra={"can_do_id": can_do_id, "user_id": str(user_id), "has_context": True})
            return profile_context
        
        return ""
    except Exception as e:
        if can_do_id:
            logger.warning(
                "profile_context_fetch_failed",
                extra={"can_do_id": can_do_id, "user_id": str(user_id), "error": str(e)}
            )
        else:
            logger.warning("profile_context_fetch_failed", extra={"user_id": str(user_id), "error": str(e)})
        return ""


def _hash_profile_context(profile_context: str) -> str:
    """
    Generate hash for profile context to use as cache key.
    
    Args:
        profile_context: Profile context string
        
    Returns:
        First 16 characters of SHA256 hash
    """
    import hashlib
    return hashlib.sha256(profile_context.encode()).hexdigest()[:16]


def _hash_kit_context(kit_context: str, kit_requirements: str) -> str:
    """
    Generate hash for kit context to use as cache key.
    
    Args:
        kit_context: Kit context string
        kit_requirements: Kit requirements string
        
    Returns:
        First 16 characters of SHA256 hash
    """
    import hashlib
    combined = f"{kit_context}|{kit_requirements}"
    return hashlib.sha256(combined.encode()).hexdigest()[:16]


async def _get_cached_plan(
    pg: PgSession,
    can_do_id: str,
    profile_context_hash: str,
    kit_context_hash: str,
) -> Optional[Dict[str, Any]]:
    """
    Check if plan exists in cache and is not expired.
    
    Args:
        pg: PostgreSQL async session
        can_do_id: CanDo descriptor ID
        profile_context_hash: Hash of profile context
        kit_context_hash: Hash of kit context
        
    Returns:
        Cached plan JSON dict if found and not expired, None otherwise
    """
    try:
        from sqlalchemy import text
        result = await pg.execute(
            text("""
                SELECT plan_json, id
                FROM plan_cache
                WHERE can_do_id = :can_do_id
                  AND profile_hash = :profile_hash
                  AND kit_hash = :kit_hash
                  AND expires_at > NOW()
                LIMIT 1
            """),
            {
                "can_do_id": can_do_id,
                "profile_hash": profile_context_hash,
                "kit_hash": kit_context_hash,
            }
        )
        row = result.first()
        if row:
            # Update hit count and last_used_at
            await pg.execute(
                text("""
                    UPDATE plan_cache
                    SET hits = hits + 1,
                        last_used_at = NOW()
                    WHERE id = :id
                """),
                {"id": row[1]}
            )
            await pg.commit()
            logger.info("plan_cache_hit", extra={"can_do_id": can_do_id})
            return row[0] if isinstance(row[0], dict) else json.loads(row[0]) if isinstance(row[0], str) else None
        return None
    except Exception as e:
        # If table doesn't exist or other error, log and return None
        logger.debug("plan_cache_lookup_failed", extra={"can_do_id": can_do_id, "error": str(e)})
        return None


async def _cache_plan(
    pg: PgSession,
    can_do_id: str,
    profile_context_hash: str,
    kit_context_hash: str,
    plan: Any,  # DomainPlan object
    ttl_hours: int = 24,
) -> None:
    """
    Cache generated plan in database.
    
    Args:
        pg: PostgreSQL async session
        can_do_id: CanDo descriptor ID
        profile_context_hash: Hash of profile context
        kit_context_hash: Hash of kit context
        plan: DomainPlan object to cache
        ttl_hours: Time to live in hours (default: 24)
    """
    try:
        from sqlalchemy import text
        from datetime import datetime, timedelta
        
        # Convert DomainPlan to JSON
        plan_json = plan.model_dump(mode='json') if hasattr(plan, 'model_dump') else plan
        
        expires_at = datetime.utcnow() + timedelta(hours=ttl_hours)
        
        # Use transaction for atomic cache update
        async with pg.begin():
            await pg.execute(
                text("""
                    INSERT INTO plan_cache (can_do_id, profile_hash, kit_hash, plan_json, expires_at)
                    VALUES (:can_do_id, :profile_hash, :kit_hash, :plan_json::jsonb, :expires_at)
                    ON CONFLICT (can_do_id, profile_hash, kit_hash)
                    DO UPDATE SET
                        plan_json = EXCLUDED.plan_json,
                        expires_at = EXCLUDED.expires_at,
                        created_at = NOW(),
                        hits = 0,
                        last_used_at = NOW()
                """),
                {
                    "can_do_id": can_do_id,
                    "profile_hash": profile_context_hash,
                    "kit_hash": kit_context_hash,
                    "plan_json": json.dumps(plan_json, ensure_ascii=False),
                    "expires_at": expires_at,
                }
            )
        logger.info("plan_cached", extra={"can_do_id": can_do_id, "ttl_hours": ttl_hours})
    except OperationalError as e:
        # Database connection/operation error
        logger.warning("plan_cache_store_operational_error", extra={"can_do_id": can_do_id, "error": str(e)})
    except IntegrityError as e:
        # Data integrity error
        logger.warning("plan_cache_store_integrity_error", extra={"can_do_id": can_do_id, "error": str(e)})
    except SQLAlchemyError as e:
        # Other database errors
        logger.debug("plan_cache_store_failed", extra={"can_do_id": can_do_id, "error": str(e)})
    except Exception as e:
        # If table doesn't exist or other error, log and continue
        logger.debug("plan_cache_store_failed", extra={"can_do_id": can_do_id, "error": str(e)})


def _validate_plan_quality(plan: Any) -> List[str]:
    """
    Validate plan quality beyond schema validation.
    
    Args:
        plan: DomainPlan object
        
    Returns:
        List of quality issues (empty if plan is good)
    """
    issues = []
    
    # Check scenario count
    if not hasattr(plan, 'scenarios') or len(plan.scenarios) < 1:
        issues.append("Too few scenarios (minimum 1 required)")
    elif len(plan.scenarios) > 2:
        issues.append(f"Too many scenarios ({len(plan.scenarios)}, expected 1-2)")
    
    # Check vocabulary coverage
    if hasattr(plan, 'lex_buckets'):
        total_vocab = sum(len(bucket.items) if hasattr(bucket, 'items') else 0 for bucket in plan.lex_buckets)
        if total_vocab < 20:
            issues.append(f"Insufficient vocabulary ({total_vocab} items, minimum 20 recommended)")
        elif total_vocab > 100:
            issues.append(f"Excessive vocabulary ({total_vocab} items, may be overwhelming)")
    
    # Check grammar functions
    if hasattr(plan, 'grammar_functions'):
        if len(plan.grammar_functions) < 2:
            issues.append("Too few grammar functions (minimum 2 required)")
        elif len(plan.grammar_functions) > 5:
            issues.append(f"Too many grammar functions ({len(plan.grammar_functions)}, expected 2-5)")
    
    # Check evaluation criteria
    if hasattr(plan, 'evaluation'):
        if hasattr(plan.evaluation, 'success_criteria'):
            if len(plan.evaluation.success_criteria) < 2:
                issues.append("Too few success criteria (minimum 2 required)")
            elif len(plan.evaluation.success_criteria) > 5:
                issues.append(f"Too many success criteria ({len(plan.evaluation.success_criteria)}, expected 2-5)")
    
    # Check cultural themes
    if hasattr(plan, 'cultural_themes_en'):
        if len(plan.cultural_themes_en) < 2:
            issues.append("Too few cultural themes (minimum 2 required)")
        elif len(plan.cultural_themes_en) > 5:
            issues.append(f"Too many cultural themes ({len(plan.cultural_themes_en)}, expected 2-5)")
    
    return issues


async def _fetch_prelesson_kit_from_path(
    pg: PgSession,
    can_do_id: str,
    user_id: Optional[uuid.UUID] = None
) -> Optional[Dict[str, Any]]:
    """
    Fetch pre-lesson kit from learning path for a given CanDo.
    
    This function searches for a pre-lesson kit associated with a CanDo descriptor
    in the learning paths. If a user_id is provided, it searches the user's active
    learning path first. Otherwise, it searches all active learning paths.
    
    Args:
        pg: PostgreSQL async session for database queries
        can_do_id: CanDo descriptor ID (e.g., "JFまるごと:1")
        user_id: Optional user ID to fetch from specific user's active learning path.
                If None, searches all active learning paths (fallback behavior)
        
    Returns:
        Pre-lesson kit dictionary with structure:
        {
            "can_do_context": {
                "situation": str,
                "pragmatic_act": str,
                "notes": Optional[str]
            },
            "necessary_words": List[Dict[str, Any]],
            "necessary_grammar_patterns": List[Dict[str, Any]],
            "necessary_fixed_phrases": List[Dict[str, Any]]
        }
        Returns None if kit not found or on error.
    
    Example:
        ```python
        kit = await _fetch_prelesson_kit_from_path(pg, "JFまるごと:1", user_id)
        if kit:
            # Use kit for compilation
            context, requirements = _build_prelesson_kit_context(kit)
        ```
    
    Note:
        Errors during fetching are logged as warnings and do not raise exceptions.
        This allows compilation to continue even if kit fetching fails.
    """
    try:
        from sqlalchemy import select
        from app.models.database_models import LearningPath
        
        # If user_id provided, fetch from that user's active path
        if user_id:
            result = await pg.execute(
                select(LearningPath)
                .where(
                    (LearningPath.user_id == user_id) &
                    (LearningPath.is_active == True)
                )
                .order_by(LearningPath.version.desc())
                .limit(1)
            )
            path = result.scalar_one_or_none()
            if path and path.path_data:
                steps = path.path_data.get("steps", [])
                for step in steps:
                    if step.get("can_do_id") == can_do_id:
                        return step.get("prelesson_kit")
        
        # Otherwise, try to find in any active path (fallback)
        result = await pg.execute(
            select(LearningPath)
            .where(LearningPath.is_active == True)
            .order_by(LearningPath.version.desc())
        )
        paths = result.scalars().all()
        for path in paths:
            if path.path_data:
                steps = path.path_data.get("steps", [])
                for step in steps:
                    if step.get("can_do_id") == can_do_id:
                        kit = step.get("prelesson_kit")
                        if kit:
                            return kit
        
        return None
    except Exception as e:
        logger.warning("failed_to_fetch_prelesson_kit", can_do_id=can_do_id, error=str(e))
        return None


def _build_prelesson_kit_context(prelesson_kit: Dict[str, Any]) -> Tuple[str, str]:
    """
    Build pre-lesson kit context string and requirements for card generation.
    
    Converts a pre-lesson kit dictionary into formatted context strings that are
    included in LLM prompts during card generation. The context includes:
    - CanDo context (situation, pragmatic act, notes)
    - Essential words list
    - Grammar patterns list
    - Fixed phrases list
    
    Also calculates mandatory usage requirements:
    - Words: At least 30% (minimum 6) must be used
    - Grammar: At least 20% (minimum 2) must be used
    - Phrases: At least 20% (minimum 2) must be used
    
    Args:
        prelesson_kit: Pre-lesson kit dictionary with structure:
            {
                "can_do_context": {
                    "situation": str,
                    "pragmatic_act": str,
                    "notes": Optional[str]
                },
                "necessary_words": List[Dict[str, Any]],  # Each with "surface", "reading", etc.
                "necessary_grammar_patterns": List[Dict[str, Any]],  # Each with "pattern", "explanation"
                "necessary_fixed_phrases": List[Dict[str, Any]]  # Each with "phrase" (dict or str), "usage_note"
            }
    
    Returns:
        Tuple of (kit_context, kit_requirements) where:
        - kit_context: Formatted string describing kit components for LLM prompts
        - kit_requirements: Formatted string with mandatory usage requirements
    
    Example:
        ```python
        kit = {
            "can_do_context": {"situation": "At a restaurant", "pragmatic_act": "order"},
            "necessary_words": [{"surface": "レストラン", "reading": "れすとらん"}],
            "necessary_grammar_patterns": [{"pattern": "〜をください"}],
            "necessary_fixed_phrases": [{"phrase": {"kanji": "いらっしゃいませ"}}]
        }
        context, requirements = _build_prelesson_kit_context(kit)
        # context contains formatted kit information
        # requirements contains mandatory usage instructions
        ```
    
    Note:
        Handles missing or None components gracefully. If a component is missing,
        it is simply omitted from the context string.
    """
    kit_context = "\n\n**Pre-Lesson Kit Context (REQUIRED - use these in your lesson):**\n"
    kit_requirements = ""
    
    # Component (0): CanDo context
    can_do_ctx = prelesson_kit.get("can_do_context")
    if can_do_ctx:
        kit_context += f"- Situation: {can_do_ctx.get('situation', '')}\n"
        kit_context += f"- Pragmatic Act: {can_do_ctx.get('pragmatic_act', '')}\n"
        if can_do_ctx.get('notes'):
            kit_context += f"- Notes: {can_do_ctx.get('notes')}\n"
    
    # Component (1): Words
    words = prelesson_kit.get("necessary_words", [])
    if words:
        word_list = [w.get("surface", "") for w in words]
        kit_context += f"- Essential Words ({len(words)}): {', '.join(word_list)}\n"
        # Minimum usage requirement
        min_words = max(6, int(len(words) * 0.3))  # At least 30% or 6 words, whichever is higher
        kit_requirements += f"\n- **MANDATORY:** Use at least {min_words} of the {len(words)} kit words across reading, dialogue, and practice sections.\n"
    
    # Component (2): Grammar patterns
    grammar = prelesson_kit.get("necessary_grammar_patterns", [])
    if grammar:
        grammar_list = [g.get("pattern", "") for g in grammar]
        kit_context += f"- Grammar Patterns ({len(grammar)}): {', '.join(grammar_list)}\n"
        # Minimum usage requirement
        min_grammar = max(2, int(len(grammar) * 0.2))  # At least 20% or 2 patterns
        kit_requirements += f"- **MANDATORY:** Use at least {min_grammar} of the {len(grammar)} kit grammar patterns in examples and dialogue.\n"
    
    # Component (3): Fixed phrases
    phrases = prelesson_kit.get("necessary_fixed_phrases", [])
    if phrases:
        phrase_texts = []
        for p in phrases:
            phrase_obj = p.get("phrase", {})
            if isinstance(phrase_obj, dict):
                phrase_texts.append(phrase_obj.get("kanji", "") or phrase_obj.get("romaji", ""))
            elif isinstance(phrase_obj, str):
                phrase_texts.append(phrase_obj)
        kit_context += f"- Fixed Phrases ({len(phrases)}): {', '.join(phrase_texts)}\n"
        # Minimum usage requirement
        min_phrases = max(2, int(len(phrases) * 0.2))  # At least 20% or 2 phrases
        kit_requirements += f"- **MANDATORY:** Use at least {min_phrases} of the {len(phrases)} kit phrases naturally in dialogue and examples.\n"
    
    kit_context += "\n**CRITICAL:** Your lesson content MUST demonstrate use of these kit components. They are not optional suggestions."
    
    return kit_context, kit_requirements


def _extract_text_from_lesson(lesson_json: Dict[str, Any]) -> str:
    """
    Extract all Japanese text from a lesson for kit usage analysis.
    
    Scans through all lesson cards (dialogue, reading, words, grammar) and
    extracts Japanese text content for analysis. Used to determine which
    kit elements appear in the compiled lesson.
    
    Args:
        lesson_json: Complete lesson JSON structure
    
    Returns:
        Combined string of all Japanese text found in the lesson
    """
    text_parts = []
    
    cards = lesson_json.get("lesson", {}).get("cards", {})
    
    # Extract from dialogue
    dialogue = cards.get("lesson_dialogue", {})
    if dialogue:
        turns = dialogue.get("turns", [])
        for turn in turns:
            jp = turn.get("japanese", {})
            if isinstance(jp, dict):
                text_parts.append(jp.get("kanji", "") or jp.get("std", "") or jp.get("romaji", ""))
            elif isinstance(jp, str):
                text_parts.append(jp)
    
    # Extract from reading
    reading = cards.get("reading_comprehension", {})
    if reading:
        reading_content = reading.get("reading", {})
        if reading_content:
            content = reading_content.get("content", {})
            if isinstance(content, dict):
                text_parts.append(content.get("kanji", "") or content.get("std", "") or content.get("romaji", ""))
            elif isinstance(content, str):
                text_parts.append(content)
    
    # Extract from words
    words = cards.get("words", {})
    if words:
        # Handle both dict and Pydantic model
        if hasattr(words, "items"):
            items = words.items if isinstance(words.items, list) else []
        elif isinstance(words, dict):
            items = words.get("items", [])
        else:
            items = []
        for item in items:
            # Handle both dict and Pydantic model
            if hasattr(item, "jp"):
                jp = item.jp
            elif isinstance(item, dict):
                jp = item.get("jp", {})
            else:
                jp = {}
            if isinstance(jp, dict):
                text_parts.append(jp.get("kanji", "") or jp.get("std", "") or jp.get("romaji", ""))
            elif isinstance(jp, str):
                text_parts.append(jp)
    
    # Extract from grammar examples
    grammar = cards.get("grammar_patterns", {})
    if grammar:
        # Handle both dict and Pydantic model
        if hasattr(grammar, "patterns"):
            patterns = grammar.patterns if isinstance(grammar.patterns, list) else []
        elif isinstance(grammar, dict):
            patterns = grammar.get("patterns", [])
        else:
            patterns = []
        for pattern in patterns:
            # Handle both dict and Pydantic model
            if hasattr(pattern, "examples"):
                examples = pattern.examples if isinstance(pattern.examples, list) else []
            elif isinstance(pattern, dict):
                examples = pattern.get("examples", [])
            else:
                examples = []
            for example in examples:
                # Handle both dict and Pydantic model
                if hasattr(example, "jp"):
                    jp = example.jp
                elif isinstance(example, dict):
                    jp = example.get("jp", {})
                else:
                    jp = {}
                if isinstance(jp, dict):
                    text_parts.append(jp.get("kanji", "") or jp.get("std", "") or jp.get("romaji", ""))
                elif isinstance(jp, str):
                    text_parts.append(jp)
    
    return " ".join(text_parts)


def _count_kit_word_usage(lesson_text: str, kit_words: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Count how many kit words appear in lesson text and which ones.
    
    Args:
        lesson_text: Combined Japanese text from lesson
        kit_words: List of kit word dictionaries with "surface" field
    
    Returns:
        Dictionary with:
        - "used": List of word surfaces that were found
        - "count": Number of kit words found
        - "total": Total number of kit words
    """
    used_words = []
    word_surfaces = [w.get("surface", "") for w in kit_words if w.get("surface")]
    
    for word in word_surfaces:
        if word and word in lesson_text:
            used_words.append(word)
    
    return {
        "used": used_words,
        "count": len(used_words),
        "total": len(kit_words),
    }


def _count_kit_grammar_usage(lesson_text: str, kit_grammar: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Count how many kit grammar patterns appear in lesson text and which ones.
    
    Args:
        lesson_text: Combined Japanese text from lesson
        kit_grammar: List of kit grammar dictionaries with "pattern" field
    
    Returns:
        Dictionary with:
        - "used": List of patterns that were found
        - "count": Number of kit patterns found
        - "total": Total number of kit patterns
    """
    used_patterns = []
    grammar_patterns = [g.get("pattern", "") for g in kit_grammar if g.get("pattern")]
    
    for pattern in grammar_patterns:
        if pattern and pattern in lesson_text:
            used_patterns.append(pattern)
    
    return {
        "used": used_patterns,
        "count": len(used_patterns),
        "total": len(kit_grammar),
    }


def _count_kit_phrase_usage(lesson_text: str, kit_phrases: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Count how many kit phrases appear in lesson text and which ones.
    
    Args:
        lesson_text: Combined Japanese text from lesson
        kit_phrases: List of kit phrase dictionaries with "phrase" field
                    (can be dict with "kanji"/"romaji" or string)
    
    Returns:
        Dictionary with:
        - "used": List of phrase texts that were found
        - "count": Number of kit phrases found
        - "total": Total number of kit phrases
    """
    used_phrases = []
    
    for phrase_data in kit_phrases:
        phrase_obj = phrase_data.get("phrase", {})
        if isinstance(phrase_obj, dict):
            phrase_text = phrase_obj.get("kanji", "") or phrase_obj.get("romaji", "")
        elif isinstance(phrase_obj, str):
            phrase_text = phrase_obj
        else:
            continue
        
        if phrase_text and phrase_text in lesson_text:
            used_phrases.append(phrase_text)
    
    return {
        "used": used_phrases,
        "count": len(used_phrases),
        "total": len(kit_phrases),
    }


def _track_kit_usage(lesson_json: Dict[str, Any], kit: Dict[str, Any]) -> Dict[str, Any]:
    """
    Track pre-lesson kit usage in compiled lesson.
    
    Analyzes the compiled lesson to determine which kit elements (words, grammar,
    phrases) were actually used and whether mandatory requirements were met.
    
    Args:
        lesson_json: Complete compiled lesson JSON structure
        kit: Pre-lesson kit dictionary
    
    Returns:
        Dictionary with comprehensive usage statistics:
        {
            "words": {
                "used": List[str],  # Word surfaces that were found
                "count": int,        # Number of kit words used
                "total": int,        # Total kit words available
                "required": int,     # Minimum required (30% or 6)
                "meets_requirement": bool
            },
            "grammar": {
                "used": List[str],  # Patterns that were found
                "count": int,
                "total": int,
                "required": int,     # Minimum required (20% or 2)
                "meets_requirement": bool
            },
            "phrases": {
                "used": List[str],  # Phrase texts that were found
                "count": int,
                "total": int,
                "required": int,     # Minimum required (20% or 2)
                "meets_requirement": bool
            },
            "all_requirements_met": bool,  # True if all requirements met
            "usage_percentage": float       # Overall percentage (0-100)
        }
    
    Note:
        This function performs simple string matching to find kit elements.
        More sophisticated NLP-based matching could be added in the future.
    """
    lesson_text = _extract_text_from_lesson(lesson_json)
    
    kit_words = kit.get("necessary_words", [])
    kit_grammar = kit.get("necessary_grammar_patterns", [])
    kit_phrases = kit.get("necessary_fixed_phrases", [])
    
    # Calculate requirements
    min_words = max(6, int(len(kit_words) * 0.3)) if kit_words else 0
    min_grammar = max(2, int(len(kit_grammar) * 0.2)) if kit_grammar else 0
    min_phrases = max(2, int(len(kit_phrases) * 0.2)) if kit_phrases else 0
    
    # Count usage
    words_result = _count_kit_word_usage(lesson_text, kit_words)
    grammar_result = _count_kit_grammar_usage(lesson_text, kit_grammar)
    phrases_result = _count_kit_phrase_usage(lesson_text, kit_phrases)
    
    # Check requirements
    words_meets = words_result["count"] >= min_words if min_words > 0 else True
    grammar_meets = grammar_result["count"] >= min_grammar if min_grammar > 0 else True
    phrases_meets = phrases_result["count"] >= min_phrases if min_phrases > 0 else True
    
    # Calculate overall usage percentage
    total_elements = len(kit_words) + len(kit_grammar) + len(kit_phrases)
    used_elements = words_result["count"] + grammar_result["count"] + phrases_result["count"]
    usage_percentage = (used_elements / total_elements * 100) if total_elements > 0 else 0.0
    
    return {
        "words": {
            **words_result,
            "required": min_words,
            "meets_requirement": words_meets,
        },
        "grammar": {
            **grammar_result,
            "required": min_grammar,
            "meets_requirement": grammar_meets,
        },
        "phrases": {
            **phrases_result,
            "required": min_phrases,
            "meets_requirement": phrases_meets,
        },
        "all_requirements_met": words_meets and grammar_meets and phrases_meets,
        "usage_percentage": round(usage_percentage, 2),
    }


async def _compile_content_stage_only(
    *,
    neo: AsyncSession,
    pg: PgSession,
    can_do_id: str,
    metalanguage: str,
    model: str,
    timeout: int,
    prelesson_kit: Optional[Dict[str, Any]],
    user_id: Optional[uuid.UUID],
    fast_model_override: Optional[str],
    progress_callback: Optional[Callable[[Dict[str, Any]], None]],
    cando_input: Dict[str, Any],
    plan: Any,
    llm_call_main: Callable,
    llm_call_fast: Callable,
    kit_context: str,
    kit_requirements: str,
    profile_context: str,
) -> Tuple[Dict[str, Any], int, int, Dict[str, Any]]:
    """
    Generate and save only the Content stage of a lesson.
    
    Returns:
        Tuple of (lesson_json, lesson_id, version, content_cards_dict)
    """
    import time
    import json
    from sqlalchemy import text
    pipeline = _load_pipeline_module()
    
    # Generate Content stage only
    if progress_callback:
        progress_callback({"stage": "content", "progress": 15, "message": "Generating Content stage...", "substep": "planning"})
    
    logger.info("Generating Content stage", extra={"can_do_id": can_do_id, "stage": "content"})
    content_start = time.time()
    print(f"[COMPILE] {can_do_id}: Starting Content stage generation at {time.strftime('%H:%M:%S')}")
    
    # Create a progress callback wrapper for content stage
    def content_progress_callback(card_name: str, progress_pct: int):
        """Helper to send progress updates for individual content cards"""
        if progress_callback:
            base_progress = 15  # Start after plan
            card_progress = int(base_progress + (progress_pct * 0.15))  # Content stage is ~15% of total
            progress_callback({
                "stage": "content",
                "progress": card_progress,
                "message": f"Generating {card_name}...",
                "substep": card_name.lower().replace(" ", "_")
            })
    
    content_cards = await pipeline.gen_content_stage(
        llm_call_main,
        llm_call_fast,
        metalanguage,
        cando_input,
        plan,
        max_repair=2,
        kit_context=kit_context,
        profile_context=profile_context,
        kit_requirements=kit_requirements,
        progress_callback=content_progress_callback,  # Pass progress callback
    )
    
    content_duration = time.time() - content_start
    print(f"[COMPILE] {can_do_id}: Content stage generated in {content_duration:.1f}s")
    logger.info("Content stage generated", extra={"can_do_id": can_do_id, "stage": "content", "duration": content_duration})
    
    if progress_callback:
        progress_callback({"stage": "content", "progress": 30, "message": "Content stage complete!", "substep": "complete"})
    
    # Assemble partial lesson with Content stage only
    if progress_callback:
        progress_callback({"step": "finalizing", "progress": 50, "message": "Assembling lesson..."})
    
    root = pipeline.assemble_lesson(
        metalanguage,
        cando_input,
        plan,
        content_cards["objective"],
        content_cards["words"],
        content_cards["grammar_patterns"],
        content_cards["lesson_dialogue"],
        reading=None,  # Not generated yet
        guided=None,  # Not generated yet
        exercises=None,
        culture=content_cards["cultural_explanation"],
        drills=None,
        formulaic_expressions=content_cards.get("formulaic_expressions"),
        comprehension_exercises=None,  # Not generated yet
        ai_comprehension_tutor=None,  # Not generated yet
        production_exercises=None,  # Not generated yet
        ai_production_evaluator=None,  # Not generated yet
        interactive_dialogue=None,  # Not generated yet
        interaction_activities=None,  # Not generated yet
        ai_scenario_manager=None,  # Not generated yet
        lesson_id=f"canDo_{can_do_id}_v1",
    )
    
    # Convert to dict
    lesson_json = root.model_dump(mode='json')
    
    # Add generation status metadata
    if "lesson" not in lesson_json:
        lesson_json["lesson"] = {}
    if "meta" not in lesson_json["lesson"]:
        lesson_json["lesson"]["meta"] = {}
    lesson_json["lesson"]["meta"]["generation_status"] = {
        "content": "complete",
        "comprehension": "pending",
        "production": "pending",
        "interaction": "pending",
    }
    
    # Enrich grammar with Neo4j IDs
    await _enrich_grammar_neo4j_ids(neo, lesson_json)
    
    # Track pre-lesson kit usage if kit was provided
    kit_usage_report = None
    if prelesson_kit:
        try:
            kit_usage_report = _track_kit_usage(lesson_json, prelesson_kit)
        except Exception as e:
            logger.warning("prelesson_kit_usage_tracking_failed", extra={"can_do_id": can_do_id, "error": str(e)})
    
    # Persist in lessons/lesson_versions tables
    result = await pg.execute(text("SELECT id FROM lessons WHERE can_do_id = :cid LIMIT 1"), {"cid": can_do_id})
    row = result.first()
    if row:
        lesson_id = int(row[0])
    else:
        ins = await pg.execute(text("INSERT INTO lessons (can_do_id, status) VALUES (:cid, 'draft') RETURNING id"), {"cid": can_do_id})
        lesson_id = int(ins.first()[0])
    
    ver_row = (await pg.execute(text("SELECT COALESCE(MAX(version),0) FROM lesson_versions WHERE lesson_id=:lid"), {"lid": lesson_id})).first()
    next_ver = int(ver_row[0]) + 1
    
    # Store pre-lesson kit usage in lesson metadata if available
    if kit_usage_report and isinstance(lesson_json, dict) and "lesson" in lesson_json:
        if "meta" not in lesson_json["lesson"]:
            lesson_json["lesson"]["meta"] = {}
        lesson_json["lesson"]["meta"]["prelesson_kit_usage"] = kit_usage_report
        lesson_json["lesson"]["meta"]["prelesson_kit_available"] = True
    
    await pg.execute(
        text("INSERT INTO lesson_versions (lesson_id, version, lesson_plan) VALUES (:lid, :ver, :plan)"),
        {"lid": lesson_id, "ver": next_ver, "plan": json.dumps(lesson_json, ensure_ascii=False)},
    )
    await pg.commit()
    
    logger.info("Content stage saved", extra={"can_do_id": can_do_id, "lesson_id": lesson_id, "version": next_ver})
    
    # Extract content_cards dict for background task
    content_cards_dict = {
        "objective": content_cards["objective"],
        "words": content_cards["words"],
        "grammar_patterns": content_cards["grammar_patterns"],
        "formulaic_expressions": content_cards.get("formulaic_expressions"),
        "lesson_dialogue": content_cards["lesson_dialogue"],
        "cultural_explanation": content_cards["cultural_explanation"],
    }
    
    return lesson_json, lesson_id, next_ver, content_cards_dict


def _is_retryable_error(error: Exception) -> bool:
    """
    Determine if an error is retryable (transient) or permanent.
    
    Retryable errors: timeouts, rate limits, network issues, temporary API errors
    Permanent errors: validation errors, invalid input, authentication failures
    """
    error_str = str(error).lower()
    error_type = type(error).__name__
    
    # Retryable error patterns
    retryable_patterns = [
        "timeout", "timed out", "rate limit", "too many requests",
        "connection", "network", "temporary", "service unavailable",
        "internal server error", "bad gateway", "gateway timeout"
    ]
    
    # Permanent error patterns
    permanent_patterns = [
        "validation", "invalid", "authentication", "authorization",
        "not found", "forbidden", "bad request"
    ]
    
    # Check error type
    retryable_types = ["TimeoutError", "ConnectionError", "HTTPError"]
    permanent_types = ["ValueError", "KeyError", "AttributeError"]
    
    if any(pattern in error_str for pattern in retryable_patterns):
        return True
    if any(pattern in error_str for pattern in permanent_patterns):
        return False
    if error_type in retryable_types:
        return True
    if error_type in permanent_types:
        return False
    
    # Default: assume retryable for unknown errors (safer to retry)
    return True


async def _generate_remaining_stages_background(
    *,
    neo: AsyncSession,
    pg: PgSession,
    can_do_id: str,
    lesson_id: int,
    version: int,
    metalanguage: str,
    model: str,
    timeout: int,
    prelesson_kit: Optional[Dict[str, Any]],
    fast_model_override: Optional[str],
    cando_input: Dict[str, Any],
    plan: Any,
    content_cards: Dict[str, Any],
    llm_call_main: Callable,
    llm_call_fast: Callable,
    kit_context: str,
    kit_requirements: str,
    profile_context: str,
    progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> None:
    """
    Generate remaining stages (Comprehension, Production, Interaction) in background and update lesson incrementally.
    """
    import time
    import sys
    pipeline = _load_pipeline_module()
    
    try:
        # STAGE 2: COMPREHENSION
        if progress_callback:
            progress_callback({"stage": "comprehension", "progress": 60, "message": "Generating Comprehension stage..."})
        
        logger.info("Generating Comprehension stage (background)", extra={"can_do_id": can_do_id, "stage": "comprehension"})
        comprehension_start = time.time()
        print(f"[COMPILE] {can_do_id}: Starting Comprehension stage generation (background) at {time.strftime('%H:%M:%S')}")
        
        # Generate reading first (needs dialogue)
        reading = await asyncio.to_thread(
            pipeline.gen_reading_card,
            llm_call_fast,
            metalanguage,
            cando_input,
            plan,
            content_cards["lesson_dialogue"],
            max_repair=0,
            kit_context=kit_context,
        profile_context=profile_context,
            kit_requirements=kit_requirements,
        )
        
        # Generate comprehension exercises and AI tutor in parallel
        comprehension_cards = await pipeline.gen_comprehension_stage(
            llm_call_main,
            llm_call_fast,
            metalanguage,
            plan,
            content_cards,
            reading=reading,
            max_repair=0,
            kit_context=kit_context,
        profile_context=profile_context,
            kit_requirements=kit_requirements,
        )
        
        comprehension_duration = time.time() - comprehension_start
        print(f"[COMPILE] {can_do_id}: Comprehension stage generated in {comprehension_duration:.1f}s")
        logger.info("Comprehension stage generated (background)", extra={"can_do_id": can_do_id, "stage": "comprehension", "duration": comprehension_duration})
        
        # Update lesson in database
        await _update_lesson_stage_in_db(pg, lesson_id, version, "comprehension", comprehension_cards)
        if progress_callback:
            progress_callback({"stage": "comprehension", "progress": 70, "message": "Comprehension stage complete", "event": "comprehension_ready"})
        
    except Exception as e:
        import traceback
        error_type = type(e).__name__
        error_message = str(e)
        error_traceback = traceback.format_exc()
        is_retryable = _is_retryable_error(e)
        
        # Log full error details including traceback
        print(f"[ERROR] Comprehension stage failed for {can_do_id}: {error_type}: {error_message}")
        print(f"[ERROR] Traceback:\n{error_traceback}")
        
        logger.error(
            "comprehension_stage_generation_failed",
            extra={
                "can_do_id": can_do_id,
                "error": error_message,
                "error_type": error_type,
                "retryable": is_retryable,
                "traceback": error_traceback
            }
        )
        
        # Try retry if it's a retryable error
        if is_retryable:
            try:
                logger.info("retrying_comprehension_stage", extra={"can_do_id": can_do_id, "attempt": 1})
                await asyncio.sleep(2)  # Brief delay before retry
                reading = await asyncio.to_thread(
                    pipeline.gen_reading_card,
                    llm_call_fast,
                    metalanguage,
                    cando_input,
                    plan,
                    content_cards["lesson_dialogue"],
                    max_repair=0,
                    kit_context=kit_context,
        profile_context=profile_context,
                    kit_requirements=kit_requirements,
                )
                comprehension_cards = await pipeline.gen_comprehension_stage(
                    llm_call_main,
                    llm_call_fast,
                    metalanguage,
                    plan,
                    content_cards,
                    reading=reading,
                    max_repair=0,
                    kit_context=kit_context,
        profile_context=profile_context,
                    kit_requirements=kit_requirements,
                )
                await _update_lesson_stage_in_db(pg, lesson_id, version, "comprehension", comprehension_cards)
                if progress_callback:
                    progress_callback({"stage": "comprehension", "progress": 70, "message": "Comprehension stage complete", "event": "comprehension_ready"})
                logger.info("comprehension_stage_retry_successful", extra={"can_do_id": can_do_id})
                return  # Success after retry
            except Exception as retry_error:
                logger.error("comprehension_stage_retry_failed", extra={"can_do_id": can_do_id, "error": str(retry_error)})
                error_message = f"Retry failed: {str(retry_error)}"
        
        # Mark as failed in metadata but continue (atomic JSONB update)
        try:
            import json
            # Use simpler JSONB update pattern
            error_update = json.dumps({
                "error_type": error_type,
                "message": error_message[:500],
                "retryable": is_retryable,
                "timestamp": time.time()
            }, ensure_ascii=False)
            
            # Use jsonb_set with proper path syntax
            await pg.execute(
                text("""
                    UPDATE lesson_versions 
                    SET lesson_plan = 
                        jsonb_set(
                            jsonb_set(
                                COALESCE(lesson_plan, '{}'::jsonb),
                                '{lesson,meta,generation_status,comprehension}',
                                '"failed"'::jsonb
                            ),
                            '{lesson,meta,errors,comprehension}',
                            :errors::jsonb
                        )
                    WHERE lesson_id = :lid AND version = :ver
                """),
                {"lid": lesson_id, "ver": version, "errors": error_update}
            )
            await pg.commit()
            print(f"[UPDATE] Successfully marked comprehension as failed for {can_do_id}")
            # Notify via callback
            if progress_callback:
                progress_callback({
                    "stage": "comprehension",
                    "progress": 60,
                    "message": f"Comprehension stage failed: {error_message[:100]}",
                    "event": "comprehension_failed",
                    "error": {
                        "type": error_type,
                        "message": error_message,
                        "retryable": is_retryable
                    }
                })
        except Exception as update_err:
            logger.error("failed_to_update_comprehension_error_status", extra={"error": str(update_err)})
    
    try:
        # STAGE 3: PRODUCTION
        # Check dependency: production needs comprehension to be complete
        comprehension_ready = False
        try:
            result = await pg.execute(
                text("SELECT lesson_plan FROM lesson_versions WHERE lesson_id = :lid AND version = :ver"),
                {"lid": lesson_id, "ver": version}
            )
            row = result.first()
            if row:
                import json
                current_lesson = json.loads(row[0]) if isinstance(row[0], str) else row[0]
                status = current_lesson.get("lesson", {}).get("meta", {}).get("generation_status", {})
                comprehension_ready = status.get("comprehension") == "complete"
        except Exception:
            pass
        
        if not comprehension_ready:
            logger.warning("production_stage_waiting_for_comprehension", extra={"can_do_id": can_do_id})
            # Wait up to 5 minutes for comprehension to complete
            max_wait = 300  # 5 minutes
            wait_interval = 5  # Check every 5 seconds
            waited = 0
            while not comprehension_ready and waited < max_wait:
                await asyncio.sleep(wait_interval)
                waited += wait_interval
                try:
                    result = await pg.execute(
                        text("SELECT lesson_plan FROM lesson_versions WHERE lesson_id = :lid AND version = :ver"),
                        {"lid": lesson_id, "ver": version}
                    )
                    row = result.first()
                    if row:
                        import json
                        current_lesson = json.loads(row[0]) if isinstance(row[0], str) else row[0]
                        status = current_lesson.get("lesson", {}).get("meta", {}).get("generation_status", {})
                        comprehension_ready = status.get("comprehension") == "complete"
                except Exception:
                    pass
            
            if not comprehension_ready:
                logger.warning("production_stage_proceeding_without_comprehension", extra={"can_do_id": can_do_id})
        
        if progress_callback:
            progress_callback({"stage": "production", "progress": 80, "message": "Generating Production stage..."})
        
        logger.info("Generating Production stage (background)", extra={"can_do_id": can_do_id, "stage": "production"})
        production_start = time.time()
        print(f"[COMPILE] {can_do_id}: Starting Production stage generation (background) at {time.strftime('%H:%M:%S')}")
        
        # Fetch comprehension cards for production stage
        comprehension_cards_for_prod = {}
        try:
            result = await pg.execute(
                text("SELECT lesson_plan FROM lesson_versions WHERE lesson_id = :lid AND version = :ver"),
                {"lid": lesson_id, "ver": version}
            )
            row = result.first()
            if row:
                import json
                current_lesson = json.loads(row[0]) if isinstance(row[0], str) else row[0]
                if "cards" in current_lesson:
                    comprehension_cards_for_prod = {
                        "reading_comprehension": current_lesson["cards"].get("reading_comprehension"),
                        "comprehension_exercises": current_lesson["cards"].get("comprehension_exercises"),
                        "ai_comprehension_tutor": current_lesson["cards"].get("ai_comprehension_tutor"),
                    }
        except Exception:
            pass  # Continue without comprehension cards if fetch fails
        
        production_cards = await pipeline.gen_production_stage(
            llm_call_main,
            llm_call_fast,
            metalanguage,
            plan,
            content_cards,
            comprehension_cards=comprehension_cards_for_prod if comprehension_cards_for_prod else None,
            max_repair=0,
            kit_context=kit_context,
        profile_context=profile_context,
            kit_requirements=kit_requirements,
        )
        
        production_duration = time.time() - production_start
        print(f"[COMPILE] {can_do_id}: Production stage generated in {production_duration:.1f}s")
        logger.info("Production stage generated (background)", extra={"can_do_id": can_do_id, "stage": "production", "duration": production_duration})
        
        # Update lesson in database
        await _update_lesson_stage_in_db(pg, lesson_id, version, "production", production_cards)
        if progress_callback:
            progress_callback({"stage": "production", "progress": 90, "message": "Production stage complete", "event": "production_ready"})
        
    except Exception as e:
        error_type = type(e).__name__
        error_message = str(e)
        is_retryable = _is_retryable_error(e)
        
        logger.error(
            "production_stage_generation_failed",
            extra={
                "can_do_id": can_do_id,
                "error": error_message,
                "error_type": error_type,
                "retryable": is_retryable
            }
        )
        
        # Try retry if it's a retryable error
        if is_retryable:
            try:
                logger.info("retrying_production_stage", extra={"can_do_id": can_do_id, "attempt": 1})
                await asyncio.sleep(2)
                production_cards = await pipeline.gen_production_stage(
                    llm_call_main,
                    llm_call_fast,
                    metalanguage,
                    plan,
                    content_cards,
                    comprehension_cards=comprehension_cards_for_prod if comprehension_cards_for_prod else None,
                    max_repair=0,
                    kit_context=kit_context,
        profile_context=profile_context,
                    kit_requirements=kit_requirements,
                )
                await _update_lesson_stage_in_db(pg, lesson_id, version, "production", production_cards)
                if progress_callback:
                    progress_callback({"stage": "production", "progress": 90, "message": "Production stage complete", "event": "production_ready"})
                logger.info("production_stage_retry_successful", extra={"can_do_id": can_do_id})
                return
            except Exception as retry_error:
                logger.error("production_stage_retry_failed", extra={"can_do_id": can_do_id, "error": str(retry_error)})
                error_message = f"Retry failed: {str(retry_error)}"
        
        # Mark as failed but continue
        try:
            result = await pg.execute(
                text("SELECT lesson_plan FROM lesson_versions WHERE lesson_id = :lid AND version = :ver"),
                {"lid": lesson_id, "ver": version}
            )
            # Use atomic JSONB update instead of read-modify-write
            import json
            status_json = json.dumps({"production": f"failed: {error_message[:200]}"}, ensure_ascii=False)
            error_json = json.dumps({
                "production": {
                    "error_type": error_type,
                    "message": error_message[:500],
                    "retryable": is_retryable,
                    "timestamp": time.time()
                }
            }, ensure_ascii=False)
            
            await pg.execute(
                text("""
                    UPDATE lesson_versions 
                    SET lesson_plan = jsonb_set(
                        jsonb_set(
                            COALESCE(lesson_plan, '{}'::jsonb),
                            '{lesson,meta,generation_status}',
                            COALESCE(lesson_plan->'lesson'->'meta'->'generation_status', '{}'::jsonb) || :status::jsonb
                        ),
                        '{lesson,meta,errors}',
                        COALESCE(lesson_plan->'lesson'->'meta'->'errors', '{}'::jsonb) || :errors::jsonb
                    )
                    WHERE lesson_id = :lid AND version = :ver
                """),
                {"lid": lesson_id, "ver": version, "status": status_json, "errors": error_json}
            )
            await pg.commit()
            if progress_callback:
                progress_callback({
                    "stage": "production",
                    "progress": 80,
                    "message": f"Production stage failed: {error_message[:100]}",
                    "event": "production_failed",
                    "error": {
                        "type": error_type,
                        "message": error_message,
                        "retryable": is_retryable
                    }
                })
        except Exception as update_err:
            logger.error("failed_to_update_production_error_status", extra={"error": str(update_err)})
    
    try:
        # STAGE 4: INTERACTION
        # Check dependencies: interaction needs production (and ideally comprehension) to be complete
        production_ready = False
        comprehension_ready = False
        try:
            result = await pg.execute(
                text("SELECT lesson_plan FROM lesson_versions WHERE lesson_id = :lid AND version = :ver"),
                {"lid": lesson_id, "ver": version}
            )
            row = result.first()
            if row:
                import json
                current_lesson = json.loads(row[0]) if isinstance(row[0], str) else row[0]
                status = current_lesson.get("lesson", {}).get("meta", {}).get("generation_status", {})
                production_ready = status.get("production") == "complete"
                comprehension_ready = status.get("comprehension") == "complete"
        except Exception:
            pass
        
        if not production_ready:
            logger.warning("interaction_stage_waiting_for_production", extra={"can_do_id": can_do_id})
            max_wait = 300  # 5 minutes
            wait_interval = 5
            waited = 0
            while not production_ready and waited < max_wait:
                await asyncio.sleep(wait_interval)
                waited += wait_interval
                try:
                    result = await pg.execute(
                        text("SELECT lesson_plan FROM lesson_versions WHERE lesson_id = :lid AND version = :ver"),
                        {"lid": lesson_id, "ver": version}
                    )
                    row = result.first()
                    if row:
                        import json
                        current_lesson = json.loads(row[0]) if isinstance(row[0], str) else row[0]
                        status = current_lesson.get("lesson", {}).get("meta", {}).get("generation_status", {})
                        production_ready = status.get("production") == "complete"
                except Exception:
                    pass
            
            if not production_ready:
                logger.warning("interaction_stage_proceeding_without_production", extra={"can_do_id": can_do_id})
        
        if progress_callback:
            progress_callback({"stage": "interaction", "progress": 95, "message": "Generating Interaction stage..."})
        
        logger.info("Generating Interaction stage (background)", extra={"can_do_id": can_do_id, "stage": "interaction"})
        interaction_start = time.time()
        print(f"[COMPILE] {can_do_id}: Starting Interaction stage generation (background) at {time.strftime('%H:%M:%S')}")
        
        # Fetch previous stages for interaction stage
        comprehension_cards_for_inter = {}
        production_cards_for_inter = {}
        try:
            result = await pg.execute(
                text("SELECT lesson_plan FROM lesson_versions WHERE lesson_id = :lid AND version = :ver"),
                {"lid": lesson_id, "ver": version}
            )
            row = result.first()
            if row:
                import json
                current_lesson = json.loads(row[0]) if isinstance(row[0], str) else row[0]
                if "cards" in current_lesson:
                    comprehension_cards_for_inter = {
                        "reading_comprehension": current_lesson["cards"].get("reading_comprehension"),
                        "comprehension_exercises": current_lesson["cards"].get("comprehension_exercises"),
                        "ai_comprehension_tutor": current_lesson["cards"].get("ai_comprehension_tutor"),
                    }
                    production_cards_for_inter = {
                        "guided_dialogue": current_lesson["cards"].get("guided_dialogue"),
                        "production_exercises": current_lesson["cards"].get("production_exercises"),
                        "ai_production_evaluator": current_lesson["cards"].get("ai_production_evaluator"),
                    }
        except Exception:
            pass  # Continue without previous stages if fetch fails
        
        interaction_cards = await pipeline.gen_interaction_stage(
            llm_call_main,
            llm_call_fast,
            metalanguage,
            plan,
            content_cards,
            comprehension_cards=comprehension_cards_for_inter if comprehension_cards_for_inter else None,
            production_cards=production_cards_for_inter if production_cards_for_inter else None,
            max_repair=0,
            kit_context=kit_context,
        profile_context=profile_context,
            kit_requirements=kit_requirements,
        )
        
        interaction_duration = time.time() - interaction_start
        print(f"[COMPILE] {can_do_id}: Interaction stage generated in {interaction_duration:.1f}s")
        logger.info("Interaction stage generated (background)", extra={"can_do_id": can_do_id, "stage": "interaction", "duration": interaction_duration})
        
        # Update lesson in database
        await _update_lesson_stage_in_db(pg, lesson_id, version, "interaction", interaction_cards)
        if progress_callback:
            progress_callback({"stage": "interaction", "progress": 100, "message": "All stages complete!", "event": "interaction_ready"})
        
    except Exception as e:
        error_type = type(e).__name__
        error_message = str(e)
        is_retryable = _is_retryable_error(e)
        
        logger.error(
            "interaction_stage_generation_failed",
            extra={
                "can_do_id": can_do_id,
                "error": error_message,
                "error_type": error_type,
                "retryable": is_retryable
            }
        )
        
        # Try retry if it's a retryable error
        if is_retryable:
            try:
                logger.info("retrying_interaction_stage", extra={"can_do_id": can_do_id, "attempt": 1})
                await asyncio.sleep(2)
                interaction_cards = await pipeline.gen_interaction_stage(
                    llm_call_main,
                    llm_call_fast,
                    metalanguage,
                    plan,
                    content_cards,
                    comprehension_cards=comprehension_cards_for_inter if comprehension_cards_for_inter else None,
                    production_cards=production_cards_for_inter if production_cards_for_inter else None,
                    max_repair=0,
                    kit_context=kit_context,
        profile_context=profile_context,
                    kit_requirements=kit_requirements,
                )
                await _update_lesson_stage_in_db(pg, lesson_id, version, "interaction", interaction_cards)
                if progress_callback:
                    progress_callback({"stage": "interaction", "progress": 100, "message": "All stages complete!", "event": "interaction_ready"})
                logger.info("interaction_stage_retry_successful", extra={"can_do_id": can_do_id})
                return
            except Exception as retry_error:
                logger.error("interaction_stage_retry_failed", extra={"can_do_id": can_do_id, "error": str(retry_error)})
                error_message = f"Retry failed: {str(retry_error)}"
        
        # Mark as failed (atomic JSONB update)
        try:
            import json
            status_json = json.dumps({"interaction": f"failed: {error_message[:200]}"}, ensure_ascii=False)
            error_json = json.dumps({
                "interaction": {
                    "error_type": error_type,
                    "message": error_message[:500],
                    "retryable": is_retryable,
                    "timestamp": time.time()
                }
            }, ensure_ascii=False)
            
            await pg.execute(
                text("""
                    UPDATE lesson_versions 
                    SET lesson_plan = jsonb_set(
                        jsonb_set(
                            COALESCE(lesson_plan, '{}'::jsonb),
                            '{lesson,meta,generation_status}',
                            COALESCE(lesson_plan->'lesson'->'meta'->'generation_status', '{}'::jsonb) || :status::jsonb
                        ),
                        '{lesson,meta,errors}',
                        COALESCE(lesson_plan->'lesson'->'meta'->'errors', '{}'::jsonb) || :errors::jsonb
                    )
                    WHERE lesson_id = :lid AND version = :ver
                """),
                {"lid": lesson_id, "ver": version, "status": status_json, "errors": error_json}
            )
            await pg.commit()
            if progress_callback:
                progress_callback({
                    "stage": "interaction",
                    "progress": 95,
                    "message": f"Interaction stage failed: {error_message[:100]}",
                    "event": "interaction_failed",
                    "error": {
                        "type": error_type,
                        "message": error_message,
                        "retryable": is_retryable
                    }
                })
        except Exception as update_err:
            logger.error("failed_to_update_interaction_error_status", extra={"error": str(update_err)})
    
    print(f"[COMPILE] {can_do_id}: ✅ Background generation complete")


async def regenerate_lesson_stage(
    *,
    neo: AsyncSession,
    pg: PgSession,
    lesson_id: int,
    version: int,
    stage: str,
    model: str = "gpt-4.1",
    timeout: int = 120,
    fast_model_override: Optional[str] = None,
    user_id: Optional[uuid.UUID] = None,
) -> Dict[str, Any]:
    """
    Regenerate a specific stage of an existing lesson.
    
    This function fetches the lesson plan, extracts necessary context (plan, content_cards, etc.),
    reconstructs compilation context (llm_call, kit_context, profile_context), and regenerates
    the specified stage.
    
    Args:
        neo: Neo4j session
        pg: PostgreSQL session
        lesson_id: Lesson ID
        version: Lesson version
        stage: Stage to regenerate ("comprehension", "production", or "interaction")
        model: LLM model to use (default: "gpt-4.1")
        timeout: LLM timeout in seconds (default: 120)
        fast_model_override: Override for fast model
        user_id: Optional user ID for profile context
    
    Returns:
        Dict with status and generated stage data
    
    Raises:
        ValueError: If lesson not found or stage is invalid
    """
    import json
    import time
    import asyncio
    from sqlalchemy import text
    
    if stage not in ["comprehension", "production", "interaction"]:
        raise ValueError(f"Invalid stage: {stage}. Must be one of: comprehension, production, interaction")
    
    pipeline = _load_pipeline_module()
    
    # Fetch lesson plan from database
    result = await pg.execute(
        text("SELECT lesson_plan FROM lesson_versions WHERE lesson_id = :lid AND version = :ver"),
        {"lid": lesson_id, "ver": version}
    )
    row = result.first()
    if not row:
        raise ValueError(f"Lesson {lesson_id} version {version} not found")
    
    lesson_plan = json.loads(row[0]) if isinstance(row[0], str) else row[0]
    
    # Extract can_do_id and metadata
    can_do_id = lesson_plan.get("lesson", {}).get("meta", {}).get("can_do", {}).get("uid")
    if not can_do_id:
        raise ValueError("Cannot determine can_do_id from lesson")
    
    # Extract plan and convert to DomainPlan object (reuse existing plan)
    plan_dict = lesson_plan.get("plan")
    if not plan_dict:
        raise ValueError("Cannot find plan in lesson")
    
    # Convert dict to DomainPlan object for reuse
    plan = None
    try:
        from cando_creation.models.plan import DomainPlan
        plan = DomainPlan.model_validate(plan_dict)
        
        # Validate plan quality
        quality_issues = _validate_plan_quality(plan)
        if quality_issues:
            logger.warning("reused_plan_has_quality_issues", extra={"lesson_id": lesson_id, "issues": quality_issues})
        
        logger.info("plan_reused_from_lesson", extra={"lesson_id": lesson_id, "version": version})
    except Exception as e:
        logger.warning("plan_extraction_failed_regenerating", extra={"lesson_id": lesson_id, "error": str(e)})
        # Fallback: regenerate plan if extraction fails
        plan = None
    
    # Extract content cards (needed for all stages)
    content_cards = {}
    if lesson_plan.get("cards"):
        cards = lesson_plan["cards"]
        content_cards = {
            "objective": cards.get("objective"),
            "words": cards.get("words"),
            "grammar_patterns": cards.get("grammar_patterns"),
            "formulaic_expressions": cards.get("formulaic_expressions"),
            "lesson_dialogue": cards.get("lesson_dialogue"),
            "cultural_explanation": cards.get("cultural_explanation"),
        }
    
    # Validate that content cards exist (required for all stages)
    if not content_cards.get("lesson_dialogue"):
        raise ValueError("Content stage is incomplete. Cannot regenerate dependent stages. Please regenerate the entire lesson.")
    
    # Extract metalanguage (default to "en")
    metalanguage = lesson_plan.get("lesson", {}).get("meta", {}).get("metalanguage", "en")
    
    # Fetch CanDo metadata
    meta = await _fetch_cando_meta(neo, can_do_id)
    cando_input = {
        "uid": meta["uid"],
        "level": meta["level"],
        "primaryTopic": meta["primaryTopic"],
        "primaryTopicEn": meta["primaryTopicEn"],
        "skillDomain": meta["skillDomain"],
        "type": meta["type"],
        "descriptionEn": meta.get("descriptionEn", ""),
        "descriptionJa": meta.get("descriptionJa", ""),
        "titleEn": meta.get("titleEn", ""),
        "titleJa": meta.get("titleJa", ""),
        "source": meta.get("source", "graph"),
    }
    
    # Try to get user_id from lesson metadata if not provided
    if not user_id:
        user_id_str = lesson_plan.get("lesson", {}).get("meta", {}).get("user_id")
        if user_id_str:
            try:
                user_id = uuid.UUID(user_id_str)
            except (ValueError, TypeError):
                user_id = None
    
    # Fetch pre-lesson kit if user_id is available
    prelesson_kit = None
    if user_id:
        try:
            prelesson_kit = await _fetch_prelesson_kit_from_path(pg, can_do_id, user_id)
        except Exception as e:
            logger.warning("prelesson_kit_fetch_failed_for_regeneration", extra={"error": str(e)})
    
    # Build kit context
    kit_context = ""
    kit_requirements = ""
    if prelesson_kit:
        try:
            kit_context, kit_requirements = _build_prelesson_kit_context(prelesson_kit)
        except Exception as e:
            logger.warning("kit_context_build_failed_for_regeneration", extra={"error": str(e)})
    
    # Build profile context using shared function
    profile_context = ""
    if user_id:
        profile_context = await _build_user_profile_context(
            pg=pg,
            user_id=user_id,
            can_do_id=can_do_id,
            include_full_details=False,  # Simplified for regeneration
        )
    
    # Create LLM call functions
    fast_enabled = os.getenv("CANDO_FAST_MODE", "1") == "1"
    fast_model = (fast_model_override or os.getenv("OPENAI_FAST_MODEL", "gpt-4.1")).strip()
    
    llm_call_main = _make_llm_call_openai(model=model, timeout=timeout)
    fallback_fast_model = "gpt-4.1"
    _fast_fallback_active = False
    _llm_call_fast_primary = _make_llm_call_openai(model=fast_model, timeout=timeout) if fast_enabled else llm_call_main
    _llm_call_fast_fallback = _make_llm_call_openai(model=fallback_fast_model, timeout=timeout) if fast_enabled else llm_call_main
    
    def llm_call_fast(system: str, user: str) -> str:
        nonlocal _fast_fallback_active
        if not fast_enabled:
            return llm_call_main(system, user)
        if _fast_fallback_active:
            return _llm_call_fast_fallback(system, user)
        try:
            return _llm_call_fast_primary(system, user)
        except Exception:
            _fast_fallback_active = True
            return _llm_call_fast_fallback(system, user)
    
    # Regenerate plan if extraction failed
    if plan is None:
        logger.info("regenerating_plan_for_stage", extra={"lesson_id": lesson_id, "stage": stage})
        try:
            # Try to get cached plan first
            profile_hash = _hash_profile_context(profile_context) if profile_context else ""
            kit_hash = _hash_kit_context(kit_context, kit_requirements) if (kit_context or kit_requirements) else ""
            
            cached_plan_json = await _get_cached_plan(pg, can_do_id, profile_hash, kit_hash)
            if cached_plan_json:
                try:
                    from cando_creation.models.plan import DomainPlan
                    plan = DomainPlan.model_validate(cached_plan_json)
                    logger.info("plan_loaded_from_cache_for_regeneration", extra={"lesson_id": lesson_id})
                except Exception as e:
                    logger.warning("cached_plan_validation_failed_for_regeneration", extra={"lesson_id": lesson_id, "error": str(e)})
            
            # Generate plan if still None
            if plan is None:
                plan = await asyncio.to_thread(
                    pipeline.gen_domain_plan,
                    llm_call_main,
                    cando_input,
                    metalanguage,
                    kit_context=kit_context,
                    kit_requirements=kit_requirements,
                    profile_context=profile_context,
                )
                # Validate plan quality
                quality_issues = _validate_plan_quality(plan)
                if quality_issues:
                    logger.warning("regenerated_plan_has_quality_issues", extra={"lesson_id": lesson_id, "issues": quality_issues})
                
                # Cache the generated plan
                if profile_hash or kit_hash:
                    await _cache_plan(pg, can_do_id, profile_hash, kit_hash, plan, ttl_hours=24)
                logger.info("plan_regenerated_for_stage", extra={"lesson_id": lesson_id, "stage": stage})
        except Exception as e:
            logger.error("plan_regeneration_failed", extra={"lesson_id": lesson_id, "error": str(e)})
            raise ValueError(f"Failed to regenerate plan: {str(e)}")
    
    # Generate the requested stage
    logger.info("regenerating_lesson_stage", extra={"lesson_id": lesson_id, "version": version, "stage": stage, "can_do_id": can_do_id})
    stage_start = time.time()
    
    # Update status to "generating" at the start
    try:
        await _update_lesson_stage_status_in_db(pg, lesson_id, version, stage, "generating")
    except Exception as status_err:
        logger.warning("failed_to_update_stage_status_to_generating", extra={"error": str(status_err)})
        # Continue with regeneration even if status update fails
    
    try:
        if stage == "comprehension":
            # Generate reading first
            reading = await asyncio.to_thread(
                pipeline.gen_reading_card,
                llm_call_fast,
                metalanguage,
                cando_input,
                plan,
                content_cards["lesson_dialogue"],
                max_repair=0,
                kit_context=kit_context,
        profile_context=profile_context,
                kit_requirements=kit_requirements,
            )
            
            # Generate comprehension stage
            comprehension_cards = await pipeline.gen_comprehension_stage(
                llm_call_main,
                llm_call_fast,
                metalanguage,
                plan,
                content_cards,
                reading=reading,
                max_repair=0,
                kit_context=kit_context,
        profile_context=profile_context,
                kit_requirements=kit_requirements,
            )
            
            # Update lesson in database
            await _update_lesson_stage_in_db(pg, lesson_id, version, "comprehension", comprehension_cards)
            
            stage_duration = time.time() - stage_start
            logger.info("comprehension_stage_regenerated", extra={"lesson_id": lesson_id, "duration": stage_duration})
            
            return {
                "status": "success",
                "stage": "comprehension",
                "cards": comprehension_cards,
                "duration": stage_duration
            }
        
        elif stage == "production":
            # Need comprehension cards for production
            comprehension_cards_for_prod = {}
            if lesson_plan.get("cards"):
                cards = lesson_plan["cards"]
                comprehension_cards_for_prod = {
                    "reading_comprehension": cards.get("reading_comprehension"),
                    "comprehension_exercises": cards.get("comprehension_exercises"),
                    "ai_comprehension_tutor": cards.get("ai_comprehension_tutor"),
                }
            
            # Warn if comprehension stage is missing (but allow regeneration)
            if not any(comprehension_cards_for_prod.values()):
                logger.warning(
                    "production_regeneration_without_comprehension",
                    extra={"lesson_id": lesson_id, "version": version}
                )
            
            # Generate production stage
            production_cards = await pipeline.gen_production_stage(
                llm_call_main,
                llm_call_fast,
                metalanguage,
                plan,
                content_cards,
                comprehension_cards=comprehension_cards_for_prod if comprehension_cards_for_prod else None,
                max_repair=0,
                kit_context=kit_context,
        profile_context=profile_context,
                kit_requirements=kit_requirements,
            )
            
            # Update lesson in database
            await _update_lesson_stage_in_db(pg, lesson_id, version, "production", production_cards)
            
            stage_duration = time.time() - stage_start
            logger.info("production_stage_regenerated", extra={"lesson_id": lesson_id, "duration": stage_duration})
            
            return {
                "status": "success",
                "stage": "production",
                "cards": production_cards,
                "duration": stage_duration
            }
        
        elif stage == "interaction":
            # Need comprehension and production cards for interaction
            comprehension_cards_for_inter = {}
            production_cards_for_inter = {}
            if lesson_plan.get("cards"):
                cards = lesson_plan["cards"]
                comprehension_cards_for_inter = {
                    "reading_comprehension": cards.get("reading_comprehension"),
                    "comprehension_exercises": cards.get("comprehension_exercises"),
                    "ai_comprehension_tutor": cards.get("ai_comprehension_tutor"),
                }
                production_cards_for_inter = {
                    "guided_dialogue": cards.get("guided_dialogue"),
                    "production_exercises": cards.get("production_exercises"),
                    "ai_production_evaluator": cards.get("ai_production_evaluator"),
                }
            
            # Warn if dependencies are missing (but allow regeneration)
            if not any(comprehension_cards_for_inter.values()):
                logger.warning(
                    "interaction_regeneration_without_comprehension",
                    extra={"lesson_id": lesson_id, "version": version}
                )
            if not any(production_cards_for_inter.values()):
                logger.warning(
                    "interaction_regeneration_without_production",
                    extra={"lesson_id": lesson_id, "version": version}
                )
            
            # Generate interaction stage
            interaction_cards = await pipeline.gen_interaction_stage(
                llm_call_main,
                llm_call_fast,
                metalanguage,
                plan,
                content_cards,
                comprehension_cards=comprehension_cards_for_inter if comprehension_cards_for_inter else None,
                production_cards=production_cards_for_inter if production_cards_for_inter else None,
                max_repair=0,
                kit_context=kit_context,
        profile_context=profile_context,
                kit_requirements=kit_requirements,
            )
            
            # Update lesson in database
            await _update_lesson_stage_in_db(pg, lesson_id, version, "interaction", interaction_cards)
            
            stage_duration = time.time() - stage_start
            logger.info("interaction_stage_regenerated", extra={"lesson_id": lesson_id, "duration": stage_duration})
            
            return {
                "status": "success",
                "stage": "interaction",
                "cards": interaction_cards,
                "duration": stage_duration
            }
    
    except Exception as e:
        error_type = type(e).__name__
        error_message = str(e)
        logger.error(
            "stage_regeneration_failed",
            extra={
                "lesson_id": lesson_id,
                "version": version,
                "stage": stage,
                "error": error_message,
                "error_type": error_type
            }
        )
        
        # Update error status in lesson (atomic JSONB update)
        try:
            import json
            status_json = json.dumps({stage: f"failed: {error_message[:200]}"}, ensure_ascii=False)
            error_json = json.dumps({
                stage: {
                    "type": error_type,
                    "message": error_message[:500],
                    "retryable": _is_retryable_error(e),
                    "timestamp": time.time()
                }
            }, ensure_ascii=False)
            
            await pg.execute(
                text("""
                    UPDATE lesson_versions 
                    SET lesson_plan = jsonb_set(
                        jsonb_set(
                            COALESCE(lesson_plan, '{}'::jsonb),
                            '{lesson,meta,generation_status}',
                            COALESCE(lesson_plan->'lesson'->'meta'->'generation_status', '{}'::jsonb) || :status::jsonb
                        ),
                        '{lesson,meta,errors}',
                        COALESCE(lesson_plan->'lesson'->'meta'->'errors', '{}'::jsonb) || :errors::jsonb
                    )
                    WHERE lesson_id = :lid AND version = :ver
                """),
                {"lid": lesson_id, "ver": version, "status": status_json, "errors": error_json}
            )
            await pg.commit()
        except Exception as update_err:
            logger.error("failed_to_update_stage_error_status", extra={"error": str(update_err)})
        
        raise


async def compile_lessonroot(
    *,
    neo: AsyncSession,
    pg: PgSession,
    can_do_id: str,
    metalanguage: str = "en",
    model: str = "gpt-4.1",
    timeout: int = 120,
    prelesson_kit: Optional[Dict[str, Any]] = None,
    user_id: Optional[uuid.UUID] = None,
    fast_model_override: Optional[str] = None,
    progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    incremental: bool = False,
) -> Dict[str, Any]:
    # DEBUG: Immediate print to confirm function is called
    import sys
    import time as _time
    import json as _j
    _compile_start = _time.time()
    sys.stderr.write(f"[COMPILE] {can_do_id}: compile_lessonroot() CALLED at {_time.strftime('%H:%M:%S')}\n")
    sys.stderr.flush()
    logger.info("compile_lessonroot() called", extra={"can_do_id": can_do_id, "model": model})
    
    pipeline = _load_pipeline_module()
    meta = await _fetch_cando_meta(neo, can_do_id)
    cando_input = {
        "uid": meta["uid"],
        "level": meta["level"],
        "primaryTopic": meta["primaryTopic"],
        "primaryTopicEn": meta["primaryTopicEn"],
        "skillDomain": meta["skillDomain"],
        "type": meta["type"],
        "descriptionEn": meta.get("descriptionEn", ""),
        "descriptionJa": meta.get("descriptionJa", ""),
        "titleEn": meta.get("titleEn", ""),
        "titleJa": meta.get("titleJa", ""),
        "source": meta.get("source", "graph"),
    }

    # Fetch pre-lesson kit if not provided
    if prelesson_kit is None and user_id:
        try:
            prelesson_kit = await _fetch_prelesson_kit_from_path(pg, can_do_id, user_id)
            if prelesson_kit:
                logger.info("prelesson_kit_fetched_from_path", extra={"can_do_id": can_do_id, "user_id": str(user_id)})
            else:
                logger.debug("prelesson_kit_not_found_in_path", extra={"can_do_id": can_do_id, "user_id": str(user_id)})
        except Exception as e:
            logger.warning(
                "prelesson_kit_fetch_failed",
                extra={"can_do_id": can_do_id, "user_id": str(user_id), "error": str(e)}
            )
            # Continue compilation without kit if fetch fails
            prelesson_kit = None
    
    # Fetch user profile data for personalization context using shared function
    profile_context = ""
    if user_id:
        profile_context = await _build_user_profile_context(
            pg=pg,
            user_id=user_id,
            can_do_id=can_do_id,
            include_full_details=True,  # Full details for initial compilation
        )
    
    # Build kit context if available
    kit_context = ""
    kit_requirements = ""
    if prelesson_kit:
        try:
            kit_context, kit_requirements = _build_prelesson_kit_context(prelesson_kit)
            logger.info(
                "prelesson_kit_integrated_into_compilation",
                extra={
                    "can_do_id": can_do_id,
                    "has_context": bool(kit_context),
                    "has_requirements": bool(kit_requirements),
                }
            )
        except Exception as e:
            logger.warning(
                "prelesson_kit_context_build_failed",
                extra={"can_do_id": can_do_id, "error": str(e)}
            )
            # Continue compilation without kit context if build fails
            kit_context = ""
            kit_requirements = ""

    # Performance: use a cheaper/faster model for non-critical cards.
    # Runtime evidence: reading generation is the dominant step (~60s+).
    fast_enabled = os.getenv("CANDO_FAST_MODE", "1") == "1"
    fast_model = (fast_model_override or os.getenv("OPENAI_FAST_MODEL", "gpt-4.1")).strip()

    llm_call_main = _make_llm_call_openai(model=model, timeout=timeout)

    # Safe fast-model wrapper with fallback if the requested model isn't available / compatible.
    fallback_fast_model = "gpt-4.1"
    _fast_fallback_active = False
    _llm_call_fast_primary = _make_llm_call_openai(model=fast_model, timeout=timeout) if fast_enabled else llm_call_main
    _llm_call_fast_fallback = _make_llm_call_openai(model=fallback_fast_model, timeout=timeout) if fast_enabled else llm_call_main

    def llm_call_fast(system: str, user: str) -> str:
        nonlocal _fast_fallback_active
        if not fast_enabled:
            return llm_call_main(system, user)
        if _fast_fallback_active:
            return _llm_call_fast_fallback(system, user)
        try:
            return _llm_call_fast_primary(system, user)
        except Exception as e:
            _fast_fallback_active = True
            logger.warning(
                "Fast model failed, falling back",
                extra={
                    "can_do_id": can_do_id,
                    "fast_model": fast_model,
                    "fallback_fast_model": fallback_fast_model,
                    "error_type": type(e).__name__,
                    "error": str(e)[:300],
                },
            )
            return _llm_call_fast_fallback(system, user)

    logger.debug(
        "Model selection",
        extra={
            "can_do_id": can_do_id,
            "fast_enabled": fast_enabled,
            "model_main": model,
            "model_fast": fast_model if fast_enabled else model,
            "fast_model_override_present": bool(fast_model_override),
        },
    )

    # Sequence: Generate plan and objective first (must be sequential - objective depends on plan)
    import time
    import sys
    start_time = time.time()
    msg = f"[COMPILE] {can_do_id}: Starting lesson compilation at {time.strftime('%H:%M:%S')}"
    print(msg, flush=True)
    sys.stderr.write(msg + "\n")
    logger.info("Starting lesson compilation", extra={"can_do_id": can_do_id, "step": "plan"})
    
    # Progress: Planning
    if progress_callback:
        progress_callback({"step": "planning", "progress": 5, "message": "Generating lesson plan..."})
    
    plan_start = time.time()
    logger.debug("Step: Plan generation START", extra={"can_do_id": can_do_id, "step": "plan"})
    plan = await asyncio.to_thread(
        pipeline.gen_domain_plan,
        llm_call_main,
        cando_input,
        metalanguage,
        kit_context=kit_context,
        kit_requirements=kit_requirements,
        profile_context=profile_context,
    )
    _plan_duration = time.time() - plan_start
    print(f"[COMPILE] {can_do_id}: Plan generated in {_plan_duration:.1f}s")
    logger.info("Plan generated", extra={"can_do_id": can_do_id, "step": "plan", "duration_seconds": round(_plan_duration, 2)})
    
    # Check if incremental mode is enabled
    if incremental:
        logger.info("Incremental mode enabled - generating Content stage only", extra={"can_do_id": can_do_id})
        
        # Generate and save Content stage only
        lesson_json, lesson_id, version, content_cards_dict = await _compile_content_stage_only(
            neo=neo,
            pg=pg,
            can_do_id=can_do_id,
            metalanguage=metalanguage,
            model=model,
            timeout=timeout,
            prelesson_kit=prelesson_kit,
            user_id=user_id,
            fast_model_override=fast_model_override,
            progress_callback=progress_callback,
            cando_input=cando_input,
            plan=plan,
            llm_call_main=llm_call_main,
            llm_call_fast=llm_call_fast,
            kit_context=kit_context,
            kit_requirements=kit_requirements,
            profile_context=profile_context,
        )
        
        # Track kit usage if available
        kit_usage_report = None
        if prelesson_kit:
            try:
                kit_usage_report = _track_kit_usage(lesson_json, prelesson_kit)
            except Exception as e:
                logger.warning("prelesson_kit_usage_tracking_failed", extra={"can_do_id": can_do_id, "error": str(e)})
        
        # Spawn background task for remaining stages
        asyncio.create_task(
            _generate_remaining_stages_background(
                neo=neo,
                pg=pg,
                can_do_id=can_do_id,
                lesson_id=lesson_id,
                version=version,
                metalanguage=metalanguage,
                model=model,
                timeout=timeout,
                prelesson_kit=prelesson_kit,
                fast_model_override=fast_model_override,
                cando_input=cando_input,
                plan=plan,
                content_cards=content_cards_dict,
                llm_call_main=llm_call_main,
                llm_call_fast=llm_call_fast,
                kit_context=kit_context,
                kit_requirements=kit_requirements,
                profile_context=profile_context,
                progress_callback=progress_callback,
            )
        )
        
        total_time = time.time() - start_time
        print(f"[COMPILE] {can_do_id}: ✅ CONTENT STAGE COMPLETE in {total_time:.1f}s - background generation started")
        print(f"[COMPILE] {can_do_id}: Lesson ID: {lesson_id}, Version: {version}")
        
        final_result = {"lesson_id": lesson_id, "version": version, "lesson": lesson_json, "incremental": True}
        if kit_usage_report:
            final_result["prelesson_kit_usage"] = kit_usage_report
        
        # Emit content_ready event via progress callback (with lesson data)
        if progress_callback:
            progress_callback({
                "step": "content_ready",
                "progress": 50,
                "message": "Content stage ready!",
                "event": "content_ready",
                "lesson_id": lesson_id,
                "version": version,
                "lesson": lesson_json  # Include full lesson data
            })
        
        return final_result
    
    # ======================================================================================
    # STAGE 1: CONTENT - Generate Objective, Vocabulary, Grammar, Formulaic Expressions, Dialogue, Culture
    # ======================================================================================
    if progress_callback:
        progress_callback({"stage": "content", "progress": 15, "message": "Generating Content stage...", "substep": "planning"})
    
    logger.info("Generating Content stage", extra={"can_do_id": can_do_id, "stage": "content"})
    content_start = time.time()
    print(f"[COMPILE] {can_do_id}: Starting Content stage generation at {time.strftime('%H:%M:%S')}")
    
    # Create a progress callback wrapper for content stage
    def content_progress_callback(card_name: str, progress_pct: int):
        """Helper to send progress updates for individual content cards"""
        if progress_callback:
            base_progress = 15  # Start after plan
            card_progress = int(base_progress + (progress_pct * 0.15))  # Content stage is ~15% of total
            progress_callback({
                "stage": "content",
                "progress": card_progress,
                "message": f"Generating {card_name}...",
                "substep": card_name.lower().replace(" ", "_")
            })
    
    content_cards = await pipeline.gen_content_stage(
        llm_call_main,
        llm_call_fast,
        metalanguage,
        cando_input,
        plan,
        max_repair=2,  # Allow auto-fix + 2 repair attempts
        kit_context=kit_context,
        profile_context=profile_context,  # Include profile context
        kit_requirements=kit_requirements,
        progress_callback=content_progress_callback,  # Pass progress callback
    )
    
    content_duration = time.time() - content_start
    print(f"[COMPILE] {can_do_id}: Content stage generated in {content_duration:.1f}s")
    logger.info("Content stage generated", extra={"can_do_id": can_do_id, "stage": "content", "duration": content_duration})
    
    if progress_callback:
        progress_callback({"stage": "content", "progress": 30, "message": "Content stage complete!", "substep": "complete"})
    
    # ======================================================================================
    # STAGE 2: COMPREHENSION - Generate Reading, Comprehension Exercises, AI Comprehension Tutor
    # Reading needs dialogue, so generate it first, then comprehension exercises and tutor in parallel
    # ======================================================================================
    if progress_callback:
        progress_callback({"stage": "comprehension", "progress": 50, "message": "Generating Comprehension stage..."})
    
    logger.info("Generating Comprehension stage", extra={"can_do_id": can_do_id, "stage": "comprehension"})
    comprehension_start = time.time()
    print(f"[COMPILE] {can_do_id}: Starting Comprehension stage generation at {time.strftime('%H:%M:%S')}")
    
    # Generate reading first (needs dialogue)
    reading = await asyncio.to_thread(
        pipeline.gen_reading_card,
        llm_call_fast,
        metalanguage,
        cando_input,
        plan,
        content_cards["lesson_dialogue"],
        max_repair=0,
        kit_context=kit_context,
        profile_context=profile_context,  # Include profile context
        kit_requirements=kit_requirements,
    )
    
    # Generate comprehension exercises and AI tutor in parallel
    comprehension_cards = await pipeline.gen_comprehension_stage(
        llm_call_main,
        llm_call_fast,
        metalanguage,
        plan,
        content_cards,
        reading=reading,
        max_repair=0,
        kit_context=kit_context,
        profile_context=profile_context,  # Include profile context
        kit_requirements=kit_requirements,
    )
    
    comprehension_duration = time.time() - comprehension_start
    print(f"[COMPILE] {can_do_id}: Comprehension stage generated in {comprehension_duration:.1f}s")
    logger.info("Comprehension stage generated", extra={"can_do_id": can_do_id, "stage": "comprehension", "duration": comprehension_duration})
    
    if progress_callback:
        progress_callback({
            "step": "comprehension_ready",
            "progress": 60,
            "message": "Comprehension stage complete!",
            "event": "comprehension_ready"
        })
    
    # ======================================================================================
    # STAGE 3: PRODUCTION - Generate Guided Dialogue, Production Exercises, AI Production Evaluator
    # ======================================================================================
    if progress_callback:
        progress_callback({"stage": "production", "progress": 65, "message": "Generating Production stage...", "substep": "guided_dialogue"})
    
    logger.info("Generating Production stage", extra={"can_do_id": can_do_id, "stage": "production"})
    production_start = time.time()
    print(f"[COMPILE] {can_do_id}: Starting Production stage generation at {time.strftime('%H:%M:%S')}")
    
    production_cards = await pipeline.gen_production_stage(
        llm_call_main,
        llm_call_fast,
        metalanguage,
        plan,
        content_cards,
        comprehension_cards=comprehension_cards,
        max_repair=0,
        kit_context=kit_context,
        profile_context=profile_context,  # Include profile context
        kit_requirements=kit_requirements,
    )
    
    production_duration = time.time() - production_start
    print(f"[COMPILE] {can_do_id}: Production stage generated in {production_duration:.1f}s")
    logger.info("Production stage generated", extra={"can_do_id": can_do_id, "stage": "production", "duration": production_duration})
    
    if progress_callback:
        progress_callback({
            "step": "production_ready",
            "progress": 80,
            "message": "Production stage complete!",
            "event": "production_ready"
        })
    
    # ======================================================================================
    # STAGE 4: INTERACTION - Generate Interactive Dialogue, Interaction Activities, AI Scenario Manager
    # ======================================================================================
    if progress_callback:
        progress_callback({"stage": "interaction", "progress": 85, "message": "Generating Interaction stage...", "substep": "interactive_dialogue"})
    
    logger.info("Generating Interaction stage", extra={"can_do_id": can_do_id, "stage": "interaction"})
    interaction_start = time.time()
    print(f"[COMPILE] {can_do_id}: Starting Interaction stage generation at {time.strftime('%H:%M:%S')}")
    
    interaction_cards = await pipeline.gen_interaction_stage(
        llm_call_main,
        llm_call_fast,
        metalanguage,
        plan,
        content_cards,
        comprehension_cards=comprehension_cards,
        production_cards=production_cards,
        max_repair=0,
        kit_context=kit_context,
        profile_context=profile_context,  # Include profile context
        kit_requirements=kit_requirements,
    )
    
    interaction_duration = time.time() - interaction_start
    print(f"[COMPILE] {can_do_id}: Interaction stage generated in {interaction_duration:.1f}s")
    logger.info("Interaction stage generated", extra={"can_do_id": can_do_id, "stage": "interaction", "duration": interaction_duration})
    
    if progress_callback:
        progress_callback({
            "step": "interaction_ready",
            "progress": 95,
            "message": "Interaction stage complete!",
            "event": "interaction_ready"
        })
    
    logger.info("All stages generated", extra={"can_do_id": can_do_id, "step": "assembly"})

    # Progress: Finalizing
    if progress_callback:
        progress_callback({"step": "finalizing", "progress": 95, "message": "Assembling lesson..."})

    root = pipeline.assemble_lesson(
        metalanguage,
        cando_input,
        plan,
        content_cards["objective"],
        content_cards["words"],
        content_cards["grammar_patterns"],
        content_cards["lesson_dialogue"],
        comprehension_cards["reading_comprehension"],
        production_cards["guided_dialogue"],
        exercises=None,  # Legacy - use comprehension_exercises or production_exercises
        culture=content_cards["cultural_explanation"],
        drills=None,  # Legacy
        # New stage-organized cards
        formulaic_expressions=content_cards.get("formulaic_expressions"),
        comprehension_exercises=comprehension_cards.get("comprehension_exercises"),
        ai_comprehension_tutor=comprehension_cards.get("ai_comprehension_tutor"),
        production_exercises=production_cards.get("production_exercises"),
        ai_production_evaluator=production_cards.get("ai_production_evaluator"),
        interactive_dialogue=interaction_cards.get("interactive_dialogue"),
        interaction_activities=interaction_cards.get("interaction_activities"),
        ai_scenario_manager=interaction_cards.get("ai_scenario_manager"),
        lesson_id=f"canDo_{can_do_id}_v1",
    )

    logger.debug("Starting serialization", extra={"can_do_id": can_do_id})
    # Convert Pydantic model to dict, ensuring nested models are also converted
    lesson_json = root.model_dump(mode='json')
    # Debug: Log ReadingCard structure if present
    if "reading_comprehension" in lesson_json and lesson_json["reading_comprehension"]:
        _reading_card = lesson_json["reading_comprehension"]
        logger.debug(
            "ReadingCard in serialized JSON",
            extra={
                "can_do_id": can_do_id,
                "has_title": "title" in _reading_card,
                "has_reading": "reading" in _reading_card,
            },
        )
    await _enrich_grammar_neo4j_ids(neo, lesson_json)
    
    # Note: Entity linking removed - we use plan-based generation which doesn't require
    # extracting and linking entities from dialogue/reading text
    
    # Track pre-lesson kit usage if kit was provided
    kit_usage_report = None
    if prelesson_kit:
        try:
            kit_usage_report = _track_kit_usage(lesson_json, prelesson_kit)
            logger.info(
                "prelesson_kit_usage_tracked",
                extra={
                    "can_do_id": can_do_id,
                    "words_used": kit_usage_report.get("words", {}).get("count", 0),
                    "words_required": kit_usage_report.get("words", {}).get("required", 0),
                    "grammar_used": kit_usage_report.get("grammar", {}).get("count", 0),
                    "grammar_required": kit_usage_report.get("grammar", {}).get("required", 0),
                    "phrases_used": kit_usage_report.get("phrases", {}).get("count", 0),
                    "phrases_required": kit_usage_report.get("phrases", {}).get("required", 0),
                    "all_requirements_met": kit_usage_report.get("all_requirements_met", False),
                    "usage_percentage": kit_usage_report.get("usage_percentage", 0.0),
                }
            )
            
            # Warn if requirements not met
            if not kit_usage_report.get("all_requirements_met", False):
                logger.warning(
                    "prelesson_kit_requirements_not_met",
                    extra={
                        "can_do_id": can_do_id,
                        "words_meets": kit_usage_report.get("words", {}).get("meets_requirement", False),
                        "grammar_meets": kit_usage_report.get("grammar", {}).get("meets_requirement", False),
                        "phrases_meets": kit_usage_report.get("phrases", {}).get("meets_requirement", False),
                    }
                )
        except Exception as e:
            logger.warning(
                "prelesson_kit_usage_tracking_failed",
                extra={"can_do_id": can_do_id, "error": str(e)}
            )
            # Continue compilation even if tracking fails

    # Optional: image generation can be slow. Default OFF (enable explicitly).
    # - If disabled, lesson still contains image prompts; UI shows fallback placeholders.
    images_generated = 0
    generate_images = os.getenv("CANDO_GENERATE_IMAGES", "0") == "1"
    if generate_images and os.getenv("GEMINI_API_KEY"):
        try:
            images_generated, _ = await asyncio.to_thread(
                ensure_image_paths_for_lesson,
                lesson_json,
                can_do_id=can_do_id,
            )
            if images_generated:
                logger.info(
                    "Generated %s lesson images for %s", images_generated, can_do_id
                )
        except Exception as exc:
            logger.warning("Image generation skipped for %s: %s", can_do_id, exc)

    # Persist in lessons/lesson_versions tables (JSONB as lesson_plan)
    # Upsert lesson
    result = await pg.execute(text("SELECT id FROM lessons WHERE can_do_id = :cid LIMIT 1"), {"cid": can_do_id})
    row = result.first()
    if row:
        lesson_id = int(row[0])
    else:
        ins = await pg.execute(text("INSERT INTO lessons (can_do_id, status) VALUES (:cid, 'draft') RETURNING id"), {"cid": can_do_id})
        lesson_id = int(ins.first()[0])
    # Next version
    ver_row = (await pg.execute(text("SELECT COALESCE(MAX(version),0) FROM lesson_versions WHERE lesson_id=:lid"), {"lid": lesson_id})).first()
    next_ver = int(ver_row[0]) + 1
    
    # Store pre-lesson kit usage in lesson metadata if available
    if kit_usage_report and isinstance(lesson_json, dict) and "lesson" in lesson_json:
        if "meta" not in lesson_json["lesson"]:
            lesson_json["lesson"]["meta"] = {}
        lesson_json["lesson"]["meta"]["prelesson_kit_usage"] = kit_usage_report
        lesson_json["lesson"]["meta"]["prelesson_kit_available"] = True
    
    await pg.execute(
        text("INSERT INTO lesson_versions (lesson_id, version, lesson_plan) VALUES (:lid, :ver, :plan)"),
        {"lid": lesson_id, "ver": next_ver, "plan": json.dumps(lesson_json, ensure_ascii=False)},
    )
    await pg.commit()
    
    # Progress: Complete
    if progress_callback:
        progress_callback({"step": "complete", "progress": 100, "message": "Lesson compiled successfully!"})
    
    total_time = time.time() - start_time
    print(f"[COMPILE] {can_do_id}: ✅ COMPILATION COMPLETE in {total_time:.1f}s ({total_time/60:.1f} minutes)")
    print(f"[COMPILE] {can_do_id}: Lesson ID: {lesson_id}, Version: {next_ver}")
    logger.info(
        "compile_lessonroot() complete",
        extra={
            "can_do_id": can_do_id,
            "total_duration_seconds": round(total_time, 2),
            "lesson_id": lesson_id,
            "version": next_ver,
        },
    )

    final_result = {"lesson_id": lesson_id, "version": next_ver, "lesson": lesson_json}
    if kit_usage_report:
        final_result["prelesson_kit_usage"] = kit_usage_report
    return final_result


async def _update_lesson_stage_status_in_db(
    pg: PgSession,
    lesson_id: int,
    version: int,
    stage_name: str,
    status: str,
) -> None:
    """
    Update only the generation status for a stage without updating the cards.
    
    Args:
        pg: PostgreSQL session
        lesson_id: Lesson ID
        version: Lesson version
        stage_name: Name of the stage (e.g., "comprehension", "production", "interaction")
        status: Status to set (e.g., "generating", "complete", "failed: <message>")
    """
    import json
    from sqlalchemy import text
    
    # Update status atomically using JSONB operators (no read-modify-write race condition)
    status_json = json.dumps({stage_name: status}, ensure_ascii=False)
    
    result = await pg.execute(
        text("""
            UPDATE lesson_versions 
            SET lesson_plan = jsonb_set(
                COALESCE(lesson_plan, '{}'::jsonb),
                '{lesson,meta,generation_status}',
                COALESCE(lesson_plan->'lesson'->'meta'->'generation_status', '{}'::jsonb) || :status::jsonb
            )
            WHERE lesson_id = :lid AND version = :ver
            RETURNING lesson_plan
        """),
        {"lid": lesson_id, "ver": version, "status": status_json}
    )
    row = result.first()
    if not row:
        raise ValueError(f"Lesson {lesson_id} version {version} not found")
    
    await pg.commit()


async def _update_lesson_stage_in_db(
    pg: PgSession,
    lesson_id: int,
    version: int,
    stage_name: str,
    stage_data: Dict[str, Any],
) -> None:
    """
    Update a specific stage in an existing lesson by merging stage data into lesson_plan JSONB.
    
    Args:
        pg: PostgreSQL session
        lesson_id: Lesson ID
        version: Lesson version
        stage_name: Name of the stage (e.g., "comprehension", "production", "interaction")
        stage_data: Stage data to merge into lesson
    """
    import json
    from sqlalchemy import text
    
    # Fetch current lesson
    result = await pg.execute(
        text("SELECT lesson_plan FROM lesson_versions WHERE lesson_id = :lid AND version = :ver"),
        {"lid": lesson_id, "ver": version}
    )
    row = result.first()
    if not row:
        raise ValueError(f"Lesson {lesson_id} version {version} not found")
    
    current_lesson = json.loads(row[0]) if isinstance(row[0], str) else row[0]
    
    # Ensure lesson structure exists (LessonRoot format: {lesson: {meta: {...}, cards: {...}}})
    if "lesson" not in current_lesson:
        current_lesson["lesson"] = {}
    if "cards" not in current_lesson["lesson"]:
        current_lesson["lesson"]["cards"] = {}
    if "meta" not in current_lesson["lesson"]:
        current_lesson["lesson"]["meta"] = {}
    if "generation_status" not in current_lesson["lesson"]["meta"]:
        current_lesson["lesson"]["meta"]["generation_status"] = {}
    
    # Helper function to convert Pydantic models to dicts
    def _to_dict(obj):
        """Convert Pydantic model or dict to dict for JSON serialization."""
        if obj is None:
            return None
        # Check if it's a Pydantic model (has model_dump method)
        if hasattr(obj, 'model_dump'):
            return obj.model_dump()
        # Check if it's a Pydantic v1 model (has dict method)
        elif hasattr(obj, 'dict'):
            return obj.dict()
        # Already a dict or other JSON-serializable type
        elif isinstance(obj, dict):
            return {k: _to_dict(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [_to_dict(item) for item in obj]
        else:
            return obj
    
    # Map stage names to card keys, converting Pydantic models to dicts
    stage_to_cards = {
        "comprehension": {
            "reading_comprehension": _to_dict(stage_data.get("reading_comprehension")),
            "comprehension_exercises": _to_dict(stage_data.get("comprehension_exercises")),
            "ai_comprehension_tutor": _to_dict(stage_data.get("ai_comprehension_tutor")),
        },
        "production": {
            "guided_dialogue": _to_dict(stage_data.get("guided_dialogue")),
            "production_exercises": _to_dict(stage_data.get("production_exercises")),
            "ai_production_evaluator": _to_dict(stage_data.get("ai_production_evaluator")),
        },
        "interaction": {
            "interactive_dialogue": _to_dict(stage_data.get("interactive_dialogue")),
            "interaction_activities": _to_dict(stage_data.get("interaction_activities")),
            "ai_scenario_manager": _to_dict(stage_data.get("ai_scenario_manager")),
        },
    }
    
    # Merge stage cards into lesson.cards (not root-level cards)
    if stage_name in stage_to_cards:
        for card_key, card_data in stage_to_cards[stage_name].items():
            if card_data is not None:
                current_lesson["lesson"]["cards"][card_key] = card_data
    
    # Update generation status in metadata
    current_lesson["lesson"]["meta"]["generation_status"][stage_name] = "complete"
    
    # Clear any previous errors for this stage
    if "errors" in current_lesson["lesson"]["meta"] and stage_name in current_lesson["lesson"]["meta"]["errors"]:
        del current_lesson["lesson"]["meta"]["errors"][stage_name]
    
    # Update in database using JSONB merge for atomic updates
    # This prevents race conditions when multiple stages update simultaneously
    # Use PostgreSQL's jsonb_set and || operators for atomic updates
    # Path must be {lesson,cards} not {cards} to match LessonRoot structure
    cards_json = json.dumps(stage_to_cards.get(stage_name, {}), ensure_ascii=False)
    status_json = json.dumps({stage_name: "complete"}, ensure_ascii=False)
    
    # Use bindparam to properly handle JSONB casting
    from sqlalchemy import bindparam
    
    await pg.execute(
        text("""
            UPDATE lesson_versions 
            SET lesson_plan = 
                jsonb_set(
                    jsonb_set(
                        COALESCE(lesson_plan, '{}'::jsonb),
                        '{lesson,cards}',
                        COALESCE(lesson_plan->'lesson'->'cards', '{}'::jsonb) || CAST(:cards AS jsonb)
                    ),
                    '{lesson,meta,generation_status}',
                    COALESCE(lesson_plan->'lesson'->'meta'->'generation_status', '{}'::jsonb) || CAST(:status AS jsonb)
                )
            WHERE lesson_id = :lid AND version = :ver
        """),
        {
            "lid": lesson_id,
            "ver": version,
            "cards": cards_json,
            "status": status_json
        }
    )
    await pg.commit()
    
    logger.info(
        "lesson_stage_updated",
        extra={"lesson_id": lesson_id, "version": version, "stage": stage_name}
    )


