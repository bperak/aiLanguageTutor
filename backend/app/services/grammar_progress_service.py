"""
Grammar Progress Service
========================

Service for tracking user progress with grammar patterns, including SRS scheduling
and learning analytics.
"""

import logging
from datetime import datetime, timedelta, date
from typing import List, Optional, Dict, Any
from uuid import UUID
from neo4j import AsyncSession
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.models.user import ConversationInteraction, UserLearningProgress
from app.core.config import settings

logger = logging.getLogger(__name__)

class GrammarProgressService:
    """Service for managing grammar pattern progress tracking"""
    
    def __init__(self, neo4j_session: AsyncSession, db_session: Optional[Session] = None):
        self.neo4j_session = neo4j_session
        self.db_session = db_session
        
    async def record_study_session(
        self,
        user_id: str,
        pattern_id: str,
        grade: str,
        study_time_seconds: Optional[int] = None,
        confidence_self_reported: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Record a study session and update SRS scheduling.
        
        Args:
            user_id: User UUID
            pattern_id: Grammar pattern ID
            grade: SRS grade ('again', 'hard', 'good', 'easy')
            study_time_seconds: Time spent studying
            confidence_self_reported: User's confidence rating (1-5)
            
        Returns:
            Updated progress data
        """
        try:
            # Get pattern name from Neo4j
            pattern_name = await self._get_pattern_name(pattern_id)
            if not pattern_name:
                raise ValueError(f"Pattern not found: {pattern_id}")
            
            # Calculate SRS scheduling
            current_progress = await self._get_current_progress(user_id, pattern_id)
            srs_data = self._calculate_srs_schedule(grade, current_progress)
            
            # Store/update progress in PostgreSQL
            progress_data = await self._update_progress_data(
                user_id=user_id,
                pattern_id=pattern_id,
                pattern_name=pattern_name,
                grade=grade,
                study_time_seconds=study_time_seconds,
                confidence_self_reported=confidence_self_reported,
                srs_data=srs_data
            )
            
            # Update overall user learning progress
            await self._update_user_learning_summary(user_id, study_time_seconds)
            
            logger.info(f"Recorded study session for user {user_id}, pattern {pattern_id}, grade {grade}")
            return progress_data
            
        except Exception as e:
            logger.error(f"Error recording study session: {e}")
            raise
    
    async def get_user_pattern_progress(
        self,
        user_id: str,
        pattern_ids: Optional[List[str]] = None,
        include_completed: bool = True,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get user's progress for grammar patterns"""
        try:
            # Build query conditions
            conditions = ["ci.user_id = $user_id", "ci.concept_type = 'grammar_point'"]
            params = {"user_id": user_id, "limit": limit}
            
            if pattern_ids:
                conditions.append("ci.concept_id = ANY($pattern_ids)")
                params["pattern_ids"] = pattern_ids
            
            if not include_completed:
                conditions.append("ci.mastery_level < 5")
            
            query = f"""
            MATCH (gp:GrammarPattern)
            WHERE gp.id IN [ci.concept_id]
            WITH gp, ci
            ORDER BY ci.updated_at DESC
            LIMIT $limit
            RETURN {{
                pattern_id: gp.id,
                pattern_name: gp.pattern,
                mastery_level: ci.mastery_level,
                last_studied: ci.created_at,
                next_review_date: ci.next_review_date,
                is_completed: ci.mastery_level >= 5,
                study_count: ci.attempts_count,
                ease_factor: ci.ease_factor,
                interval_days: ci.interval_days
            }} as progress
            """
            
            # This would need to be implemented with actual database integration
            # For now, return mock data structure
            progress_list = []
            
            return progress_list
            
        except Exception as e:
            logger.error(f"Error getting user pattern progress: {e}")
            raise
    
    async def get_patterns_due_for_review(
        self,
        user_id: str,
        include_overdue: bool = True,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get patterns that are due for review"""
        try:
            today = date.today()
            conditions = [
                "ci.user_id = $user_id",
                "ci.concept_type = 'grammar_point'",
                "ci.next_review_date <= $today"
            ]
            
            if not include_overdue:
                conditions.append("ci.next_review_date >= $today")
            
            params = {"user_id": user_id, "today": today.isoformat(), "limit": limit}
            
            # Mock implementation - would connect to actual database
            due_patterns = []
            
            return due_patterns
            
        except Exception as e:
            logger.error(f"Error getting due patterns: {e}")
            raise
    
    async def get_user_progress_summary(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive progress summary"""
        try:
            # Mock implementation - would query actual database
            summary = {
                "total_patterns_studied": 0,
                "total_patterns_mastered": 0,
                "current_streak_days": 0,
                "weekly_study_minutes": 0,
                "average_mastery_level": 0.0,
                "patterns_due_today": 0,
                "patterns_overdue": 0
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting progress summary: {e}")
            raise
    
    async def get_learning_path_stats(
        self,
        user_id: str,
        pattern_ids: List[str]
    ) -> Dict[str, Any]:
        """Get statistics for a learning path"""
        try:
            # Calculate stats based on pattern progress
            total_patterns = len(pattern_ids)
            completed_patterns = 0
            total_mastery = 0
            total_study_time = 0
            
            # Mock implementation - would query actual progress data
            stats = {
                "total_patterns": total_patterns,
                "completed_patterns": completed_patterns,
                "average_mastery": total_mastery / max(total_patterns, 1),
                "estimated_completion_days": max(1, (total_patterns - completed_patterns) * 3),
                "total_study_time_minutes": total_study_time
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting learning path stats: {e}")
            raise
    
    # Helper methods
    async def _get_pattern_name(self, pattern_id: str) -> Optional[str]:
        """Get pattern name from Neo4j"""
        try:
            query = """
            MATCH (gp:GrammarPattern {id: $pattern_id})
            RETURN gp.pattern as pattern_name
            """
            
            result = await self.neo4j_session.run(query, pattern_id=pattern_id)
            record = await result.single()
            
            if record:
                return record["pattern_name"]
            return None
            
        except Exception as e:
            logger.error(f"Error getting pattern name: {e}")
            return None
    
    async def _get_current_progress(self, user_id: str, pattern_id: str) -> Optional[Dict[str, Any]]:
        """Get current progress data for a pattern"""
        # Mock implementation - would query PostgreSQL ConversationInteraction table
        return {
            "mastery_level": 1,
            "ease_factor": 2.5,
            "interval_days": 1,
            "attempts_count": 0
        }
    
    def _calculate_srs_schedule(self, grade: str, current_progress: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate next SRS review schedule based on grade"""
        ease_factor = float(current_progress.get("ease_factor", 2.5))
        interval_days = current_progress.get("interval_days", 1)
        mastery_level = current_progress.get("mastery_level", 1)
        
        # Simple SRS algorithm (similar to Anki)
        if grade == "again":
            new_interval = 1
            new_ease_factor = max(1.3, ease_factor - 0.2)
            new_mastery = max(1, mastery_level - 1)
        elif grade == "hard":
            new_interval = max(1, int(interval_days * 1.2))
            new_ease_factor = max(1.3, ease_factor - 0.15)
            new_mastery = mastery_level
        elif grade == "good":
            new_interval = max(1, int(interval_days * ease_factor))
            new_ease_factor = ease_factor
            new_mastery = min(5, mastery_level + 1)
        else:  # easy
            new_interval = max(1, int(interval_days * ease_factor * 1.3))
            new_ease_factor = ease_factor + 0.15
            new_mastery = min(5, mastery_level + 1)
        
        next_review_date = datetime.now() + timedelta(days=new_interval)
        
        return {
            "interval_days": new_interval,
            "ease_factor": round(new_ease_factor, 2),
            "mastery_level": new_mastery,
            "next_review_date": next_review_date.date().isoformat()
        }
    
    async def _update_progress_data(
        self,
        user_id: str,
        pattern_id: str,
        pattern_name: str,
        grade: str,
        study_time_seconds: Optional[int],
        confidence_self_reported: Optional[int],
        srs_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update progress data in PostgreSQL"""
        try:
            # Mock implementation - would actually update ConversationInteraction table
            progress_data = {
                "pattern_id": pattern_id,
                "pattern_name": pattern_name,
                "mastery_level": srs_data["mastery_level"],
                "last_studied": datetime.now().isoformat(),
                "next_review_date": srs_data["next_review_date"],
                "is_completed": srs_data["mastery_level"] >= 5,
                "study_count": 1,  # Would increment existing count
                "ease_factor": srs_data["ease_factor"],
                "interval_days": srs_data["interval_days"]
            }
            
            return progress_data
            
        except Exception as e:
            logger.error(f"Error updating progress data: {e}")
            raise
    
    async def _update_user_learning_summary(self, user_id: str, study_time_seconds: Optional[int]):
        """Update overall user learning progress summary"""
        try:
            # Mock implementation - would update UserLearningProgress table
            if study_time_seconds:
                study_time_minutes = study_time_seconds // 60
                # Update weekly progress, streaks, etc.
                logger.debug(f"Updated learning summary for user {user_id}: +{study_time_minutes} minutes")
            
        except Exception as e:
            logger.error(f"Error updating user learning summary: {e}")
