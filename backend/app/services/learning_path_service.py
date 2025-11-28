"""
Learning Path Generation Service

Generates personalized learning paths from user profiles with CanDo descriptor integration.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import structlog
import uuid
import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from neo4j import AsyncSession as Neo4jSession

from app.models.database_models import User, UserProfile, LearningPath
from app.schemas.profile import (
    LearningPathData, LearningPathStep, LearningPathMilestone, LearningPathProgress
)
from app.services.ai_chat_service import AIChatService
from app.core.config import settings

logger = structlog.get_logger()


class LearningPathService:
    """Service for generating and managing personalized learning paths."""
    
    def __init__(self):
        self.ai_service = AIChatService()
    
    def map_level_to_cefr(self, level: Optional[str]) -> Optional[str]:
        """
        Map custom learning stage to CEFR level for CanDo descriptor queries.
        
        Args:
            level: Custom level (beginner_1, beginner_2, intermediate_1, intermediate_2, advanced_1, advanced_2)
            
        Returns:
            CEFR level (A1, A2, B1, B2, C1, C2) or None
        """
        if not level:
            return None
        
        mapping = {
            "beginner_1": "A1",
            "beginner_2": "A2",
            "intermediate_1": "B1",
            "intermediate_2": "B2",
            "advanced_1": "C1",
            "advanced_2": "C2"
        }
        
        return mapping.get(level.lower())
    
    async def fetch_cando_descriptors(
        self,
        neo4j_session: Neo4jSession,
        level: Optional[str] = None,
        topic: Optional[str] = None,
        limit: int = 200
    ) -> List[Dict[str, Any]]:
        """
        Fetch CanDo descriptors from Neo4j.
        
        Args:
            neo4j_session: Neo4j session
            level: Optional CEFR level filter (A1, A2, B1, B2, C1, C2)
            topic: Optional topic filter
            limit: Maximum number of descriptors to return
            
        Returns:
            List of CanDo descriptor dictionaries
        """
        try:
            query = """
            MATCH (c:CanDoDescriptor)
            WHERE ($level IS NULL OR toString(c.level) = $level)
              AND ($topic IS NULL OR toString(c.primaryTopic) CONTAINS $topic)
            RETURN c.uid AS uid, 
                   c.primaryTopic AS primaryTopic,
                   coalesce(toString(c.primaryTopicEn), toString(c.primaryTopic)) AS primaryTopicEn,
                   toString(c.level) AS level, 
                   toString(c.type) AS type, 
                   toString(c.skillDomain) AS skillDomain,
                   coalesce(toString(c.descriptionEn), toString(c.description)) AS descriptionEn,
                   toString(c.descriptionJa) AS descriptionJa,
                   coalesce(toString(c.source), 'JFまるごと') AS source
            ORDER BY toString(c.level) ASC, toString(c.primaryTopic) ASC
            LIMIT $limit
            """
            result = await neo4j_session.run(query, level=level, topic=topic, limit=limit)
            items: List[Dict[str, Any]] = [dict(r) async for r in result]
            return items
        except Exception as e:
            logger.error("failed_to_fetch_cando_descriptors", error=str(e), level=level, topic=topic)
            return []
    
    async def generate_learning_path(
        self,
        db: AsyncSession,
        neo4j_session: Neo4jSession,
        user_id: uuid.UUID,
        profile_data: Optional[UserProfile] = None
    ) -> LearningPathData:
        """
        Generate personalized learning path from user profile.
        
        Args:
            db: PostgreSQL session
            neo4j_session: Neo4j session
            user_id: User ID
            profile_data: Optional UserProfile object (if None, fetches from DB)
            
        Returns:
            LearningPathData object
        """
        try:
            # Fetch user and profile if not provided
            if not profile_data:
                user_result = await db.execute(
                    select(User).where(User.id == user_id)
                )
                user = user_result.scalar_one_or_none()
                if not user:
                    raise ValueError(f"User {user_id} not found")
                
                profile_result = await db.execute(
                    select(UserProfile).where(UserProfile.user_id == user_id)
                )
                profile_data = profile_result.scalar_one_or_none()
            
            # Get user data
            user_result = await db.execute(
                select(User).where(User.id == user_id)
            )
            user = user_result.scalar_one_or_none()
            if not user:
                raise ValueError(f"User {user_id} not found")
            
            # Determine appropriate level for CanDo query
            current_level = user.current_level
            cando_level = self.map_level_to_cefr(current_level) or "A1"  # Default to A1 if no level
            
            # Fetch relevant CanDo descriptors
            cando_descriptors = await self.fetch_cando_descriptors(
                neo4j_session=neo4j_session,
                level=cando_level,
                limit=200
            )
            
            # Build profile context
            profile_context = {}
            if profile_data:
                profile_context = {
                    "learning_goals": profile_data.learning_goals or [],
                    "previous_knowledge": profile_data.previous_knowledge or {},
                    "learning_experiences": profile_data.learning_experiences or {},
                    "usage_context": profile_data.usage_context or {}
                }
            else:
                profile_context = {
                    "learning_goals": user.learning_goals or [],
                    "previous_knowledge": {},
                    "learning_experiences": {},
                    "usage_context": {}
                }
            
            # Load prompt template - go from services/ to app/prompts/
            base_dir = Path(__file__).parent.parent  # Go from services/ to app/
            prompt_path = base_dir / "prompts" / "learning_path_generation_prompt.txt"
            with open(prompt_path, "r", encoding="utf-8") as f:
                prompt_template = f.read()
            
            # Format prompt with context
            cando_list = "\n".join([
                f"- {cd['uid']}: {cd['descriptionEn']} (Level: {cd['level']}, Topic: {cd['primaryTopicEn']})"
                for cd in cando_descriptors[:100]  # Limit to first 100 for prompt size
            ])
            
            formatted_prompt = prompt_template.format(
                can_do_descriptors=cando_list,
                learning_goals=json.dumps(profile_context["learning_goals"]),
                previous_knowledge=json.dumps(profile_context["previous_knowledge"]),
                learning_experiences=json.dumps(profile_context["learning_experiences"]),
                usage_context=json.dumps(profile_context["usage_context"]),
                current_level=current_level,
                target_languages=json.dumps(user.target_languages or ["ja"])
            )
            
            # Generate path using AI
            system_prompt = """You are an expert language learning path creator. Generate structured learning paths in valid JSON format.
Return ONLY valid JSON matching the LearningPathData schema with: path_name, description, total_estimated_days, steps (array), milestones (array), starting_level, target_level, learning_goals."""
            
            response = await self.ai_service.generate_reply(
                provider="openai",
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": formatted_prompt}
                ],
                temperature=0.7
            )
            
            # Parse response
            path_json = response.get("content", {})
            if isinstance(path_json, str):
                path_json = json.loads(path_json)
            
            # Validate with Pydantic
            path_data = LearningPathData(**path_json)
            path_data.created_at = datetime.utcnow()
            
            return path_data
            
        except Exception as e:
            logger.error("learning_path_generation_failed", error=str(e), user_id=str(user_id))
            raise
    
    async def save_learning_path(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        path_data: LearningPathData,
        version: Optional[int] = None
    ) -> LearningPath:
        """
        Save learning path to database.
        
        Args:
            db: Database session
            user_id: User ID
            path_data: LearningPathData object
            version: Optional version number (auto-incremented if None)
            
        Returns:
            Created LearningPath object
        """
        try:
            # Get next version number
            if version is None:
                result = await db.execute(
                    select(func.max(LearningPath.version))
                    .where(LearningPath.user_id == user_id)
                )
                max_version = result.scalar() or 0
                version = max_version + 1
            
            # Deactivate existing active path
            await db.execute(
                update(LearningPath)
                .where(
                    (LearningPath.user_id == user_id) &
                    (LearningPath.is_active == True)
                )
                .values(is_active=False)
            )
            
            # Create new path
            new_path = LearningPath(
                user_id=user_id,
                version=version,
                path_name=path_data.path_name,
                path_data=path_data.model_dump(),
                progress_data={},
                is_active=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            db.add(new_path)
            await db.commit()
            await db.refresh(new_path)
            
            return new_path
            
        except Exception as e:
            await db.rollback()
            logger.error("failed_to_save_learning_path", error=str(e), user_id=str(user_id))
            raise
    
    async def get_active_learning_path(
        self,
        db: AsyncSession,
        user_id: uuid.UUID
    ) -> Optional[LearningPath]:
        """Get user's active learning path."""
        result = await db.execute(
            select(LearningPath)
            .where(
                (LearningPath.user_id == user_id) &
                (LearningPath.is_active == True)
            )
            .order_by(LearningPath.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
    
    async def update_learning_path_progress(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        completed_step_id: str
    ) -> None:
        """
        Update learning path progress when a step is completed.
        
        Args:
            db: Database session
            user_id: User ID
            completed_step_id: ID of completed step
        """
        try:
            path = await self.get_active_learning_path(db, user_id)
            if not path:
                return
            
            progress = path.progress_data or {}
            completed_steps = progress.get("completed_step_ids", [])
            
            if completed_step_id not in completed_steps:
                completed_steps.append(completed_step_id)
                progress["completed_step_ids"] = completed_steps
                
                # Update current step
                path_data = path.path_data or {}
                steps = path_data.get("steps", [])
                current_idx = None
                for i, step in enumerate(steps):
                    if step.get("step_id") == completed_step_id:
                        current_idx = i
                        break
                
                if current_idx is not None and current_idx + 1 < len(steps):
                    progress["current_step_id"] = steps[current_idx + 1].get("step_id")
                
                # Calculate progress percentage
                total_steps = len(steps)
                if total_steps > 0:
                    progress["progress_percentage"] = (len(completed_steps) / total_steps) * 100
                
                progress["last_updated"] = datetime.utcnow().isoformat()
                
                path.progress_data = progress
                path.updated_at = datetime.utcnow()
                
                await db.commit()
                
        except Exception as e:
            await db.rollback()
            logger.error("failed_to_update_progress", error=str(e), user_id=str(user_id))
            raise
    
    async def update_learning_path_based_on_progress(
        self,
        db: AsyncSession,
        neo4j_session: Neo4jSession,
        user_id: uuid.UUID,
        learning_analytics: Dict[str, Any]
    ) -> Optional[LearningPath]:
        """
        Generate new version of learning path based on actual learning progress.
        
        Args:
            db: PostgreSQL session
            neo4j_session: Neo4j session
            user_id: User ID
            learning_analytics: Analytics data about user's progress
            
        Returns:
            New LearningPath if created, None otherwise
        """
        try:
            # Get current path and profile
            current_path = await self.get_active_learning_path(db, user_id)
            profile_result = await db.execute(
                select(UserProfile).where(UserProfile.user_id == user_id)
            )
            profile_data = profile_result.scalar_one_or_none()
            
            # Generate updated path
            new_path_data = await self.generate_learning_path(
                db=db,
                neo4j_session=neo4j_session,
                user_id=user_id,
                profile_data=profile_data
            )
            
            # Save as new version
            new_path = await self.save_learning_path(
                db=db,
                user_id=user_id,
                path_data=new_path_data
            )
            
            # Mark old path as superseded
            if current_path:
                current_path.superseded_by = new_path.id
                current_path.is_active = False
                await db.commit()
            
            return new_path
            
        except Exception as e:
            logger.error("failed_to_update_path", error=str(e), user_id=str(user_id))
            raise


# Singleton instance
learning_path_service = LearningPathService()

