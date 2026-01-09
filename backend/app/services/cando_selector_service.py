"""
CanDo Selector Service

Selects appropriate CanDo descriptors based on user profile
and handles creation of new descriptors when needed.
"""

from typing import List, Dict, Any, Optional
import structlog
from neo4j import AsyncSession as Neo4jSession

from app.services.cando_creation_service import CanDoCreationService
from app.services.cando_embedding_service import CanDoEmbeddingService

logger = structlog.get_logger()


class CanDoSelectorService:
    """Service for selecting CanDo descriptors based on user profile."""
    
    def __init__(self):
        self.creation_service = CanDoCreationService()
        self.embedding_service = CanDoEmbeddingService()
    
    def _map_level_to_cefr(self, level: Optional[str]) -> Optional[str]:
        """
        Map custom learning stage to CEFR level.
        
        Args:
            level: Custom level (beginner_1, beginner_2, etc.)
            
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
    
    async def select_initial_candos(
        self,
        profile_context: Dict[str, Any],
        neo4j_session: Neo4jSession,
        limit: int = 200
    ) -> List[Dict[str, Any]]:
        """
        Select initial CanDo descriptors based on user profile.
        
        Args:
            profile_context: User profile context with level, goals, etc.
            neo4j_session: Neo4j session
            limit: Maximum number of descriptors to fetch
            
        Returns:
            List of CanDo descriptor dictionaries
        """
        try:
            # Map user level to CEFR
            user_level = profile_context.get("current_level", "beginner_1")
            cefr_level = self._map_level_to_cefr(user_level) or "A1"
            
            # Get learning goals and topics
            learning_goals = profile_context.get("learning_goals", [])
            usage_context = profile_context.get("usage_context", {})
            contexts = usage_context.get("contexts", [])
            
            # Build query to fetch relevant CanDo descriptors
            query = """
            MATCH (c:CanDoDescriptor)
            WHERE ($level IS NULL OR toString(c.level) = $level)
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
            
            result = await neo4j_session.run(query, level=cefr_level, limit=limit)
            candos = [dict(record) async for record in result]
            
            # Filter by profile context
            filtered_candos = self.filter_by_profile(candos, profile_context)
            
            logger.info("Selected initial CanDo descriptors",
                       total=len(candos),
                       filtered=len(filtered_candos),
                       level=cefr_level)
            
            return filtered_candos
            
        except Exception as e:
            logger.error("Failed to select initial CanDo descriptors",
                        error=str(e))
            return []
    
    def filter_by_profile(
        self,
        candos: List[Dict[str, Any]],
        profile_context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Filter CanDo descriptors by profile context.
        
        Uses vocabulary_domain_goals, cultural_interests, and scenario_details
        to prioritize relevant CanDo descriptors.
        
        Args:
            candos: List of CanDo descriptor dictionaries
            profile_context: User profile context with enhanced fields
            
        Returns:
            Filtered list prioritized by relevance
        """
        learning_goals = profile_context.get("learning_goals", [])
        usage_context = profile_context.get("usage_context", {})
        contexts = usage_context.get("contexts", [])
        specific_situations = usage_context.get("specific_situations", [])
        previous_knowledge = profile_context.get("previous_knowledge", {})
        known_areas = previous_knowledge.get("specific_areas_known", [])
        
        # Score each CanDo by relevance
        scored_candos = []
        
        for cando in candos:
            score = 0.0
            topic = str(cando.get("primaryTopicEn", "")).lower()
            description = str(cando.get("descriptionEn", "")).lower()
            
            # Check against learning goals
            for goal in learning_goals:
                goal_lower = goal.lower()
                if goal_lower in topic or goal_lower in description:
                    score += 2.0
            
            # Check against vocabulary domain goals (new field)
            vocab_goals = profile_context.get("vocabulary_domain_goals", [])
            for vocab_goal in vocab_goals:
                vocab_lower = str(vocab_goal).lower()
                if vocab_lower in topic or vocab_lower in description:
                    score += 1.5
            
            # Check against cultural interests (new field)
            cultural_interests = profile_context.get("cultural_interests", [])
            for interest in cultural_interests:
                interest_lower = str(interest).lower()
                if interest_lower in topic or interest_lower in description:
                    score += 1.0
            
            # Check against usage contexts
            for context in contexts:
                context_lower = context.lower()
                if context_lower in topic or context_lower in description:
                    score += 1.5
            
            # Check against specific situations
            for situation in specific_situations:
                situation_lower = situation.lower()
                if situation_lower in description:
                    score += 1.0
            
            # Penalize known areas (but don't exclude completely)
            for known in known_areas:
                known_lower = known.lower()
                if known_lower in topic or known_lower in description:
                    score -= 0.5
            
            scored_candos.append({
                **cando,
                "_relevance_score": score
            })
        
        # Sort by relevance score (highest first)
        scored_candos.sort(key=lambda x: x["_relevance_score"], reverse=True)
        
        # Remove internal score before returning
        filtered = []
        for item in scored_candos:
            item.pop("_relevance_score", None)
            filtered.append(item)
        
        return filtered
    
    async def create_missing_cando(
        self,
        description: str,
        metadata: Dict[str, Any],
        neo4j_session: Neo4jSession
    ) -> Optional[Dict[str, Any]]:
        """
        Create a new CanDo descriptor if needed.
        
        Args:
            description: CanDo description
            metadata: Metadata including level, topic, skillDomain, type
            neo4j_session: Neo4j session
            
        Returns:
            Created CanDo descriptor dictionary or None if failed
        """
        try:
            # Use CanDoCreationService to create new descriptor with auto-processing
            # The service will infer fields, generate titles, embeddings, etc.
            created = await self.creation_service.create_cando_with_auto_processing(
                description_en=metadata.get("descriptionEn", description),
                description_ja=metadata.get("descriptionJa", ""),
                session=neo4j_session
            )
            
            if created:
                logger.info("Created new CanDo descriptor",
                           uid=created.get("uid"))
                return created
            else:
                logger.warning("Failed to create CanDo descriptor")
                return None
                
        except Exception as e:
            logger.error("Error creating missing CanDo descriptor",
                        error=str(e))
            return None


# Singleton instance
cando_selector_service = CanDoSelectorService()

