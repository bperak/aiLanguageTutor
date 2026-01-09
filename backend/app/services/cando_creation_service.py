"""
Service for creating CanDoDescriptors with automatic processing.

This service handles:
- Translation of descriptions (if only one language provided)
- AI-based field inference (level, topic, skillDomain, type)
- Title generation
- Embedding generation
- Similarity relationship creation
"""

from __future__ import annotations

from typing import Dict, Optional, Any
import structlog
from datetime import datetime
from neo4j import AsyncSession

from app.services.ai_chat_service import AIChatService
from app.services.cando_title_service import CanDoTitleService
from app.services.cando_embedding_service import CanDoEmbeddingService
from app.services.prelesson_kit_service import prelesson_kit_service

logger = structlog.get_logger()


class CanDoCreationService:
    """Service for creating CanDoDescriptors with automatic processing."""
    
    def __init__(self):
        self.ai_service = AIChatService()
        self.title_service = CanDoTitleService()
        self.embedding_service = CanDoEmbeddingService()
        self.default_provider = "openai"
        self.default_model = "gpt-4o-mini"
    
    async def translate_description(
        self,
        description: str,
        source_lang: str,
        target_lang: str
    ) -> str:
        """
        Translate a description from one language to another using AI.
        
        Args:
            description: Description text to translate
            source_lang: Source language ("en" or "ja")
            target_lang: Target language ("en" or "ja")
            
        Returns:
            Translated description
        """
        if source_lang == target_lang:
            return description
        
        if source_lang not in ["en", "ja"] or target_lang not in ["en", "ja"]:
            raise ValueError("Languages must be 'en' or 'ja'")
        
        lang_names = {"en": "English", "ja": "Japanese"}
        
        system_prompt = (
            "You are a professional translator specializing in language learning materials. "
            "Translate the Can-Do descriptor text accurately, maintaining the meaning and "
            "appropriate level of formality for language learning contexts."
        )
        
        user_prompt = (
            f"Translate this Can-Do descriptor from {lang_names[source_lang]} to {lang_names[target_lang]}:\n\n"
            f"{description}\n\n"
            f"Translation:"
        )
        
        try:
            response = await self.ai_service.generate_reply(
                provider=self.default_provider,
                model=self.default_model,
                system_prompt=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
                temperature=0.2,
                max_output_tokens=200
            )
            
            translated = response.get("content", "").strip()
            translated = translated.strip('"\'')
            
            logger.info("Translated CanDo description", 
                       source=source_lang, 
                       target=target_lang,
                       length=len(translated))
            return translated
            
        except Exception as e:
            logger.error("Failed to translate CanDo description",
                        source=source_lang,
                        target=target_lang,
                        error=str(e))
            raise
    
    async def infer_cando_fields(
        self,
        description_en: Optional[str],
        description_ja: Optional[str]
    ) -> Dict[str, Any]:
        """
        Use AI to infer CanDoDescriptor fields from descriptions.
        
        Infers: level, primaryTopic, primaryTopicEn, skillDomain, type
        
        Args:
            description_en: English description
            description_ja: Japanese description
            
        Returns:
            Dictionary with inferred fields
        """
        # Build description text
        description_parts = []
        if description_en:
            description_parts.append(f"English: {description_en}")
        if description_ja:
            description_parts.append(f"Japanese: {description_ja}")
        
        description_text = "\n".join(description_parts)
        
        system_prompt = (
            "You are a language learning curriculum expert. "
            "Analyze the Can-Do descriptor and extract structured information. "
            "Return a JSON object with the following fields:\n"
            "- level: CEFR level (A1, A2, B1, B2, C1, or C2)\n"
            "- primaryTopic: Main topic in Japanese (e.g., '旅行と交通', '食べ物')\n"
            "- primaryTopicEn: Main topic in English (e.g., 'Travel and Transportation', 'Food')\n"
            "- skillDomain: Skill domain in Japanese (one of: '産出', '受容', 'やりとり')\n"
            "- type: Type in Japanese (typically '言語活動' or similar)\n\n"
            "Be precise and consistent with standard JF Can-Do descriptor formats."
        )
        
        user_prompt = (
            f"Analyze this Can-Do descriptor and extract the fields:\n\n"
            f"{description_text}\n\n"
            f"Return only valid JSON with the fields: level, primaryTopic, primaryTopicEn, skillDomain, type"
        )
        
        try:
            response = await self.ai_service.generate_reply(
                provider=self.default_provider,
                model=self.default_model,
                system_prompt=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
                temperature=0.1,
                max_output_tokens=200,
                force_json=True
            )
            
            import json
            content = response.get("content", "{}")
            
            # Try to parse JSON (handle markdown code blocks if present)
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            inferred = json.loads(content)
            
            # Validate and set defaults
            level = inferred.get("level", "A1")
            if level not in ["A1", "A2", "B1", "B2", "C1", "C2"]:
                level = "A1"
            
            primary_topic = inferred.get("primaryTopic", "その他")
            primary_topic_en = inferred.get("primaryTopicEn", "Other")
            skill_domain = inferred.get("skillDomain", "やりとり")
            type_field = inferred.get("type", "言語活動")
            
            logger.info("Inferred CanDo fields",
                       level=level,
                       topic=primary_topic)
            
            return {
                "level": level,
                "primaryTopic": primary_topic,
                "primaryTopicEn": primary_topic_en,
                "skillDomain": skill_domain,
                "type": type_field
            }
            
        except Exception as e:
            logger.error("Failed to infer CanDo fields", error=str(e))
            # Return safe defaults
            return {
                "level": "A1",
                "primaryTopic": "その他",
                "primaryTopicEn": "Other",
                "skillDomain": "やりとり",
                "type": "言語活動"
            }
    
    async def _generate_uid(self, session: AsyncSession) -> str:
        """
        Generate a unique UID for a new CanDoDescriptor.
        
        Format: "manual:{timestamp}:{counter}"
        """
        import time
        timestamp = int(time.time())
        base_uid = f"manual:{timestamp}"
        
        # Check if UID exists, if so append counter
        result = await session.run(
            "MATCH (c:CanDoDescriptor {uid: $uid}) RETURN c.uid AS uid LIMIT 1",
            {"uid": base_uid}
        )
        if await result.single():
            # If exists, try with counter
            counter = 1
            while True:
                uid = f"{base_uid}:{counter}"
                result = await session.run(
                    "MATCH (c:CanDoDescriptor {uid: $uid}) RETURN c.uid AS uid LIMIT 1",
                    {"uid": uid}
                )
                if not await result.single():
                    return uid
                counter += 1
                if counter > 1000:  # Safety limit
                    raise RuntimeError("Failed to generate unique UID")
        
        return base_uid
    
    async def create_cando_with_auto_processing(
        self,
        description_en: Optional[str] = None,
        description_ja: Optional[str] = None,
        session: AsyncSession = None,
        include_prelesson_kit: bool = True
    ) -> Dict[str, Any]:
        """
        Create a new CanDoDescriptor with automatic processing.
        
        Processing includes:
        1. Translation (if only one description provided)
        2. Field inference (level, topic, skillDomain, type)
        3. Title generation (titleEn, titleJa)
        4. Embedding generation
        5. Similarity relationship creation
        6. PreLessonKit generation (if include_prelesson_kit=True)
        
        Args:
            description_en: English description (optional)
            description_ja: Japanese description (optional)
            session: Neo4j async session
            include_prelesson_kit: Whether to generate and persist PreLessonKit (default: True)
            
        Returns:
            Created CanDoDescriptor with all properties (may include prelesson_kit if generated)
        """
        if not description_en and not description_ja:
            raise ValueError("At least one description (en or ja) must be provided")
        
        # Step 1: Translate if needed
        if description_en and not description_ja:
            logger.info("Translating English description to Japanese")
            description_ja = await self.translate_description(description_en, "en", "ja")
        elif description_ja and not description_en:
            logger.info("Translating Japanese description to English")
            description_en = await self.translate_description(description_ja, "ja", "en")
        
        # Step 2: Infer fields using AI
        logger.info("Inferring CanDo fields from descriptions")
        inferred_fields = await self.infer_cando_fields(description_en, description_ja)
        
        # Step 3: Generate titles
        logger.info("Generating CanDo titles")
        titles = await self.title_service.generate_titles(description_en, description_ja)
        
        # Step 4: Generate UID
        uid = await self._generate_uid(session)
        
        # Step 5: Create CanDoDescriptor node
        logger.info("Creating CanDoDescriptor node", uid=uid)
        await session.run(
            """
            CREATE (c:CanDoDescriptor {
                uid: $uid,
                entryNumber: $entryNumber,
                source: $source,
                level: $level,
                primaryTopic: $primaryTopic,
                primaryTopicEn: $primaryTopicEn,
                skillDomain: $skillDomain,
                type: $type,
                descriptionEn: $descriptionEn,
                descriptionJa: $descriptionJa,
                titleEn: $titleEn,
                titleJa: $titleJa,
                createdAt: datetime()
            })
            RETURN c.uid AS uid
            """,
            {
                "uid": uid,
                "entryNumber": 0,  # Manual entries don't have entry numbers
                "source": "manual",
                "level": inferred_fields["level"],
                "primaryTopic": inferred_fields["primaryTopic"],
                "primaryTopicEn": inferred_fields["primaryTopicEn"],
                "skillDomain": inferred_fields["skillDomain"],
                "type": inferred_fields["type"],
                "descriptionEn": description_en,
                "descriptionJa": description_ja,
                "titleEn": titles["titleEn"],
                "titleJa": titles["titleJa"]
            }
        )
        
        # Step 6: Generate embedding
        logger.info("Generating embedding for new CanDo", uid=uid)
        await self.embedding_service.update_cando_embedding(
            session,
            uid,
            description_en=description_en,
            description_ja=description_ja
        )
        
        # Step 7: Create similarity relationships
        logger.info("Creating similarity relationships", uid=uid)
        await self.embedding_service.update_similarity_for_cando(session, uid)
        
        # Step 8: Generate and persist PreLessonKit (if requested)
        prelesson_kit = None
        if include_prelesson_kit:
            try:
                logger.info("Generating PreLessonKit for new CanDo", uid=uid)
                # Use inferred CEFR level as the key
                level_key = inferred_fields["level"]
                prelesson_kit = await prelesson_kit_service.generate_kit(
                    can_do_id=uid,
                    learner_level=level_key,
                    neo4j_session=session
                )
                
                # Persist as per-level cache in prelessonKitsJson
                import json
                kits_dict = {level_key: prelesson_kit.model_dump(mode="python")}
                kits_json = json.dumps(kits_dict, ensure_ascii=False)
                
                await session.run(
                    """
                    MATCH (c:CanDoDescriptor {uid: $uid})
                    SET c.prelessonKitsJson = $kits_json
                    """,
                    {"uid": uid, "kits_json": kits_json}
                )
                
                logger.info("PreLessonKit generated and persisted", 
                           uid=uid, 
                           level_key=level_key,
                           words_count=len(prelesson_kit.necessary_words),
                           grammar_count=len(prelesson_kit.necessary_grammar_patterns),
                           phrases_count=len(prelesson_kit.necessary_fixed_phrases))
            except Exception as kit_err:
                logger.warning("PreLessonKit generation failed during CanDo creation",
                             uid=uid,
                             error=str(kit_err))
                # Continue without kit - CanDo creation still succeeds
        
        # Step 9: Fetch and return created node
        result = await session.run(
            """
            MATCH (c:CanDoDescriptor {uid: $uid})
            RETURN c.uid AS uid,
                   c.level AS level,
                   c.primaryTopic AS primaryTopic,
                   c.primaryTopicEn AS primaryTopicEn,
                   c.skillDomain AS skillDomain,
                   c.type AS type,
                   c.descriptionEn AS descriptionEn,
                   c.descriptionJa AS descriptionJa,
                   c.titleEn AS titleEn,
                   c.titleJa AS titleJa,
                   c.source AS source
            """,
            {"uid": uid}
        )
        
        record = await result.single()
        if not record:
            raise RuntimeError(f"Failed to retrieve created CanDoDescriptor: {uid}")
        
        created = dict(record)
        
        # Include prelesson_kit in response if generated
        if prelesson_kit:
            created["prelesson_kit"] = prelesson_kit.model_dump(mode="python")
        
        logger.info("Successfully created CanDoDescriptor with auto-processing", uid=uid)
        
        return created

