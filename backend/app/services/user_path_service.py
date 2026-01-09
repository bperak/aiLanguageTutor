"""
User Path Service

Main service orchestrating personalized learning path generation
from user profiles with semantic CanDo descriptor ordering.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import structlog
import uuid
import json
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from neo4j import AsyncSession as Neo4jSession

from app.models.database_models import User, UserProfile
from app.schemas.profile import LearningPathData, LearningPathStep, LearningPathMilestone
from app.services.ai_chat_service import AIChatService
from app.services.cando_selector_service import cando_selector_service
from app.services.path_builder import path_builder
from app.services.cando_complexity_service import cando_complexity_service
from app.services.prelesson_kit_service import prelesson_kit_service
from app.core.config import settings

logger = structlog.get_logger()


class UserPathService:
    """Service for generating personalized learning paths."""
    
    def __init__(self):
        self.ai_service = AIChatService()
        self.selector_service = cando_selector_service
        self.path_builder = path_builder
        self.complexity_service = cando_complexity_service
        self.default_provider = "openai"
        self.default_model = "gpt-4o"
        # Cache for pre-lesson kits to avoid regenerating for same CanDo/level
        self._kit_cache: Dict[str, Any] = {}
    
    def analyze_profile_for_path(
        self,
        profile_data: Optional[UserProfile],
        user: User
    ) -> Dict[str, Any]:
        """
        Extract path requirements from user profile.
        
        Args:
            profile_data: UserProfile object
            user: User object
            
        Returns:
            Profile context dictionary with enhanced fields
        """
        if profile_data:
            # Extract learning_goals (may be list or dict with new fields)
            learning_goals_raw = profile_data.learning_goals or []
            learning_goals = learning_goals_raw.get("goals", []) if isinstance(learning_goals_raw, dict) else (learning_goals_raw if isinstance(learning_goals_raw, list) else [])
            learning_goals_dict = learning_goals_raw if isinstance(learning_goals_raw, dict) else {}
            
            profile_context = {
                "learning_goals": learning_goals,
                "previous_knowledge": profile_data.previous_knowledge or {},
                "learning_experiences": profile_data.learning_experiences or {},
                "usage_context": profile_data.usage_context or {},
                "current_level": user.current_level or "beginner_1",
                "target_languages": user.target_languages or ["ja"],
                # New path-level structure fields
                "vocabulary_domain_goals": learning_goals_dict.get("vocabulary_domain_goals", []),
                "vocabulary_known": learning_goals_dict.get("vocabulary_known", []),
                "vocabulary_learning_target": learning_goals_dict.get("vocabulary_learning_target"),
                "vocabulary_level_preference": learning_goals_dict.get("vocabulary_level_preference"),
                "grammar_progression_goals": learning_goals_dict.get("grammar_progression_goals", []),
                "grammar_known": learning_goals_dict.get("grammar_known", []),
                "grammar_learning_target": learning_goals_dict.get("grammar_learning_target"),
                "grammar_level_preference": learning_goals_dict.get("grammar_level_preference"),
                "formulaic_expression_goals": learning_goals_dict.get("formulaic_expression_goals", []),
                "expressions_known": learning_goals_dict.get("expressions_known", []),
                "expression_learning_target": learning_goals_dict.get("expression_learning_target"),
                "expression_level_preference": learning_goals_dict.get("expression_level_preference"),
                "cultural_interests": learning_goals_dict.get("cultural_interests", []),
                "cultural_background": learning_goals_dict.get("cultural_background"),
            }
        else:
            profile_context = {
                "learning_goals": user.learning_goals or [],
                "previous_knowledge": {},
                "learning_experiences": {},
                "usage_context": {},
                "current_level": user.current_level or "beginner_1",
                "target_languages": user.target_languages or ["ja"],
                # Default empty values for new fields
                "vocabulary_domain_goals": [],
                "vocabulary_known": [],
                "vocabulary_learning_target": None,
                "vocabulary_level_preference": None,
                "grammar_progression_goals": [],
                "grammar_known": [],
                "grammar_learning_target": None,
                "grammar_level_preference": None,
                "formulaic_expression_goals": [],
                "expressions_known": [],
                "expression_learning_target": None,
                "expression_level_preference": None,
                "cultural_interests": [],
                "cultural_background": None,
            }
        
        return profile_context
    
    async def validate_cando_exists(
        self,
        neo4j_session: Neo4jSession,
        can_do_id: str
    ) -> bool:
        """
        Validate that a CanDo descriptor exists in Neo4j.
        
        Args:
            neo4j_session: Neo4j session
            can_do_id: CanDo descriptor UID
            
        Returns:
            True if CanDo exists, False otherwise
        """
        try:
            query = "MATCH (c:CanDoDescriptor {uid: $uid}) RETURN c LIMIT 1"
            result = await neo4j_session.run(query, uid=can_do_id)
            record = await result.single()
            return record is not None
        except Exception as e:
            logger.warning("Failed to validate CanDo descriptor",
                         can_do_id=can_do_id, error=str(e))
            return False
    
    async def generate_user_path(
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
            profile_data: Optional UserProfile object
            
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
            else:
                user_result = await db.execute(
                    select(User).where(User.id == user_id)
                )
                user = user_result.scalar_one_or_none()
                if not user:
                    raise ValueError(f"User {user_id} not found")
            
            # Analyze profile
            profile_context = self.analyze_profile_for_path(profile_data, user)
            
            logger.info("Generating user path",
                       user_id=str(user_id),
                       level=profile_context.get("current_level"))
            
            # Step 1: Select initial CanDo descriptors
            logger.info("Selecting initial CanDo descriptors")
            initial_candos = await self.selector_service.select_initial_candos(
                profile_context=profile_context,
                neo4j_session=neo4j_session,
                limit=200
            )
            
            if not initial_candos:
                logger.warning("No CanDo descriptors found in Neo4j, attempting to create from learning goals")
                # Try to create CanDo descriptors from learning goals
                learning_goals = profile_context.get("learning_goals", [])
                if learning_goals:
                    created_candos = []
                    for goal in learning_goals[:5]:  # Limit to first 5 goals
                        try:
                            created = await self.selector_service.create_missing_cando(
                                description=str(goal),
                                metadata={
                                    "descriptionEn": f"I can {goal}",
                                    "level": profile_context.get("current_level", "beginner_1")
                                },
                                neo4j_session=neo4j_session
                            )
                            if created:
                                created_candos.append(created)
                        except Exception as e:
                            logger.warning("Failed to create CanDo from goal", goal=goal, error=str(e))
                    
                    if created_candos:
                        logger.info("Created CanDo descriptors from learning goals", count=len(created_candos))
                        # Retry selection with newly created descriptors
                        initial_candos = await self.selector_service.select_initial_candos(
                            profile_context=profile_context,
                            neo4j_session=neo4j_session,
                            limit=200
                        )
                
                if not initial_candos:
                    logger.warning("No CanDo descriptors found after creation attempt, creating default path")
                    # Create a minimal default path
                    return self._create_default_path(profile_context)
            
            # Validate CanDo descriptors exist in Neo4j
            validated_candos = []
            for cando in initial_candos:
                can_do_id = cando.get("uid")
                if can_do_id and await self.validate_cando_exists(neo4j_session, can_do_id):
                    validated_candos.append(cando)
                else:
                    logger.warning("CanDo descriptor not found in Neo4j, skipping",
                                 uid=can_do_id)
            
            if not validated_candos:
                logger.warning("No valid CanDo descriptors found after validation, creating default path")
                return self._create_default_path(profile_context)
            
            # Use validated CanDo descriptors
            initial_candos = validated_candos
            
            # Step 2: Build semantic path
            logger.info("Building semantic path",
                       initial_candidates=len(initial_candos))
            
            path_sequence = await self.path_builder.build_semantic_path(
                starting_candos=initial_candos[:10],  # Use top 10 as starting points
                all_candos=initial_candos,
                profile_context=profile_context,
                neo4j_session=neo4j_session
            )
            
            if not path_sequence:
                logger.warning("Failed to build path sequence, creating default path")
                return self._create_default_path(profile_context)
            
            # Step 3: Generate path steps with AI
            logger.info("Generating path steps",
                       path_length=len(path_sequence))
            
            steps = await self._generate_path_steps(
                path_sequence=path_sequence,
                profile_context=profile_context,
                neo4j_session=neo4j_session
            )
            
            # Step 3.25: Generate path-level structures if profile has structure goals
            path_structures = {}
            if (profile_context.get("vocabulary_domain_goals") or 
                profile_context.get("grammar_progression_goals") or 
                profile_context.get("formulaic_expression_goals")):
                try:
                    from app.services.path_structure_service import path_structure_service
                    logger.info("Generating path-level structures")
                    path_structures = await path_structure_service.generate_path_structures(
                        path_steps=steps,
                        profile_context=profile_context,
                        neo4j_session=neo4j_session
                    )
                    logger.info("Path-level structures generated",
                               vocab_count=len(path_structures.get("vocabulary", [])),
                               grammar_count=len(path_structures.get("grammar", [])),
                               expr_count=len(path_structures.get("expressions", [])))
                except Exception as e:
                    logger.warning("Failed to generate path structures", error=str(e))
                    path_structures = {}
            
            # Step 3.5: Prefetch pre-lesson kits for first N steps (hybrid strategy)
            prefetch_n = getattr(settings, "PRELESSON_KIT_PREFETCH_N", 5)
            if prefetch_n > 0 and steps:
                logger.info("Prefetching pre-lesson kits", n=prefetch_n, total_steps=len(steps))
                await self._prefetch_prelesson_kits(
                    steps=steps[:prefetch_n],
                    profile_context=profile_context,
                    neo4j_session=neo4j_session
                )
            
            # Step 4: Generate milestones
            milestones = await self._generate_milestones(
                steps=steps,
                profile_context=profile_context
            )
            
            # Step 5: Calculate total duration
            total_days = sum(step.get("estimated_duration_days", 7) for step in steps)
            
            # Determine target level
            target_level = self._determine_target_level(
                profile_context.get("current_level", "beginner_1"),
                len(steps)
            )
            
            # Create path data
            path_data = LearningPathData(
                path_name=self._generate_path_name(profile_context),
                description=self._generate_path_description(profile_context, len(steps)),
                total_estimated_days=total_days,
                steps=[LearningPathStep(**step) for step in steps],
                milestones=[LearningPathMilestone(**milestone) for milestone in milestones],
                starting_level=profile_context.get("current_level", "beginner_1"),
                target_level=target_level,
                learning_goals=profile_context.get("learning_goals", []),
                created_at=datetime.utcnow(),
                path_structures=path_structures  # Include path-level structures for evaluation
            )
            
            logger.info("User path generated successfully",
                       user_id=str(user_id),
                       steps=len(steps),
                       total_days=total_days)
            
            return path_data
            
        except Exception as e:
            logger.error("Failed to generate user path",
                        user_id=str(user_id),
                        error=str(e))
            raise
    
    async def _generate_path_steps(
        self,
        path_sequence: List[Dict[str, Any]],
        profile_context: Dict[str, Any],
        neo4j_session: Neo4jSession
    ) -> List[Dict[str, Any]]:
        """
        Generate path steps with vocabulary, grammar, formulaic expressions, and CanDo.
        
        Args:
            path_sequence: Ordered CanDo descriptors
            profile_context: User profile context
            neo4j_session: Neo4j session for validation and kit generation
            
        Returns:
            List of step dictionaries with complete structure
        """
        steps = []
        learner_level = profile_context.get("current_level", "beginner_1")
        
        for idx, cando in enumerate(path_sequence):
            can_do_id = cando.get("uid", "")
            
            # Validate CanDo exists
            if not can_do_id or not await self.validate_cando_exists(neo4j_session, can_do_id):
                logger.warning("Skipping invalid CanDo descriptor", uid=can_do_id)
                continue
            
            step_id = f"step_{idx + 1}"
            
            # Build step description using AI
            step_description = await self._generate_step_description(
                cando=cando,
                step_number=idx + 1,
                total_steps=len(path_sequence),
                profile_context=profile_context
            )
            
            # Generate pre-lesson kit (vocabulary, grammar, formulaic expressions)
            # Only generate kit for first 3 steps to speed up path creation
            # Remaining kits will be generated on-demand when user starts the lesson
            vocabulary = []
            grammar = []
            formulaic_expressions = []

            kit = None
            if idx < 3:  # Only generate kits for first 3 steps
                try:
                    kit = await self._get_cached_kit(
                        can_do_id=can_do_id,
                        learner_level=learner_level,
                        neo4j_session=neo4j_session
                    )
                except Exception as e:
                    logger.warning("Failed to generate kit for step (skipping)",
                                 step_id=step_id,
                                 can_do_id=can_do_id,
                                 error=str(e))
                    kit = None

            if kit:
                try:
                    # Extract vocabulary from kit
                    if kit and kit.necessary_words:
                        vocabulary = []
                        for word in kit.necessary_words:
                            # Handle both dict and Pydantic model
                            if isinstance(word, dict):
                                vocabulary.append({
                                    "word": word.get("surface", ""),
                                    "reading": word.get("reading", ""),
                                    "pos": word.get("pos", ""),
                                    "translation": word.get("translation", "")
                                })
                            else:
                                # Pydantic model
                                vocabulary.append({
                                    "word": getattr(word, "surface", ""),
                                    "reading": getattr(word, "reading", ""),
                                    "pos": getattr(word, "pos", ""),
                                    "translation": getattr(word, "translation", "")
                                })
                    else:
                        vocabulary = []
                
                    # Extract grammar from kit
                    if kit and kit.necessary_grammar_patterns:
                        grammar = []
                        for pattern in kit.necessary_grammar_patterns:
                            # Handle both dict and Pydantic model
                            if isinstance(pattern, dict):
                                pattern_dict = pattern
                                examples = pattern.get("examples", [])
                            else:
                                # Pydantic model
                                pattern_dict = pattern.model_dump() if hasattr(pattern, "model_dump") else {}
                                examples = getattr(pattern, "examples", [])
                            
                            # Extract examples
                            example_list = []
                            for ex in examples:
                                if isinstance(ex, dict):
                                    example_list.append({
                                        "kanji": ex.get("kanji", ""),
                                        "romaji": ex.get("romaji", ""),
                                        "translation": ex.get("translation", "")
                                    })
                                else:
                                    # Pydantic model
                                    example_list.append({
                                        "kanji": getattr(ex, "kanji", ""),
                                        "romaji": getattr(ex, "romaji", ""),
                                        "translation": getattr(ex, "translation", "")
                                    })
                            
                            grammar.append({
                                "pattern": pattern_dict.get("pattern", "") if isinstance(pattern_dict, dict) else getattr(pattern, "pattern", ""),
                                "explanation": pattern_dict.get("explanation", "") if isinstance(pattern_dict, dict) else getattr(pattern, "explanation", ""),
                                "examples": example_list
                            })
                    else:
                        grammar = []
                
                    # Extract formulaic expressions from kit
                    if kit and kit.necessary_fixed_phrases:
                        formulaic_expressions = []
                        for phrase in kit.necessary_fixed_phrases:
                            # Handle both dict and Pydantic model
                            if isinstance(phrase, dict):
                                phrase_obj = phrase.get("phrase", {})
                                if isinstance(phrase_obj, dict):
                                    phrase_dict = {
                                        "kanji": phrase_obj.get("kanji", ""),
                                        "romaji": phrase_obj.get("romaji", ""),
                                        "translation": phrase_obj.get("translation", "")
                                    }
                                else:
                                    # Pydantic model
                                    phrase_dict = {
                                        "kanji": getattr(phrase_obj, "kanji", ""),
                                        "romaji": getattr(phrase_obj, "romaji", ""),
                                        "translation": getattr(phrase_obj, "translation", "")
                                    }
                                
                                formulaic_expressions.append({
                                    "phrase": phrase_dict,
                                    "usage_note": phrase.get("usage_note", ""),
                                    "register": phrase.get("register", "")
                                })
                            else:
                                # Pydantic model
                                phrase_obj = getattr(phrase, "phrase", None)
                                if phrase_obj:
                                    if hasattr(phrase_obj, "model_dump"):
                                        phrase_dict = phrase_obj.model_dump()
                                    elif isinstance(phrase_obj, dict):
                                        phrase_dict = phrase_obj
                                    else:
                                        phrase_dict = {
                                            "kanji": getattr(phrase_obj, "kanji", ""),
                                            "romaji": getattr(phrase_obj, "romaji", ""),
                                            "translation": getattr(phrase_obj, "translation", "")
                                        }
                                else:
                                    phrase_dict = {}
                                
                                formulaic_expressions.append({
                                    "phrase": phrase_dict,
                                    "usage_note": getattr(phrase, "usage_note", ""),
                                    "register": getattr(phrase, "register", "")
                                })
                    else:
                        formulaic_expressions = []
                
                    logger.info("Generated kit for step",
                               step_id=step_id,
                               can_do_id=can_do_id,
                               vocab_count=len(vocabulary),
                               grammar_count=len(grammar),
                               formulaic_count=len(formulaic_expressions))
                
                except Exception as e:
                    logger.warning("Failed to generate kit for step",
                                 step_id=step_id,
                                 can_do_id=can_do_id,
                                 error=str(e))
                    # Continue with empty structures - step will still be created
            
            # Determine prerequisites
            prerequisites = []
            if idx > 0:
                prerequisites = [f"step_{idx}"]
            
            # Estimate duration (default 7 days, adjust based on complexity)
            estimated_days = 7
            level = cando.get("level", "A1")
            if level in ["B1", "B2"]:
                estimated_days = 10
            elif level in ["C1", "C2"]:
                estimated_days = 14
            
            # Learning objectives
            learning_objectives = [
                f"Master the CanDo: {cando.get('descriptionEn', 'Learning objective')}",
                f"Apply knowledge in {cando.get('primaryTopicEn', 'relevant contexts')}"
            ]
            
            step = {
                "step_id": step_id,
                "title": cando.get("descriptionEn", f"Step {idx + 1}")[:100],
                "description": step_description,
                "estimated_duration_days": estimated_days,
                "prerequisites": prerequisites,
                "learning_objectives": learning_objectives,
                "vocabulary": vocabulary,  # NEW: Vocabulary for this step
                "grammar": grammar,  # NEW: Grammar patterns for this step
                "formulaic_expressions": formulaic_expressions,  # NEW: Formulaic expressions for this step
                "can_do_descriptors": [can_do_id],  # Validated CanDo ID
                "resources": [],
                "difficulty_level": self._map_level_to_difficulty(cando.get("level", "A1"))
            }
            
            steps.append(step)
        
        return steps
    
    async def _get_cached_kit(
        self,
        can_do_id: str,
        learner_level: str,
        neo4j_session: Neo4jSession
    ) -> Any:
        """
        Get pre-lesson kit with caching.
        
        Args:
            can_do_id: CanDo descriptor ID
            learner_level: Learner level
            neo4j_session: Neo4j session
            
        Returns:
            PreLessonKit object
        """
        cache_key = f"{can_do_id}:{learner_level}"
        
        if cache_key in self._kit_cache:
            logger.debug("Using cached kit", can_do_id=can_do_id, level=learner_level)
            return self._kit_cache[cache_key]
        
        # Generate kit
        kit = await prelesson_kit_service.generate_kit(
            can_do_id=can_do_id,
            learner_level=learner_level,
            neo4j_session=neo4j_session
        )
        
        # Cache it
        self._kit_cache[cache_key] = kit
        logger.debug("Cached kit", can_do_id=can_do_id, level=learner_level)
        
        return kit
    
    async def _prefetch_prelesson_kits(
        self,
        steps: List[Dict[str, Any]],
        profile_context: Dict[str, Any],
        neo4j_session: Neo4jSession
    ) -> None:
        """
        Prefetch pre-lesson kits for the first N steps.
        
        Args:
            steps: List of step dictionaries (first N steps)
            profile_context: User profile context
            neo4j_session: Neo4j session for fetching CanDo metadata
        """
        learner_level = profile_context.get("current_level")
        
        # Generate kits concurrently with a limit to avoid overwhelming the API
        semaphore = asyncio.Semaphore(3)  # Max 3 concurrent requests
        
        async def generate_kit_for_step(step: Dict[str, Any]) -> None:
            async with semaphore:
                can_do_descriptors = step.get("can_do_descriptors", [])
                if not can_do_descriptors:
                    return
                
                can_do_id = can_do_descriptors[0]  # Use first CanDo descriptor
                try:
                    kit = await prelesson_kit_service.generate_kit(
                        can_do_id=can_do_id,
                        learner_level=learner_level,
                        neo4j_session=neo4j_session
                    )
                    step["prelesson_kit"] = kit.model_dump()
                    logger.info("prelesson_kit_prefetched", step_id=step.get("step_id"), can_do_id=can_do_id)
                except Exception as e:
                    logger.warning("prelesson_kit_prefetch_failed", step_id=step.get("step_id"), can_do_id=can_do_id, error=str(e))
                    # Continue without kit - it can be generated lazily later
        
        # Run all kit generations concurrently
        tasks = [generate_kit_for_step(step) for step in steps]
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _generate_step_description(
        self,
        cando: Dict[str, Any],
        step_number: int,
        total_steps: int,
        profile_context: Dict[str, Any]
    ) -> str:
        """
        Generate step description using AI.
        
        Args:
            cando: CanDo descriptor
            step_number: Step number in path
            total_steps: Total number of steps
            profile_context: User profile context
            
        Returns:
            Step description text
        """
        try:
            system_prompt = """You are an expert language learning path creator. 
Generate a clear, motivating description for a learning step that explains what the learner will accomplish."""
            
            user_prompt = f"""Create a learning step description for:

CanDo Descriptor: {cando.get('descriptionEn', '')}
Level: {cando.get('level', 'A1')}
Topic: {cando.get('primaryTopicEn', '')}
Step: {step_number} of {total_steps}

User Context:
- Goals: {json.dumps(profile_context.get('learning_goals', []), ensure_ascii=False)}
- Current Level: {profile_context.get('current_level', 'beginner_1')}

Write a 2-3 sentence description that:
1. Explains what the learner will learn
2. Connects it to their goals
3. Motivates them to continue

Description:"""
            
            response = await self.ai_service.generate_reply(
                provider=self.default_provider,
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_output_tokens=200
            )
            
            description = response.get("content", "").strip()
            if not description:
                description = f"In this step, you will learn {cando.get('descriptionEn', 'new language skills')}."
            
            return description
            
        except Exception as e:
            logger.warning("Failed to generate step description with AI",
                         error=str(e))
            return f"In this step, you will learn {cando.get('descriptionEn', 'new language skills')}."
    
    async def _generate_milestones(
        self,
        steps: List[Dict[str, Any]],
        profile_context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Generate learning milestones.
        
        Args:
            steps: List of path steps
            profile_context: User profile context
            
        Returns:
            List of milestone dictionaries
        """
        milestones = []
        total_steps = len(steps)
        
        # Create milestones at 25%, 50%, 75%, and 100%
        milestone_points = [0.25, 0.5, 0.75, 1.0]
        
        for point in milestone_points:
            step_idx = int(total_steps * point) - 1
            if step_idx < 0:
                step_idx = 0
            if step_idx >= total_steps:
                step_idx = total_steps - 1
            
            milestone_id = f"milestone_{int(point * 100)}"
            required_steps = [f"step_{i+1}" for i in range(step_idx + 1)]
            
            milestone = {
                "milestone_id": milestone_id,
                "title": f"{int(point * 100)}% Complete",
                "description": f"You've completed {int(point * 100)}% of your learning path!",
                "target_date": None,
                "steps_required": required_steps,
                "celebration_message": f"Congratulations on reaching {int(point * 100)}% completion! Keep up the great work!"
            }
            
            milestones.append(milestone)
        
        return milestones
    
    def _determine_target_level(
        self,
        starting_level: str,
        num_steps: int
    ) -> str:
        """Determine target level based on starting level and path length."""
        level_progression = {
            "beginner_1": ["beginner_2", "intermediate_1", "intermediate_2"],
            "beginner_2": ["intermediate_1", "intermediate_2", "advanced_1"],
            "intermediate_1": ["intermediate_2", "advanced_1", "advanced_2"],
            "intermediate_2": ["advanced_1", "advanced_2"],
            "advanced_1": ["advanced_2"],
            "advanced_2": ["advanced_2"]
        }
        
        progression = level_progression.get(starting_level, ["intermediate_1"])
        
        # Estimate progression based on steps
        if num_steps >= 15:
            return progression[-1] if len(progression) > 0 else starting_level
        elif num_steps >= 10:
            return progression[1] if len(progression) > 1 else progression[0] if len(progression) > 0 else starting_level
        else:
            return progression[0] if len(progression) > 0 else starting_level
    
    def _generate_path_name(self, profile_context: Dict[str, Any]) -> str:
        """Generate path name from profile context."""
        goals = profile_context.get("learning_goals", [])
        if goals:
            goal_name = goals[0].title() if isinstance(goals[0], str) else "Learning"
            return f"{goal_name} Focus Path"
        return "Personalized Learning Path"
    
    def _generate_path_description(
        self,
        profile_context: Dict[str, Any],
        num_steps: int
    ) -> str:
        """Generate path description."""
        goals = profile_context.get("learning_goals", [])
        level = profile_context.get("current_level", "beginner_1")
        
        goal_text = ", ".join(goals[:3]) if goals else "language learning"
        
        return f"A personalized {num_steps}-step learning path starting at {level} level, focused on {goal_text}."
    
    def _map_level_to_difficulty(self, level: str) -> str:
        """Map CEFR level to difficulty level."""
        if level in ["A1", "A2"]:
            return "beginner"
        elif level in ["B1", "B2"]:
            return "intermediate"
        else:
            return "advanced"
    
    def _create_default_path(self, profile_context: Dict[str, Any]) -> LearningPathData:
        """Create a default path when no CanDo descriptors are available."""
        return LearningPathData(
            path_name="Default Learning Path",
            description="A basic learning path to get you started.",
            total_estimated_days=30,
            path_structures={},  # Empty structures for default path
            steps=[
                LearningPathStep(
                    step_id="step_1",
                    title="Getting Started",
                    description="Begin your language learning journey.",
                    estimated_duration_days=7,
                    prerequisites=[],
                    learning_objectives=["Get familiar with basic concepts"],
                    vocabulary=[],  # Empty vocabulary for default path
                    grammar=[],  # Empty grammar for default path
                    formulaic_expressions=[],  # Empty formulaic expressions for default path
                    can_do_descriptors=[],
                    resources=[],
                    difficulty_level="beginner"
                )
            ],
            milestones=[],
            starting_level=profile_context.get("current_level", "beginner_1"),
            target_level="beginner_2",
            learning_goals=profile_context.get("learning_goals", []),
            created_at=datetime.utcnow()
        )


# Singleton instance
user_path_service = UserPathService()

