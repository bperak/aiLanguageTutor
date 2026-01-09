"""
Profile Building Service

Handles chatbot-based profile collection and data extraction using AI.
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path
import structlog
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from app.models.database_models import User, UserProfile, ConversationSession, ConversationMessage
from app.schemas.profile import ProfileData, PreviousKnowledge, LearningExperience, UsageContext
from app.services.ai_chat_service import AIChatService
from app.core.config import settings
from app.utils.json_helpers import parse_json_object

logger = structlog.get_logger()


def _looks_like_missing_table_error(exc: Exception, table_name: str) -> bool:
    """
    Best-effort detection for missing-table errors across async drivers.

    Args:
        exc: Raised exception.
        table_name: Table name to check for in the error message.

    Returns:
        bool: True if this looks like a "relation does not exist" error.
    """

    msg = str(exc).lower()
    t = table_name.lower()
    return ("does not exist" in msg or "undefinedtableerror" in msg) and t in msg


async def _ensure_user_profiles_table_exists(db: AsyncSession) -> None:
    """
    Ensure `user_profiles` exists.

    Reason: production DB volumes are persistent; if migrations were not applied,
    profile build should self-heal rather than erroring for end users.
    """

    from sqlalchemy import text

    # asyncpg rejects multi-statement prepared statements, so execute separately.
    await db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS user_profiles (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
                previous_knowledge JSONB DEFAULT '{}',
                learning_experiences JSONB DEFAULT '{}',
                usage_context JSONB DEFAULT '{}',
                learning_goals JSONB DEFAULT '[]',
                additional_notes TEXT,
                extraction_response JSONB DEFAULT NULL,
                profile_building_conversation_id UUID REFERENCES conversation_sessions(id) ON DELETE SET NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
            """
        )
    )
    await db.execute(text("CREATE INDEX IF NOT EXISTS idx_user_profiles_user_id ON user_profiles(user_id)"))
    await db.execute(text("CREATE INDEX IF NOT EXISTS idx_user_profiles_created_at ON user_profiles(created_at DESC)"))
    await db.commit()


class ProfileBuildingService:
    """Service for building user profiles via chatbot conversation."""
    
    def __init__(self):
        self.ai_service = AIChatService()
    
    async def check_profile_completion(
        self,
        db: AsyncSession,
        user_id: uuid.UUID
    ) -> Dict[str, bool]:
        """
        Check if user has completed or skipped profile building.
        
        Returns:
            dict with 'completed' and 'skipped' boolean flags
        """
        try:
            # Check if UserProfile exists (indicates profile is completed)
            # Use raw SQL to avoid model issues if table doesn't exist.
            #
            # Reason: do NOT unconditionally call `db.rollback()` here. This method is
            # often invoked mid-request (e.g. by `/api/v1/home/status`). A rollback
            # expires ORM instances in the session (including `current_user`), and a
            # subsequent attribute access can trigger an implicit reload that fails
            # under AsyncSession with `MissingGreenlet`.
            from sqlalchemy import text
            try:
                try:
                    result = await db.execute(
                        text("SELECT id FROM user_profiles WHERE user_id = :user_id LIMIT 1"),
                        {"user_id": str(user_id)},
                    )
                except Exception as e:  # noqa: BLE001
                    # If the session is in a failed transaction state, rollback and retry once.
                    if "PendingRollback" in type(e).__name__ or "Rollback" in type(e).__name__:
                        await db.rollback()
                        result = await db.execute(
                            text("SELECT id FROM user_profiles WHERE user_id = :user_id LIMIT 1"),
                            {"user_id": str(user_id)},
                        )
                    else:
                        raise
                profile = result.first()
                completed = profile is not None
            except Exception:
                # Table doesn't exist, profile not completed
                completed = False
            
            return {
                "completed": completed,
                "skipped": False
            }
        except Exception as e:
            # If any error occurs, rollback and return default
            try:
                await db.rollback()
            except:
                pass
            logger.warning("Error checking profile completion", user_id=str(user_id), error=str(e))
            return {
                "completed": False,
                "skipped": False
            }
    
    def get_profile_building_prompt(
        self,
        user_native_language: str = "en",
        user_name: Optional[str] = None
    ) -> str:
        """
        Generate system prompt for profile building chat.
        
        Args:
            user_native_language: ISO language code for user's native language
            user_name: Optional user name for personalization
            
        Returns:
            System prompt string
        """
        try:
            # Load prompt template - go from services/ to app/prompts/
            base_dir = Path(__file__).parent.parent  # Go from services/ to app/
            prompt_path = base_dir / "prompts" / "profile_building_prompt.txt"
            with open(prompt_path, "r", encoding="utf-8") as f:
                prompt_template = f.read()
            
            # Personalize if user name provided
            if user_name:
                prompt_template = prompt_template.replace(
                    "{user_name}",
                    user_name
                ).replace(
                    "{native_language}",
                    user_native_language
                )
            
            return prompt_template
        except Exception as e:
            logger.error("failed_to_load_profile_prompt", error=str(e))
            # Fallback prompt
            return f"""You are a friendly AI language tutor. Introduce yourself to the learner and have a natural conversation to learn about:

1. Their learning goals
2. Previous knowledge and experience
3. Learning experiences and preferences
4. Where and when they want to use the target language

Speak in {user_native_language} and be conversational. Extract all this information into a structured format at the end."""
    
    async def extract_profile_data(
        self,
        conversation_messages: List[Dict[str, Any]]
    ) -> Tuple[ProfileData, Dict[str, Any]]:
        """
        Extract structured profile data from conversation messages using AI.
        
        Args:
            conversation_messages: List of message dicts with 'role' and 'content'
            
        Returns:
            Tuple of (Validated ProfileData object, extraction_response dict with raw AI response and metadata)
            
        Raises:
            ValueError: If conversation is empty or JSON parsing fails
            Exception: For other extraction errors
        """
        # Validate input
        if not conversation_messages or len(conversation_messages) == 0:
            logger.warning("extract_profile_data_empty_conversation")
            raise ValueError("Conversation is empty. Please have a conversation before extracting profile data.")
        
        # Format conversation for AI
        conversation_text = "\n".join([
            f"{msg.get('role', 'unknown')}: {msg.get('content', '')}"
            for msg in conversation_messages
        ])
        
        # Log conversation length for debugging
        logger.info(
            "extract_profile_data_starting",
            message_count=len(conversation_messages),
            conversation_length=len(conversation_text)
        )
        
        # Create extraction prompt
        extraction_prompt = f"""Extract structured profile data from this conversation:

{conversation_text}

Extract the following information into a JSON object:
- learning_goals: List of learning goals mentioned
- previous_knowledge: Object with has_experience, experience_level, years_studying, formal_classes, self_study, specific_areas_known, specific_areas_unknown
- learning_experiences: Object with preferred_methods, methods_that_worked, methods_that_didnt_work, learning_style, study_schedule, motivation_level, challenges_faced, grammar_focus_areas, grammar_challenges, preferred_exercise_types, interaction_preferences, feedback_preferences, error_tolerance
- usage_context: Object with contexts, urgency, specific_situations, target_date, register_preferences, formality_contexts, scenario_details
- current_level: Assessed learning stage - one of: beginner_1, beginner_2, intermediate_1, intermediate_2, advanced_1, advanced_2
  - beginner_1: Complete beginner, no prior experience
  - beginner_2: Can understand basic phrases, can introduce themselves
  - intermediate_1: Can handle simple conversations, can read/write simple texts
  - intermediate_2: Can understand main points, can express opinions on familiar topics
  - advanced_1: Can understand complex topics, can discuss abstract ideas
  - advanced_2: Near-native level, can use language effectively in professional/academic contexts
- vocabulary_domain_goals: List of vocabulary topics/domains (e.g., ["travel", "business", "daily_life"])
- vocabulary_known: List of objects with word, domain, level, mastery (if mentioned)
- vocabulary_learning_target: Number of words per milestone (if mentioned)
- vocabulary_level_preference: "current", "slightly_above", or "challenging" (if mentioned)
- grammar_progression_goals: List of grammar areas (e.g., ["particles", "verb_forms", "keigo"])
- grammar_known: List of objects with pattern, level, mastery, area (if mentioned)
- grammar_learning_target: Number of patterns per milestone (if mentioned)
- grammar_level_preference: "current", "slightly_above", or "challenging" (if mentioned)
- formulaic_expression_goals: List of expression contexts (e.g., ["greetings", "requests", "apologies"])
- expressions_known: List of objects with expression, context, level, register, mastery (if mentioned)
- expression_learning_target: Number of expressions per milestone (if mentioned)
- expression_level_preference: "current", "slightly_above", or "challenging" (if mentioned)
- cultural_interests: List of cultural topics (e.g., ["etiquette", "history", "pop culture"])
- cultural_background: User's cultural background (if mentioned)
- additional_notes: Any other relevant information

Return ONLY valid JSON matching the ProfileData schema."""
        
        # Use AI to extract data
        try:
            # Use system prompt to ensure JSON output
            system_prompt = """You are a data extraction assistant. Extract structured data from conversations.
Return ONLY valid JSON matching this schema:
{
  "learning_goals": ["string"],
  "previous_knowledge": {"has_experience": bool, "experience_level": "string", ...},
  "learning_experiences": {"preferred_methods": ["string"], ...},
  "usage_context": {"contexts": ["string"], ...},
  "current_level": "beginner_1|beginner_2|intermediate_1|intermediate_2|advanced_1|advanced_2",
  "additional_notes": "string"
}"""
            
            response = await self.ai_service.generate_reply(
                provider="openai",
                model="gpt-4.1",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": extraction_prompt}
                ],
                temperature=0.0  # Lower temperature for more structured output
            )
            
            # Log the raw response for debugging
            raw_content = response.get("content", "")
            logger.info(
                "extract_profile_data_ai_response",
                response_length=len(raw_content),
                response_preview=raw_content[:200] if raw_content else "EMPTY"
            )
            
            if not raw_content or not raw_content.strip():
                logger.error("extract_profile_data_empty_ai_response")
                raise ValueError("AI returned empty response. Please try again.")
            
            # Parse response
            extracted_data = raw_content
            if isinstance(extracted_data, str):
                extracted_data = parse_json_object(extracted_data)
            elif extracted_data is None:
                logger.error("extract_profile_data_none_response")
                raise ValueError("AI returned None response. Please try again.")
            elif not isinstance(extracted_data, dict):
                extracted_data = parse_json_object(str(extracted_data))
            
            # Log extracted data structure
            logger.info(
                "extract_profile_data_parsed",
                has_goals=bool(extracted_data.get("learning_goals")),
                has_previous_knowledge=bool(extracted_data.get("previous_knowledge")),
                has_learning_experiences=bool(extracted_data.get("learning_experiences")),
                has_usage_context=bool(extracted_data.get("usage_context"))
            )
            
            # Validate with Pydantic (with new fields)
            profile_data = ProfileData(
                learning_goals=extracted_data.get("learning_goals", []),
                previous_knowledge=PreviousKnowledge(**extracted_data.get("previous_knowledge", {})),
                learning_experiences=LearningExperience(**extracted_data.get("learning_experiences", {})),
                usage_context=UsageContext(**extracted_data.get("usage_context", {})),
                current_level=extracted_data.get("current_level"),
                additional_notes=extracted_data.get("additional_notes"),
                # New fields (optional, with defaults)
                vocabulary_domain_goals=extracted_data.get("vocabulary_domain_goals", []),
                vocabulary_known=extracted_data.get("vocabulary_known", []),
                vocabulary_learning_target=extracted_data.get("vocabulary_learning_target"),
                vocabulary_level_preference=extracted_data.get("vocabulary_level_preference"),
                grammar_progression_goals=extracted_data.get("grammar_progression_goals", []),
                grammar_known=extracted_data.get("grammar_known", []),
                grammar_learning_target=extracted_data.get("grammar_learning_target"),
                grammar_level_preference=extracted_data.get("grammar_level_preference"),
                formulaic_expression_goals=extracted_data.get("formulaic_expression_goals", []),
                expressions_known=extracted_data.get("expressions_known", []),
                expression_learning_target=extracted_data.get("expression_learning_target"),
                expression_level_preference=extracted_data.get("expression_level_preference"),
                cultural_interests=extracted_data.get("cultural_interests", []),
                cultural_background=extracted_data.get("cultural_background")
            )
            
            logger.info("extract_profile_data_success")
            
            # Build extraction response metadata for storage
            extraction_response = {
                "raw_ai_response": raw_content,
                "extracted_data": extracted_data,
                "model_used": "gpt-4.1",
                "provider": "openai",
                "extraction_timestamp": datetime.utcnow().isoformat(),
                "conversation_message_count": len(conversation_messages),
                "assessment": {
                    "has_goals": bool(extracted_data.get("learning_goals")),
                    "has_previous_knowledge": bool(extracted_data.get("previous_knowledge")),
                    "has_learning_experiences": bool(extracted_data.get("learning_experiences")),
                    "has_usage_context": bool(extracted_data.get("usage_context")),
                    "current_level_assessed": extracted_data.get("current_level"),
                }
            }
            
            return profile_data, extraction_response
            
        except ValueError as e:
            # JSON parsing errors - log with more detail
            logger.error(
                "profile_extraction_failed_json_parsing",
                error=str(e),
                error_type=type(e).__name__,
                conversation_length=len(conversation_text),
                message_count=len(conversation_messages)
            )
            # Re-raise to let caller handle it
            raise
        except Exception as e:
            # Other errors - log with full context
            import traceback
            logger.error(
                "profile_extraction_failed",
                error=str(e),
                error_type=type(e).__name__,
                conversation_length=len(conversation_text),
                message_count=len(conversation_messages),
                traceback=traceback.format_exc()
            )
            # Re-raise instead of returning empty ProfileData
            raise
    
    async def save_profile_data(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        profile_data: ProfileData,
        conversation_id: Optional[uuid.UUID] = None,
        extraction_response: Optional[Dict[str, Any]] = None
    ) -> UserProfile:
        """
        Save extracted profile data to database.
        
        Args:
            db: Database session
            user_id: User ID
            profile_data: Validated ProfileData object
            conversation_id: Optional conversation session ID
            extraction_response: Optional dict containing raw AI response and assessment metadata
            
        Returns:
            Created UserProfile object
        """
        # Check if profile already exists
        try:
            result = await db.execute(
                select(UserProfile).where(UserProfile.user_id == user_id)
            )
            existing_profile = result.scalar_one_or_none()
        except Exception as e:
            if _looks_like_missing_table_error(e, "user_profiles"):
                logger.warning("user_profiles_table_missing_auto_creating")
                await _ensure_user_profiles_table_exists(db)
                result = await db.execute(
                    select(UserProfile).where(UserProfile.user_id == user_id)
                )
                existing_profile = result.scalar_one_or_none()
            else:
                raise
        
        # Build learning_goals structure: include both goals list and new structure fields
        learning_goals_data = {
            "goals": profile_data.learning_goals,  # Keep backward compatibility
        }
        # Add new path-level structure fields if they exist
        if hasattr(profile_data, 'vocabulary_domain_goals') and profile_data.vocabulary_domain_goals:
            learning_goals_data["vocabulary_domain_goals"] = profile_data.vocabulary_domain_goals
        if hasattr(profile_data, 'vocabulary_known') and profile_data.vocabulary_known:
            learning_goals_data["vocabulary_known"] = [v.model_dump() if hasattr(v, 'model_dump') else v for v in profile_data.vocabulary_known]
        if hasattr(profile_data, 'vocabulary_learning_target') and profile_data.vocabulary_learning_target is not None:
            learning_goals_data["vocabulary_learning_target"] = profile_data.vocabulary_learning_target
        if hasattr(profile_data, 'vocabulary_level_preference') and profile_data.vocabulary_level_preference:
            learning_goals_data["vocabulary_level_preference"] = profile_data.vocabulary_level_preference
        if hasattr(profile_data, 'grammar_progression_goals') and profile_data.grammar_progression_goals:
            learning_goals_data["grammar_progression_goals"] = profile_data.grammar_progression_goals
        if hasattr(profile_data, 'grammar_known') and profile_data.grammar_known:
            learning_goals_data["grammar_known"] = [g.model_dump() if hasattr(g, 'model_dump') else g for g in profile_data.grammar_known]
        if hasattr(profile_data, 'grammar_learning_target') and profile_data.grammar_learning_target is not None:
            learning_goals_data["grammar_learning_target"] = profile_data.grammar_learning_target
        if hasattr(profile_data, 'grammar_level_preference') and profile_data.grammar_level_preference:
            learning_goals_data["grammar_level_preference"] = profile_data.grammar_level_preference
        if hasattr(profile_data, 'formulaic_expression_goals') and profile_data.formulaic_expression_goals:
            learning_goals_data["formulaic_expression_goals"] = profile_data.formulaic_expression_goals
        if hasattr(profile_data, 'expressions_known') and profile_data.expressions_known:
            learning_goals_data["expressions_known"] = [e.model_dump() if hasattr(e, 'model_dump') else e for e in profile_data.expressions_known]
        if hasattr(profile_data, 'expression_learning_target') and profile_data.expression_learning_target is not None:
            learning_goals_data["expression_learning_target"] = profile_data.expression_learning_target
        if hasattr(profile_data, 'expression_level_preference') and profile_data.expression_level_preference:
            learning_goals_data["expression_level_preference"] = profile_data.expression_level_preference
        if hasattr(profile_data, 'cultural_interests') and profile_data.cultural_interests:
            learning_goals_data["cultural_interests"] = profile_data.cultural_interests
        if hasattr(profile_data, 'cultural_background') and profile_data.cultural_background:
            learning_goals_data["cultural_background"] = profile_data.cultural_background
        
        profile_dict = {
            "user_id": user_id,
            "learning_goals": learning_goals_data if len(learning_goals_data) > 1 else profile_data.learning_goals,  # Use dict if new fields exist, else use list for backward compatibility
            "previous_knowledge": profile_data.previous_knowledge.model_dump(),
            "learning_experiences": profile_data.learning_experiences.model_dump(),
            "usage_context": profile_data.usage_context.model_dump(),
            "additional_notes": profile_data.additional_notes,
            "extraction_response": extraction_response,  # Store AI extraction response and assessment
            "profile_building_conversation_id": conversation_id,
            "updated_at": datetime.utcnow()
        }
        
        # Also update User.current_level if provided
        if profile_data.current_level:
            from sqlalchemy import update
            from app.models.database_models import User
            await db.execute(
                update(User)
                .where(User.id == user_id)
                .values(current_level=profile_data.current_level)
            )
            await db.commit()
        
        if existing_profile:
            # Update existing profile
            for key, value in profile_dict.items():
                setattr(existing_profile, key, value)
            await db.commit()
            await db.refresh(existing_profile)
            return existing_profile
        else:
            # Create new profile
            profile_dict["created_at"] = datetime.utcnow()
            new_profile = UserProfile(**profile_dict)
            db.add(new_profile)
            await db.commit()
            await db.refresh(new_profile)
            return new_profile
    
    async def mark_profile_complete(
        self,
        db: AsyncSession,
        user_id: uuid.UUID
    ) -> None:
        """Mark user profile as completed."""
        # Profile is marked complete when UserProfile is created
        # This method is kept for API compatibility but doesn't need to do anything
        # since completion is determined by UserProfile existence
        pass
    
    async def mark_profile_skipped(
        self,
        db: AsyncSession,
        user_id: uuid.UUID
    ) -> None:
        """Mark user profile as skipped."""
        # Skipped status is not currently tracked in the database
        # This method is kept for API compatibility
        pass


# Singleton instance
profile_building_service = ProfileBuildingService()

