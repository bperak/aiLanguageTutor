"""
Path Builder Service

Algorithm-based path construction using semantic similarity
to ensure continuous learning progression.
"""

from typing import List, Dict, Any, Optional, Set
import structlog

from app.services.cando_embedding_service import CanDoEmbeddingService
from app.services.cando_complexity_service import cando_complexity_service
from app.core.config import settings

logger = structlog.get_logger()


class PathBuilder:
    """Service for building semantically connected learning paths."""
    
    def __init__(self):
        self.embedding_service = CanDoEmbeddingService()
        self.complexity_service = cando_complexity_service
        self.max_steps = settings.PATH_MAX_STEPS
        self.complexity_increment = settings.PATH_COMPLEXITY_INCREMENT
        self.semantic_threshold = settings.PATH_SEMANTIC_THRESHOLD
    
    async def build_semantic_path(
        self,
        starting_candos: List[Dict[str, Any]],
        all_candos: List[Dict[str, Any]],
        profile_context: Dict[str, Any],
        neo4j_session
    ) -> List[Dict[str, Any]]:
        """
        Build a continuous semantic path from CanDo descriptors.
        
        Args:
            starting_candos: Initial CanDo descriptors to start from
            all_candos: All available CanDo descriptors
            profile_context: User profile context
            neo4j_session: Neo4j session for similarity queries
            
        Returns:
            Ordered list of CanDo descriptors forming the path
        """
        if not starting_candos:
            logger.warning("No starting CanDo descriptors provided")
            return []
        
        # Assess complexity for all candidates
        logger.info("Assessing complexity for path building",
                   total_candos=len(all_candos))
        
        # Get complexity scores for all candidates
        cando_with_complexity = []
        for cando in all_candos:
            complexity = await self.complexity_service.assess_complexity(
                cando, profile_context
            )
            cando_with_complexity.append({
                **cando,
                "_complexity": complexity
            })
        
        # Sort starting candidates by complexity (lowest first)
        starting_with_complexity = []
        for cando in starting_candos:
            matching = next(
                (c for c in cando_with_complexity if c.get("uid") == cando.get("uid")),
                None
            )
            if matching:
                starting_with_complexity.append(matching)
        
        if not starting_with_complexity:
            # Fallback: use first starting cando and assess
            first = starting_candos[0]
            complexity = await self.complexity_service.assess_complexity(first, profile_context)
            starting_with_complexity = [{
                **first,
                "_complexity": complexity
            }]
        
        starting_with_complexity.sort(key=lambda x: x["_complexity"])
        
        # Start with the lowest complexity CanDo
        path = []
        visited: Set[str] = set()
        current_cando = starting_with_complexity[0]
        path.append(current_cando)
        visited.add(current_cando.get("uid"))
        current_complexity = current_cando["_complexity"]
        
        logger.info("Starting path building",
                   starting_uid=current_cando.get("uid"),
                   starting_complexity=current_complexity)
        
        # Build path step by step
        while len(path) < self.max_steps:
            # Find next semantically related CanDo
            next_cando = await self.find_next_semantic_cando(
                current_cando=current_cando,
                available_candos=cando_with_complexity,
                visited=visited,
                current_complexity=current_complexity,
                profile_context=profile_context,
                neo4j_session=neo4j_session
            )
            
            if not next_cando:
                logger.info("No more suitable CanDo descriptors found",
                           path_length=len(path))
                break
            
            # Add to path
            path.append(next_cando)
            visited.add(next_cando.get("uid"))
            current_cando = next_cando
            current_complexity = next_cando["_complexity"]
            
            logger.debug("Added CanDo to path",
                        uid=next_cando.get("uid"),
                        complexity=current_complexity,
                        path_length=len(path))
        
        # Remove internal complexity scores
        for item in path:
            item.pop("_complexity", None)
        
        # Verify continuity
        await self.ensure_continuity(path, neo4j_session)
        
        logger.info("Path building completed",
                   path_length=len(path))
        
        return path
    
    async def find_next_semantic_cando(
        self,
        current_cando: Dict[str, Any],
        available_candos: List[Dict[str, Any]],
        visited: Set[str],
        current_complexity: float,
        profile_context: Dict[str, Any],
        neo4j_session
    ) -> Optional[Dict[str, Any]]:
        """
        Find the next semantically related CanDo descriptor.
        
        Args:
            current_cando: Current CanDo in the path
            available_candos: All available CanDo descriptors with complexity
            visited: Set of already visited CanDo UIDs
            current_complexity: Current complexity level
            profile_context: User profile context
            neo4j_session: Neo4j session
            
        Returns:
            Next CanDo descriptor or None if none found
        """
        current_uid = current_cando.get("uid")
        if not current_uid:
            return None
        
        # Find semantically similar CanDo descriptors
        try:
            similar_candos = await self.embedding_service.find_similar_candos(
                neo4j_session=neo4j_session,
                can_do_uid=current_uid,
                limit=50,  # Get more candidates
                similarity_threshold=self.semantic_threshold
            )
        except Exception as e:
            logger.warning("Failed to find similar CanDo descriptors, using fallback",
                          error=str(e))
            similar_candos = []
        
        # Create a map of UID to CanDo for quick lookup
        cando_map = {c.get("uid"): c for c in available_candos}
        
        # Filter and score candidates
        candidates = []
        
        for similar in similar_candos:
            uid = similar.get("uid")
            
            # Skip if already visited
            if uid in visited:
                continue
            
            # Get full CanDo descriptor
            cando = cando_map.get(uid)
            if not cando:
                continue
            
            # Check complexity progression
            candidate_complexity = cando.get("_complexity", 0.0)
            
            # Must be at least current complexity, but not too far ahead
            if candidate_complexity < current_complexity:
                continue
            
            max_allowed = current_complexity + self.complexity_increment
            if candidate_complexity > max_allowed:
                continue
            
            # Score candidate: combine similarity and complexity fit
            similarity_score = similar.get("similarity", 0.0)
            complexity_fit = 1.0 - abs(candidate_complexity - (current_complexity + 0.05))
            combined_score = (similarity_score * 0.7) + (complexity_fit * 0.3)
            
            candidates.append({
                **cando,
                "_similarity": similarity_score,
                "_combined_score": combined_score
            })
        
        # If no similar candidates found, try from available list
        if not candidates:
            # Filter available by complexity constraints
            for cando in available_candos:
                uid = cando.get("uid")
                if uid in visited:
                    continue
                
                candidate_complexity = cando.get("_complexity", 0.0)
                
                # Must be at least current complexity, but not too far ahead
                if candidate_complexity < current_complexity:
                    continue
                
                max_allowed = current_complexity + self.complexity_increment
                if candidate_complexity > max_allowed:
                    continue
                
                # Lower score since not semantically similar
                candidates.append({
                    **cando,
                    "_similarity": 0.5,  # Default similarity
                    "_combined_score": 0.5
                })
        
        if not candidates:
            return None
        
        # Sort by combined score (highest first)
        candidates.sort(key=lambda x: x["_combined_score"], reverse=True)
        
        # Return best candidate
        best = candidates[0]
        best.pop("_similarity", None)
        best.pop("_combined_score", None)
        
        return best
    
    async def ensure_continuity(
        self,
        path_sequence: List[Dict[str, Any]],
        neo4j_session
    ) -> bool:
        """
        Verify semantic relationships in the path sequence.
        
        Args:
            path_sequence: Ordered list of CanDo descriptors
            neo4j_session: Neo4j session
            
        Returns:
            True if path has good continuity, False otherwise
        """
        if len(path_sequence) < 2:
            return True
        
        continuity_issues = 0
        
        for i in range(len(path_sequence) - 1):
            current = path_sequence[i]
            next_cando = path_sequence[i + 1]
            
            current_uid = current.get("uid")
            next_uid = next_cando.get("uid")
            
            if not current_uid or not next_uid:
                continue
            
            # Check if they're semantically similar
            try:
                similar = await self.embedding_service.find_similar_candos(
                    neo4j_session=neo4j_session,
                    can_do_uid=current_uid,
                    limit=10,
                    similarity_threshold=self.semantic_threshold
                )
                
                # Check if next is in similar list
                is_related = any(s.get("uid") == next_uid for s in similar)
                
                if not is_related:
                    continuity_issues += 1
                    logger.warning("Potential continuity gap in path",
                                  from_uid=current_uid,
                                  to_uid=next_uid)
            except Exception as e:
                logger.warning("Failed to verify continuity",
                              error=str(e))
                continuity_issues += 1
        
        continuity_ratio = 1.0 - (continuity_issues / max(1, len(path_sequence) - 1))
        
        logger.info("Path continuity check",
                   total_steps=len(path_sequence),
                   issues=continuity_issues,
                   continuity_ratio=continuity_ratio)
        
        return continuity_ratio >= 0.7  # At least 70% continuity


# Singleton instance
path_builder = PathBuilder()

