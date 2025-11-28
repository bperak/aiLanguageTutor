"""
Profile Building Service

Handles chatbot-based profile collection and data extraction using AI.
"""

from typing import List, Dict, Any, Optional
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

logger = structlog.get_logger()


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
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            return {"completed": False, "skipped": False}
        
        return {
            "completed": user.profile_completed or False,
            "skipped": user.profile_skipped or False
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
    ) -> ProfileData:
        """
        Extract structured profile data from conversation messages using AI.
        
        Args:
            conversation_messages: List of message dicts with 'role' and 'content'
            
        Returns:
            Validated ProfileData object
        """
        # Format conversation for AI
        conversation_text = "\n".join([
            f"{msg.get('role', 'unknown')}: {msg.get('content', '')}"
            for msg in conversation_messages
        ])
        
        # Create extraction prompt
        extraction_prompt = f"""Extract structured profile data from this conversation:

{conversation_text}

Extract the following information into a JSON object:
- learning_goals: List of learning goals mentioned
- previous_knowledge: Object with has_experience, experience_level, years_studying, formal_classes, self_study, specific_areas_known, specific_areas_unknown
- learning_experiences: Object with preferred_methods, methods_that_worked, methods_that_didnt_work, learning_style, study_schedule, motivation_level, challenges_faced
- usage_context: Object with contexts, urgency, specific_situations, target_date
- current_level: Assessed learning stage - one of: beginner_1, beginner_2, intermediate_1, intermediate_2, advanced_1, advanced_2
  - beginner_1: Complete beginner, no prior experience
  - beginner_2: Can understand basic phrases, can introduce themselves
  - intermediate_1: Can handle simple conversations, can read/write simple texts
  - intermediate_2: Can understand main points, can express opinions on familiar topics
  - advanced_1: Can understand complex topics, can discuss abstract ideas
  - advanced_2: Near-native level, can use language effectively in professional/academic contexts
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
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": extraction_prompt}
                ],
                temperature=0.0  # Lower temperature for more structured output
            )
            
            # Parse response
            extracted_data = response.get("content", {})
            if isinstance(extracted_data, str):
                import json
                extracted_data = json.loads(extracted_data)
            
            # Validate with Pydantic
            profile_data = ProfileData(
                learning_goals=extracted_data.get("learning_goals", []),
                previous_knowledge=PreviousKnowledge(**extracted_data.get("previous_knowledge", {})),
                learning_experiences=LearningExperience(**extracted_data.get("learning_experiences", {})),
                usage_context=UsageContext(**extracted_data.get("usage_context", {})),
                current_level=extracted_data.get("current_level"),
                additional_notes=extracted_data.get("additional_notes")
            )
            
            return profile_data
            
        except Exception as e:
            logger.error("profile_extraction_failed", error=str(e))
            # Return default ProfileData on failure
            return ProfileData()
    
    async def save_profile_data(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        profile_data: ProfileData,
        conversation_id: Optional[uuid.UUID] = None
    ) -> UserProfile:
        """
        Save extracted profile data to database.
        
        Args:
            db: Database session
            user_id: User ID
            profile_data: Validated ProfileData object
            conversation_id: Optional conversation session ID
            
        Returns:
            Created UserProfile object
        """
        # Check if profile already exists
        result = await db.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )
        existing_profile = result.scalar_one_or_none()
        
        profile_dict = {
            "user_id": user_id,
            "learning_goals": profile_data.learning_goals,
            "previous_knowledge": profile_data.previous_knowledge.model_dump(),
            "learning_experiences": profile_data.learning_experiences.model_dump(),
            "usage_context": profile_data.usage_context.model_dump(),
            "additional_notes": profile_data.additional_notes,
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
        await db.execute(
            update(User)
            .where(User.id == user_id)
            .values(
                profile_completed=True,
                profile_completed_at=datetime.utcnow()
            )
        )
        await db.commit()
    
    async def mark_profile_skipped(
        self,
        db: AsyncSession,
        user_id: uuid.UUID
    ) -> None:
        """Mark user profile as skipped."""
        await db.execute(
            update(User)
            .where(User.id == user_id)
            .values(profile_skipped=True)
        )
        await db.commit()


# Singleton instance
profile_building_service = ProfileBuildingService()

