"""
CanDo lesson recommendation service.

Analyzes user evidence across all CanDo lessons to provide adaptive recommendations:
- Next CanDo to study
- Review items (vocabulary/grammar patterns)
- Focus areas (stages needing more practice)
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, date
from collections import Counter
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession as PgSession
from neo4j import AsyncSession
import structlog

from app.models.database_models import ConversationInteraction, User
from app.services.cando_embedding_service import CanDoEmbeddingService

logger = structlog.get_logger()


class CanDoRecommendationService:
    """Service for generating adaptive CanDo lesson recommendations."""
    
    def __init__(self):
        self.embedding_service = CanDoEmbeddingService()
    
    async def get_recommendations(
        self,
        pg: PgSession,
        neo4j_session: AsyncSession,
        user_id: str,
        limit: int = 5,
    ) -> Dict[str, Any]:
        """
        Get adaptive recommendations for the user.
        
        Args:
            pg: Postgres session
            neo4j_session: Neo4j session
            user_id: User ID
            limit: Maximum number of recommendations
            
        Returns:
            Dict with next_lesson, review_items, focus_areas
        """
        try:
            # Get all CanDo evidence for this user
            # user_id might be string or UUID, convert to UUID if needed
            from uuid import UUID
            user_uuid = UUID(user_id) if isinstance(user_id, str) else user_id
            interactions_query = select(ConversationInteraction).where(
                and_(
                    ConversationInteraction.user_id == user_uuid,
                    ConversationInteraction.concept_type == 'cando_lesson'
                )
            ).order_by(ConversationInteraction.created_at.desc())
            
            result = await pg.execute(interactions_query)
            interactions = result.scalars().all()
            
            # Analyze evidence gaps
            can_do_stats = {}
            stage_stats = {"content": 0, "comprehension": 0, "production": 0, "interaction": 0}
            error_tags_all = []
            low_mastery_candos = []
            
            for interaction in interactions:
                can_do_id = interaction.concept_id
                if can_do_id not in can_do_stats:
                    can_do_stats[can_do_id] = {
                        "total_attempts": 0,
                        "correct_count": 0,
                        "stages": set(),
                        "mastery_level": interaction.mastery_level or 1,
                        "last_attempted": interaction.created_at.isoformat() if interaction.created_at else None,
                    }
                
                stats = can_do_stats[can_do_id]
                stats["total_attempts"] += 1
                if interaction.is_correct:
                    stats["correct_count"] += 1
                
                # Track stages
                if interaction.evidence_metadata:
                    stage = interaction.evidence_metadata.get("stage")
                    if stage:
                        stats["stages"].add(stage)
                        stage_stats[stage] = stage_stats.get(stage, 0) + 1
                
                # Track errors
                if interaction.evidence_metadata and interaction.evidence_metadata.get("error_tags"):
                    error_tags_all.extend(interaction.evidence_metadata["error_tags"])
                
                # Track low mastery
                if interaction.mastery_level and interaction.mastery_level < 3:
                    if can_do_id not in [c["can_do_id"] for c in low_mastery_candos]:
                        low_mastery_candos.append({
                            "can_do_id": can_do_id,
                            "mastery_level": interaction.mastery_level,
                            "last_attempted": interaction.created_at.isoformat() if interaction.created_at else None
                        })
            
            # Find next lesson (CanDo with no or minimal evidence)
            next_lesson = await self._find_next_lesson(
                neo4j_session, pg, user_id, can_do_stats, limit=1
            )
            
            # Find review items (low mastery CanDo)
            review_items = sorted(
                low_mastery_candos,
                key=lambda x: x.get("mastery_level", 1)
            )[:limit]
            
            # Find focus areas (stages with least practice)
            focus_areas = sorted(
                stage_stats.items(),
                key=lambda x: x[1]
            )[:2]  # Top 2 stages needing practice
            
            # Common error patterns
            error_tag_counts = Counter(error_tags_all)
            common_errors = [tag for tag, _ in error_tag_counts.most_common(5)]
            
            return {
                "next_lesson": next_lesson,
                "review_items": review_items,
                "focus_areas": [{"stage": stage, "practice_count": count} for stage, count in focus_areas],
                "common_errors": common_errors,
                "total_lessons_studied": len(can_do_stats),
                "total_attempts": sum(s["total_attempts"] for s in can_do_stats.values())
            }
            
        except Exception as e:
            logger.error("get_recommendations_failed", user_id=user_id, error=str(e))
            return {
                "next_lesson": None,
                "review_items": [],
                "focus_areas": [],
                "common_errors": [],
                "total_lessons_studied": 0,
                "total_attempts": 0
            }
    
    async def _find_next_lesson(
        self,
        neo4j_session: AsyncSession,
        pg: PgSession,
        user_id: str,
        can_do_stats: Dict[str, Any],
        limit: int = 1,
    ) -> Optional[Dict[str, Any]]:
        """
        Find next CanDo lesson to study.
        
        Strategy:
        1. Find CanDo with no evidence
        2. If all have evidence, find one with low mastery
        3. Use similarity search to find related CanDo
        """
        try:
            # Find CanDo with no evidence
            studied_ids = set(can_do_stats.keys())
            
            # Query all CanDo from Neo4j
            query = """
            MATCH (c:CanDoDescriptor)
            RETURN c.uid AS uid, c.titleEn AS title_en, c.titleJa AS title_ja,
                   c.level AS level, c.primaryTopic AS topic
            ORDER BY c.level ASC
            LIMIT 50
            """
            result = await neo4j_session.run(query)
            all_candos = []
            async for record in result:
                all_candos.append({
                    "uid": record.get("uid"),
                    "title_en": record.get("title_en"),
                    "title_ja": record.get("title_ja"),
                    "level": record.get("level"),
                    "topic": record.get("topic")
                })
            
            # Find unstudied CanDo
            unstudied = [c for c in all_candos if c["uid"] not in studied_ids]
            
            if unstudied:
                # Return first unstudied (could be enhanced with similarity to studied)
                next_cando = unstudied[0]
                return {
                    "can_do_id": next_cando["uid"],
                    "title": next_cando.get("title_en") or next_cando.get("title_ja") or next_cando["uid"],
                    "level": next_cando.get("level"),
                    "topic": next_cando.get("topic"),
                    "reason": "not_studied"
                }
            
            # All studied - find one with low mastery or incomplete stages
            low_mastery = [
                (cid, stats) for cid, stats in can_do_stats.items()
                if stats.get("mastery_level", 1) < 3 or len(stats.get("stages", set())) < 4
            ]
            
            if low_mastery:
                # Get CanDo details
                cando_id, stats = low_mastery[0]
                cando_query = """
                MATCH (c:CanDoDescriptor {uid: $can_do_id})
                RETURN c.titleEn AS title_en, c.titleJa AS title_ja,
                       c.level AS level, c.primaryTopic AS topic
                LIMIT 1
                """
                cando_result = await neo4j_session.run(cando_query, can_do_id=cando_id)
                cando_record = await cando_result.single()
                if cando_record:
                    return {
                        "can_do_id": cando_id,
                        "title": cando_record.get("title_en") or cando_record.get("title_ja") or cando_id,
                        "level": cando_record.get("level"),
                        "topic": cando_record.get("topic"),
                        "reason": "needs_review",
                        "mastery_level": stats.get("mastery_level", 1)
                    }
            
            # Fallback: return first CanDo
            if all_candos:
                first = all_candos[0]
                return {
                    "can_do_id": first["uid"],
                    "title": first.get("title_en") or first.get("title_ja") or first["uid"],
                    "level": first.get("level"),
                    "topic": first.get("topic"),
                    "reason": "default"
                }
            
            return None
            
        except Exception as e:
            logger.warning("_find_next_lesson_failed", error=str(e))
            return None


# Singleton instance
cando_recommendation_service = CanDoRecommendationService()

