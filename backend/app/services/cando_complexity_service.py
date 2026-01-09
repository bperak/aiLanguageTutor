"""
CanDo Complexity Assessment Service

AI-based complexity assessment for CanDo descriptors to enable
progressive learning path ordering.
"""

from typing import Dict, Any, List, Optional
import structlog
import json
from neo4j import AsyncSession as Neo4jSession

from app.services.ai_chat_service import AIChatService
from app.core.config import settings

logger = structlog.get_logger()


class CanDoComplexityService:
    """Service for assessing complexity of CanDo descriptors."""
    
    def __init__(self):
        self.ai_service = AIChatService()
        self.default_provider = "openai"
        self.default_model = settings.PATH_COMPLEXITY_MODEL
    
    def _map_level_to_numeric(self, level: Optional[str]) -> float:
        """
        Map CEFR level to numeric value for complexity baseline.
        
        Args:
            level: CEFR level (A1, A2, B1, B2, C1, C2)
            
        Returns:
            Numeric complexity baseline (0.0-1.0)
        """
        if not level:
            return 0.0
        
        level_mapping = {
            "A1": 0.1,
            "A2": 0.25,
            "B1": 0.4,
            "B2": 0.55,
            "C1": 0.75,
            "C2": 0.9
        }
        
        level_upper = str(level).upper()
        return level_mapping.get(level_upper, 0.0)
    
    async def assess_complexity(
        self,
        cando_descriptor: Dict[str, Any],
        profile_context: Optional[Dict[str, Any]] = None
    ) -> float:
        """
        Assess complexity of a CanDo descriptor using AI.
        
        Args:
            cando_descriptor: CanDo descriptor dictionary with uid, level, descriptionEn, descriptionJa
            profile_context: Optional user profile context for personalized assessment
            
        Returns:
            Complexity score (0.0-1.0) where higher is more complex
        """
        try:
            # Base complexity from CEFR level
            level = cando_descriptor.get("level")
            base_complexity = self._map_level_to_numeric(level)
            
            # Get descriptions
            description_en = cando_descriptor.get("descriptionEn") or cando_descriptor.get("description", "")
            description_ja = cando_descriptor.get("descriptionJa", "")
            
            if not description_en and not description_ja:
                logger.warning("No description available for complexity assessment", 
                             uid=cando_descriptor.get("uid"))
                return base_complexity
            
            # Build context for AI assessment
            user_level = profile_context.get("current_level", "beginner_1") if profile_context else "beginner_1"
            previous_knowledge = profile_context.get("previous_knowledge", {}) if profile_context else {}
            
            system_prompt = """You are an expert language learning assessment specialist. 
Analyze the complexity of a Can-Do descriptor considering:
1. Linguistic complexity (grammar structures, vocabulary difficulty)
2. Cognitive load (concepts, context complexity)
3. Prerequisites needed
4. Relative difficulty within the CEFR level

Return ONLY a JSON object with a single "complexity_score" field (float between 0.0 and 1.0).
The score should reflect how complex this learning objective is relative to language learning in general.
Consider the user's context but focus on the objective complexity itself."""
            
            user_prompt = f"""Assess the complexity of this Can-Do descriptor:

Level: {level}
English Description: {description_en}
Japanese Description: {description_ja}

User Context:
- Current Level: {user_level}
- Previous Knowledge: {json.dumps(previous_knowledge, ensure_ascii=False)}

Consider:
- Grammar complexity required
- Vocabulary difficulty
- Cognitive concepts involved
- Prerequisites needed
- Context complexity

Return JSON: {{"complexity_score": <float 0.0-1.0>}}"""
            
            response = await self.ai_service.generate_reply(
                provider=self.default_provider,
                model=self.default_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2,
                max_output_tokens=100
            )
            
            # Parse response
            content = response.get("content", "")
            if isinstance(content, str):
                # Try to extract JSON
                try:
                    # Remove markdown code blocks if present
                    if "```" in content:
                        content = content.split("```")[1]
                        if content.startswith("json"):
                            content = content[4:]
                    content = content.strip()
                    result = json.loads(content)
                    ai_complexity = float(result.get("complexity_score", base_complexity))
                except (json.JSONDecodeError, ValueError, KeyError) as e:
                    logger.warning("Failed to parse complexity score from AI", 
                                 error=str(e), content=content[:100])
                    ai_complexity = base_complexity
            else:
                ai_complexity = float(content.get("complexity_score", base_complexity))
            
            # Combine base complexity (from level) with AI assessment
            # Weight: 40% level baseline, 60% AI assessment
            final_complexity = (base_complexity * 0.4) + (ai_complexity * 0.6)
            
            # Ensure it's within bounds
            final_complexity = max(0.0, min(1.0, final_complexity))
            
            logger.debug("Assessed CanDo complexity",
                        uid=cando_descriptor.get("uid"),
                        level=level,
                        base=base_complexity,
                        ai=ai_complexity,
                        final=final_complexity)
            
            return final_complexity
            
        except Exception as e:
            logger.error("Failed to assess CanDo complexity",
                        uid=cando_descriptor.get("uid"),
                        error=str(e))
            # Fallback to level-based complexity
            return self._map_level_to_numeric(cando_descriptor.get("level"))
    
    async def compare_complexity(
        self,
        cando1: Dict[str, Any],
        cando2: Dict[str, Any],
        profile_context: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Compare complexity of two CanDo descriptors.
        
        Args:
            cando1: First CanDo descriptor
            cando2: Second CanDo descriptor
            profile_context: Optional user profile context
            
        Returns:
            -1 if cando1 < cando2, 0 if equal, 1 if cando1 > cando2
        """
        complexity1 = await self.assess_complexity(cando1, profile_context)
        complexity2 = await self.assess_complexity(cando2, profile_context)
        
        if complexity1 < complexity2:
            return -1
        elif complexity1 > complexity2:
            return 1
        else:
            return 0
    
    async def rank_by_complexity(
        self,
        cando_list: List[Dict[str, Any]],
        profile_context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Rank CanDo descriptors by complexity.
        
        Args:
            cando_list: List of CanDo descriptor dictionaries
            profile_context: Optional user profile context
            
        Returns:
            List sorted by complexity (lowest to highest)
        """
        # Assess complexity for each
        cando_with_complexity = []
        for cando in cando_list:
            complexity = await self.assess_complexity(cando, profile_context)
            cando_with_complexity.append({
                **cando,
                "_complexity_score": complexity
            })
        
        # Sort by complexity
        sorted_list = sorted(cando_with_complexity, key=lambda x: x["_complexity_score"])
        
        # Remove internal complexity score before returning
        for item in sorted_list:
            item.pop("_complexity_score", None)
        
        return sorted_list


# Singleton instance
cando_complexity_service = CanDoComplexityService()

