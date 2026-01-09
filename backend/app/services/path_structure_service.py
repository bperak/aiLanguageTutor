"""
Path-Level Structure Generation Service

Generates vocabulary, grammar patterns, and formulaic expressions at the path level
(complementary to CanDo list) for evaluation tracking and learning loop feedback.
"""

from typing import Dict, Any, List, Optional
import structlog
import json
from neo4j import AsyncSession as Neo4jSession

from app.services.ai_chat_service import AIChatService
from app.core.config import settings
from app.utils.json_helpers import parse_json_object

logger = structlog.get_logger()


class PathStructureService:
    """Service for generating path-level structures (vocabulary, grammar, expressions)."""
    
    def __init__(self):
        self.ai_service = AIChatService()
        self.default_provider = "openai"
        self.default_model = "gpt-4o-mini"
    
    def _map_level_to_cefr(self, level: Optional[str]) -> Optional[str]:
        """Map custom learning stage to CEFR level."""
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
    
    async def generate_path_structures(
        self,
        path_steps: List[Dict[str, Any]],
        profile_context: Dict[str, Any],
        neo4j_session: Optional[Neo4jSession] = None
    ) -> Dict[str, Any]:
        """
        Generate path-level structures (vocabulary, grammar, expressions) for entire path.
        
        Args:
            path_steps: List of learning path steps with CanDo descriptors
            profile_context: User profile context with goals, known inventory, learning targets
            neo4j_session: Optional Neo4j session for validation
            
        Returns:
            Dictionary with path_structures containing vocabulary, grammar, and expressions
        """
        try:
            # Extract profile data
            vocabulary_domain_goals = profile_context.get("vocabulary_domain_goals", [])
            grammar_progression_goals = profile_context.get("grammar_progression_goals", [])
            formulaic_expression_goals = profile_context.get("formulaic_expression_goals", [])
            vocabulary_known = profile_context.get("vocabulary_known", [])
            grammar_known = profile_context.get("grammar_known", [])
            expressions_known = profile_context.get("expressions_known", [])
            vocabulary_learning_target = profile_context.get("vocabulary_learning_target")
            grammar_learning_target = profile_context.get("grammar_learning_target")
            expression_learning_target = profile_context.get("expression_learning_target")
            current_level = profile_context.get("current_level", "beginner_1")
            
            # Generate structures for each milestone
            path_structures = {
                "vocabulary": [],
                "grammar": [],
                "expressions": []
            }
            
            # Calculate structures per milestone
            num_milestones = len(path_steps)
            if num_milestones == 0:
                return path_structures
            
            vocab_per_milestone = (vocabulary_learning_target or 20) if vocabulary_learning_target else 20
            grammar_per_milestone = (grammar_learning_target or 5) if grammar_learning_target else 5
            expr_per_milestone = (expression_learning_target or 3) if expression_learning_target else 3
            
            # Generate structures for each step/milestone
            for idx, step in enumerate(path_steps):
                milestone_id = step.get("step_id", f"milestone_{idx + 1}")
                can_do_ids = step.get("can_do_descriptors", [])
                step_level = step.get("difficulty_level") or current_level
                cefr_level = self._map_level_to_cefr(step_level) or "A1"
                
                # Generate vocabulary for this milestone
                vocab_structures = await self._generate_vocabulary_structures(
                    milestone_id=milestone_id,
                    can_do_ids=can_do_ids,
                    vocabulary_domain_goals=vocabulary_domain_goals,
                    vocabulary_known=vocabulary_known,
                    target_count=vocab_per_milestone,
                    level=step_level,
                    cefr_level=cefr_level,
                    neo4j_session=neo4j_session
                )
                path_structures["vocabulary"].extend(vocab_structures)
                
                # Generate grammar for this milestone
                grammar_structures = await self._generate_grammar_structures(
                    milestone_id=milestone_id,
                    can_do_ids=can_do_ids,
                    grammar_progression_goals=grammar_progression_goals,
                    grammar_known=grammar_known,
                    target_count=grammar_per_milestone,
                    level=step_level,
                    cefr_level=cefr_level,
                    neo4j_session=neo4j_session
                )
                path_structures["grammar"].extend(grammar_structures)
                
                # Generate expressions for this milestone
                expr_structures = await self._generate_expression_structures(
                    milestone_id=milestone_id,
                    can_do_ids=can_do_ids,
                    formulaic_expression_goals=formulaic_expression_goals,
                    expressions_known=expressions_known,
                    target_count=expr_per_milestone,
                    level=step_level,
                    cefr_level=cefr_level,
                    register_preferences=profile_context.get("usage_context", {}).get("register_preferences", []) if isinstance(profile_context.get("usage_context"), dict) else [],
                    neo4j_session=neo4j_session
                )
                path_structures["expressions"].extend(expr_structures)
            
            logger.info("Path structures generated",
                       vocabulary_count=len(path_structures["vocabulary"]),
                       grammar_count=len(path_structures["grammar"]),
                       expressions_count=len(path_structures["expressions"]))
            
            return path_structures
            
        except Exception as e:
            logger.error("Failed to generate path structures", error=str(e))
            return {"vocabulary": [], "grammar": [], "expressions": []}
    
    async def _generate_vocabulary_structures(
        self,
        milestone_id: str,
        can_do_ids: List[str],
        vocabulary_domain_goals: List[str],
        vocabulary_known: List[Dict[str, Any]],
        target_count: int,
        level: str,
        cefr_level: str,
        neo4j_session: Optional[Neo4jSession] = None
    ) -> List[Dict[str, Any]]:
        """Generate vocabulary structures for a milestone."""
        # Filter out known vocabulary
        known_words = {v.get("word") for v in vocabulary_known if isinstance(v, dict)}
        
        # Build prompt for AI generation
        prompt = f"""Generate {target_count} vocabulary words for milestone {milestone_id} at level {level} ({cefr_level}).

CanDo IDs: {', '.join(can_do_ids)}
Vocabulary Domain Goals: {', '.join(vocabulary_domain_goals) if vocabulary_domain_goals else 'general'}
Known Vocabulary (exclude these): {', '.join(list(known_words)[:10]) if known_words else 'none'}

Generate vocabulary that:
- Matches level {level} ({cefr_level}) complexity
- Is complementary to the CanDo descriptors
- Aligns with vocabulary domain goals
- Is not in the known vocabulary list

Return JSON array of vocabulary items:
[
  {{
    "word": "Japanese word",
    "domain": "domain name",
    "milestone": "{milestone_id}",
    "level": "{level}",
    "cefr_level": "{cefr_level}",
    "validated": true
  }},
  ...
]"""
        
        try:
            response = await self.ai_service.generate_reply(
                provider=self.default_provider,
                model=self.default_model,
                messages=[{"role": "user", "content": prompt}],
                system_prompt="You are a Japanese language learning expert. Generate level-appropriate vocabulary. Return only valid JSON.",
                temperature=0.3
            )
            
            # Parse response
            content = response.get("content", "")
            if isinstance(content, str):
                # Try to extract JSON
                try:
                    # Remove markdown code blocks if present
                    if "```json" in content:
                        start = content.find("```json") + 7
                        end = content.find("```", start)
                        content = content[start:end].strip()
                    elif "```" in content:
                        start = content.find("```") + 3
                        end = content.find("```", start)
                        content = content[start:end].strip()
                    
                    vocab_list = parse_json_object(content)
                    if isinstance(vocab_list, list):
                        # Ensure all items have required fields
                        for item in vocab_list:
                            if not isinstance(item, dict):
                                continue
                            item.setdefault("milestone", milestone_id)
                            item.setdefault("level", level)
                            item.setdefault("cefr_level", cefr_level)
                            item.setdefault("validated", True)
                        return vocab_list
                    elif isinstance(vocab_list, dict) and "vocabulary" in vocab_list:
                        return vocab_list["vocabulary"]
                except (json.JSONDecodeError, ValueError, KeyError) as e:
                    logger.warning("Failed to parse vocabulary structures", milestone=milestone_id, error=str(e))
            return []
            
        except Exception as e:
            logger.warning("Failed to generate vocabulary structures", milestone=milestone_id, error=str(e))
            return []
    
    async def _generate_grammar_structures(
        self,
        milestone_id: str,
        can_do_ids: List[str],
        grammar_progression_goals: List[str],
        grammar_known: List[Dict[str, Any]],
        target_count: int,
        level: str,
        cefr_level: str,
        neo4j_session: Optional[Neo4jSession] = None
    ) -> List[Dict[str, Any]]:
        """Generate grammar structures for a milestone."""
        # Filter out known grammar
        known_patterns = {g.get("pattern") for g in grammar_known if isinstance(g, dict)}
        
        prompt = f"""Generate {target_count} grammar patterns for milestone {milestone_id} at level {level} ({cefr_level}).

CanDo IDs: {', '.join(can_do_ids)}
Grammar Progression Goals: {', '.join(grammar_progression_goals) if grammar_progression_goals else 'general'}
Known Grammar (exclude these): {', '.join(list(known_patterns)[:10]) if known_patterns else 'none'}

Generate grammar patterns that:
- Match level {level} ({cefr_level}) complexity
- Are complementary to the CanDo descriptors
- Align with grammar progression goals
- Are not in the known grammar list
- Follow logical progression (prerequisites before dependent patterns)

Return JSON array:
[
  {{
    "pattern": "grammar pattern name",
    "level": "{level}",
    "cefr_level": "{cefr_level}",
    "milestone": "{milestone_id}",
    "validated": true,
    "prerequisites": ["pattern1", "pattern2"]
  }},
  ...
]"""
        
        try:
            response = await self.ai_service.generate_reply(
                provider=self.default_provider,
                model=self.default_model,
                messages=[{"role": "user", "content": prompt}],
                system_prompt="You are a Japanese language learning expert. Generate level-appropriate grammar patterns. Return only valid JSON.",
                temperature=0.3
            )
            
            content = response.get("content", "")
            if isinstance(content, str):
                try:
                    if "```json" in content:
                        start = content.find("```json") + 7
                        end = content.find("```", start)
                        content = content[start:end].strip()
                    elif "```" in content:
                        start = content.find("```") + 3
                        end = content.find("```", start)
                        content = content[start:end].strip()
                    
                    grammar_list = parse_json_object(content)
                    if isinstance(grammar_list, list):
                        for item in grammar_list:
                            if not isinstance(item, dict):
                                continue
                            item.setdefault("milestone", milestone_id)
                            item.setdefault("level", level)
                            item.setdefault("cefr_level", cefr_level)
                            item.setdefault("validated", True)
                            item.setdefault("prerequisites", [])
                        return grammar_list
                    elif isinstance(grammar_list, dict) and "grammar" in grammar_list:
                        return grammar_list["grammar"]
                except (json.JSONDecodeError, ValueError, KeyError) as e:
                    logger.warning("Failed to parse grammar structures", milestone=milestone_id, error=str(e))
            return []
        except Exception as e:
            logger.warning("Failed to generate grammar structures", milestone=milestone_id, error=str(e))
            return []
    
    async def _generate_expression_structures(
        self,
        milestone_id: str,
        can_do_ids: List[str],
        formulaic_expression_goals: List[str],
        expressions_known: List[Dict[str, Any]],
        target_count: int,
        level: str,
        cefr_level: str,
        register_preferences: List[str],
        neo4j_session: Optional[Neo4jSession] = None
    ) -> List[Dict[str, Any]]:
        """Generate formulaic expression structures for a milestone."""
        # Filter out known expressions
        known_exprs = {e.get("expression") for e in expressions_known if isinstance(e, dict)}
        
        register_str = ', '.join(register_preferences) if register_preferences else 'polite'
        
        prompt = f"""Generate {target_count} formulaic expressions for milestone {milestone_id} at level {level} ({cefr_level}).

CanDo IDs: {', '.join(can_do_ids)}
Expression Goals: {', '.join(formulaic_expression_goals) if formulaic_expression_goals else 'general'}
Register Preferences: {register_str}
Known Expressions (exclude these): {', '.join(list(known_exprs)[:10]) if known_exprs else 'none'}

Generate expressions that:
- Match level {level} ({cefr_level}) complexity
- Are complementary to the CanDo descriptors
- Align with expression goals
- Match register preferences ({register_str})
- Are not in the known expressions list

Return JSON array:
[
  {{
    "expression": "Japanese expression",
    "context": "pragmatic context",
    "level": "{level}",
    "cefr_level": "{cefr_level}",
    "register": "{register_str.split(',')[0] if register_str else 'polite'}",
    "milestone": "{milestone_id}",
    "validated": true
  }},
  ...
]"""
        
        try:
            response = await self.ai_service.generate_reply(
                provider=self.default_provider,
                model=self.default_model,
                messages=[{"role": "user", "content": prompt}],
                system_prompt="You are a Japanese language learning expert. Generate level-appropriate formulaic expressions. Return only valid JSON.",
                temperature=0.3
            )
            
            content = response.get("content", "")
            if isinstance(content, str):
                try:
                    if "```json" in content:
                        start = content.find("```json") + 7
                        end = content.find("```", start)
                        content = content[start:end].strip()
                    elif "```" in content:
                        start = content.find("```") + 3
                        end = content.find("```", start)
                        content = content[start:end].strip()
                    
                    expr_list = parse_json_object(content)
                    if isinstance(expr_list, list):
                        for item in expr_list:
                            if not isinstance(item, dict):
                                continue
                            item.setdefault("milestone", milestone_id)
                            item.setdefault("level", level)
                            item.setdefault("cefr_level", cefr_level)
                            item.setdefault("register", register_str.split(',')[0] if register_str else 'polite')
                            item.setdefault("validated", True)
                        return expr_list
                    elif isinstance(expr_list, dict) and "expressions" in expr_list:
                        return expr_list["expressions"]
                except (json.JSONDecodeError, ValueError, KeyError) as e:
                    logger.warning("Failed to parse expression structures", milestone=milestone_id, error=str(e))
            return []
        except Exception as e:
            logger.warning("Failed to generate expression structures", milestone=milestone_id, error=str(e))
            return []


# Singleton instance
path_structure_service = PathStructureService()

