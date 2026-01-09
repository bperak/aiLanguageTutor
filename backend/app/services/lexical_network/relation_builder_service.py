"""
Relation Builder Service

Core service orchestrating AI-driven lexical relation building with full metadata tracking.
"""

import json
from typing import Dict, List, Optional, Tuple

import structlog

from app.schemas.lexical_network import BuildResult, RelationCandidate
from app.services.lexical_network.ai_providers import AIProviderManager
from app.services.lexical_network.prompts import LexicalPromptBuilder
from app.services.lexical_network.relation_types import (
    get_valid_relations_for_pos,
    is_symmetric_relation,
    validate_relation_for_pos,
)
from app.services.lexical_network.vocabularies import (
    validate_aligned_arrays,
    validate_domain_tag,
    validate_context_tag,
    validate_register_tag,
)
from app.services.lexical_network.word_resolution import resolve_target_word

logger = structlog.get_logger()


class RelationBuilderService:
    """Service for AI-driven lexical relation building."""
    
    def __init__(self):
        self.prompt_builder = LexicalPromptBuilder()
        self.provider_manager = AIProviderManager()
    
    async def build_relations_for_word(
        self,
        neo4j_session,
        word: str,
        config,
    ) -> BuildResult:
        """
        Build lexical relations for a single word.
        
        Args:
            neo4j_session: Neo4j async session
            word: Target word (kanji/standard_orthography)
            config: JobConfig with model, relation_types, etc.
            
        Returns:
            BuildResult with statistics
        """
        try:
            # 1. Fetch word data
            word_data = await self._fetch_word_data(neo4j_session, word)
            if not word_data:
                raise ValueError(f"Word not found: {word}")
            
            pos = word_data.get("pos_primary", "名詞")
            
            # 2. Get embedding candidates
            candidates = await self._get_embedding_candidates(
                neo4j_session, word, pos_filter=pos, limit=50
            )
            
            # 3. Build prompt
            prompt = self.prompt_builder.build_relation_prompt(
                word_data=word_data,
                candidates=candidates,
                relation_types=config.relation_types,
                pos=pos,
                max_results=config.batch_size,
            )
            system_prompt = self.prompt_builder.build_system_prompt()
            
            # 4. Get AI provider and generate (temperature=0)
            provider = self.provider_manager.get_provider(config.model)
            ai_result = await provider.generate_relations(
                prompt=prompt,
                system_prompt=system_prompt,
                max_tokens=4096,
            )
            
            # 5. Parse and validate
            relation_candidates = self._parse_ai_response(
                ai_result.content, pos, word_data.get("standard_orthography", word)
            )
            
            # 6. Enrich with AI metadata
            for candidate in relation_candidates:
                candidate.ai_provider = ai_result.provider
                candidate.ai_model = ai_result.model
                candidate.ai_temperature = ai_result.temperature
                candidate.ai_request_id = ai_result.request_id
            
            # 7. Resolve targets to existing Word nodes
            resolved_candidates, resolution_stats = await self._resolve_targets(
                neo4j_session, relation_candidates, pos
            )
            
            # 8. Create Neo4j relationships with full metadata
            stats = await self._create_relations_with_metadata(
                neo4j_session, resolved_candidates, ai_result
            )
            
            return BuildResult(
                word=word,
                candidates_found=len(relation_candidates),
                relations_created=stats["created"],
                relations_updated=stats["updated"],
                errors=stats["errors"],
                tokens_input=ai_result.tokens_input,
                tokens_output=ai_result.tokens_output,
                cost_usd=ai_result.cost_usd,
                latency_ms=ai_result.latency_ms,
                model_used=ai_result.model,
                targets_attempted=resolution_stats["attempted"],
                targets_resolved=resolution_stats["resolved"],
                targets_dropped_not_found=resolution_stats["not_found"],
                targets_dropped_ambiguous=resolution_stats["ambiguous"],
                dropped_not_found_samples=resolution_stats["not_found_samples"][:10],  # Limit to 10
                dropped_ambiguous_samples=resolution_stats["ambiguous_samples"][:10],  # Limit to 10
            )
        except Exception as e:
            logger.error("Failed to build relations", word=word, error=str(e))
            raise
    
    async def _fetch_word_data(
        self,
        session,
        word: str,
    ) -> Optional[Dict]:
        """Fetch comprehensive word data from Neo4j."""
        query = """
        MATCH (w:Word)
        WHERE w.standard_orthography = $word
        OPTIONAL MATCH (w)-[r:LEXICAL_RELATION]-()
        RETURN w {
            .standard_orthography, .reading_hiragana, .translation, .pos_primary,
            .etymology, .difficulty_numeric, .jlpt_level
        } AS word_data,
        coalesce(w.pos_primary_norm, w.pos1, w.pos_primary, "名詞") AS pos_primary,
        coalesce(w.domain_tags, []) AS domains,
        count(DISTINCT r) AS existing_relations
        """
        
        result = await session.run(query, word=word)
        record = await result.single()
        
        if not record:
            return None
        
        word_data = dict(record["word_data"]) if record["word_data"] else {}
        word_data["pos_primary"] = record.get("pos_primary", "名詞")
        word_data["domains"] = record.get("domains", [])
        word_data["existing_relations"] = record.get("existing_relations", 0)
        
        return word_data
    
    async def _get_embedding_candidates(
        self,
        session,
        word: str,
        pos_filter: Optional[str],
        limit: int = 50,
    ) -> List[Dict]:
        """Get candidate words using existing synonym edges (no embeddings)."""
        query = """
        MATCH (source:Word)
        WHERE source.standard_orthography = $word
        MATCH (source)-[r:SYNONYM_OF]-(target:Word)
        WHERE ($pos_filter IS NULL OR coalesce(target.pos_primary_norm, target.pos1, target.pos_primary) = $pos_filter)
        RETURN target.standard_orthography AS word,
               target.reading_hiragana AS reading,
               target.translation AS translation,
               coalesce(target.pos_primary_norm, target.pos1, target.pos_primary) AS pos,
               target.etymology AS etymology,
               coalesce(r.synonym_strength, 0.5) AS similarity
        ORDER BY similarity DESC
        LIMIT $limit
        """
        result = await session.run(query, word=word, pos_filter=pos_filter, limit=limit)
        return [dict(record) for record in await result.data()]
    
    def _parse_ai_response(
        self, content: str, pos: str, source_word: str
    ) -> List[RelationCandidate]:
        """Parse AI response JSON into RelationCandidate objects."""
        try:
            # Clean up the response text
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            # Parse JSON
            data = json.loads(content)
            
            # Handle both array and object with "relations" key
            if isinstance(data, dict):
                relations = data.get("relations", [])
            elif isinstance(data, list):
                relations = data
            else:
                logger.warning("Unexpected AI response format", content=content[:200])
                return []
            
            candidates = []
            valid_relations = get_valid_relations_for_pos(pos)
            
            for rel_data in relations:
                try:
                    # Validate relation type
                    rel_type = rel_data.get("relation_type", "")
                    if rel_type not in valid_relations:
                        logger.warning(
                            "Invalid relation type for POS",
                            relation_type=rel_type,
                            pos=pos,
                        )
                        continue
                    
                    # Extract target_orthography and target_reading (new format)
                    # Backward compatibility: if target_orthography missing, use target_word
                    target_orthography = rel_data.get("target_orthography") or rel_data.get("target_word", "")
                    target_reading = rel_data.get("target_reading")
                    
                    if not target_orthography:
                        continue
                    
                    # Set defaults
                    rel_data.setdefault("source_word", source_word)
                    rel_data.setdefault("relation_category", pos)
                    rel_data.setdefault("is_symmetric", is_symmetric_relation(rel_type))
                    rel_data.setdefault("register_source", "neutral")
                    rel_data.setdefault("register_target", "neutral")
                    rel_data.setdefault("formality_difference", "same")
                    rel_data.setdefault("domain_tags", [])
                    rel_data.setdefault("domain_weights", [])
                    rel_data.setdefault("context_tags", [])
                    rel_data.setdefault("context_weights", [])
                    
                    # Store raw fields for resolution
                    rel_data["target_orthography"] = target_orthography
                    rel_data["target_reading"] = target_reading
                    # Set target_word to orthography initially (will be overwritten with resolved canonical key)
                    rel_data["target_word"] = target_orthography
                    
                    # Normalize relation_category (guard against "None" or null from model)
                    if not rel_data.get("relation_category") or str(rel_data.get("relation_category")).lower() == "none":
                        rel_data["relation_category"] = pos or "lexical"

                    # Align domain/context arrays (trim/pad to match tags length)
                    def _align(tags: List[str], weights: List[float]) -> (List[str], List[float]):
                        tags = tags or []
                        weights = weights or []
                        if not tags:
                            return [], []
                        if len(weights) > len(tags):
                            weights = weights[: len(tags)]
                        elif len(weights) < len(tags):
                            # pad with 0.0 to match length
                            weights = weights + [0.0] * (len(tags) - len(weights))
                        return tags, weights

                    rel_data["domain_tags"], rel_data["domain_weights"] = _align(
                        rel_data.get("domain_tags"), rel_data.get("domain_weights")
                    )
                    rel_data["context_tags"], rel_data["context_weights"] = _align(
                        rel_data.get("context_tags"), rel_data.get("context_weights")
                    )
                    
                    # Validate aligned arrays
                    if not validate_aligned_arrays(
                        rel_data["domain_tags"], rel_data["domain_weights"]
                    ):
                        logger.warning("Invalid domain arrays alignment", rel_data=rel_data)
                        rel_data["domain_tags"] = []
                        rel_data["domain_weights"] = []
                    
                    if not validate_aligned_arrays(
                        rel_data["context_tags"], rel_data["context_weights"]
                    ):
                        logger.warning("Invalid context arrays alignment", rel_data=rel_data)
                        rel_data["context_tags"] = []
                        rel_data["context_weights"] = []
                    
                    # Validate tags against vocabularies
                    rel_data["domain_tags"] = [
                        tag for tag in rel_data["domain_tags"] if validate_domain_tag(tag)
                    ]
                    rel_data["context_tags"] = [
                        tag for tag in rel_data["context_tags"] if validate_context_tag(tag)
                    ]
                    # Re-align after filtering invalid tags
                    rel_data["domain_tags"], rel_data["domain_weights"] = _align(
                        rel_data.get("domain_tags"), rel_data.get("domain_weights")
                    )
                    rel_data["context_tags"], rel_data["context_weights"] = _align(
                        rel_data.get("context_tags"), rel_data.get("context_weights")
                    )
                    if not validate_register_tag(rel_data["register_source"]):
                        rel_data["register_source"] = "neutral"
                    if not validate_register_tag(rel_data["register_target"]):
                        rel_data["register_target"] = "neutral"
                    
                    # Create candidate
                    candidate = RelationCandidate(**rel_data)
                    candidates.append(candidate)
                except Exception as e:
                    logger.warning("Failed to parse relation candidate", error=str(e), data=rel_data)
                    continue
            
            return candidates
        except json.JSONDecodeError as e:
            logger.error("Failed to parse AI response as JSON", error=str(e), content=content[:500])
            return []
        except Exception as e:
            logger.error("Unexpected error parsing AI response", error=str(e))
            return []
    
    async def _resolve_targets(
        self,
        session,
        candidates: List[RelationCandidate],
        expected_pos: str,
    ) -> Tuple[List[RelationCandidate], Dict]:
        """
        Resolve AI-proposed target words to existing Neo4j Word nodes.
        
        Args:
            session: Neo4j async session
            candidates: List of relation candidates with target_orthography/target_reading
            expected_pos: Expected POS (e.g., "形容詞")
            
        Returns:
            Tuple of (resolved_candidates, resolution_stats)
        """
        resolved = []
        stats = {
            "attempted": len(candidates),
            "resolved": 0,
            "not_found": 0,
            "ambiguous": 0,
            "not_found_samples": [],
            "ambiguous_samples": [],
        }
        
        # Determine expected POS list for resolution
        expected_pos_list = None
        # Include both legacy and canonical formats for adjectives
        adjective_pos = {"形容詞", "形容動詞", "形状詞", "イ形容詞", "ナ形容詞"}
        if expected_pos in adjective_pos:
            # Allow both i-adj and na-adj variants to match (legacy and canonical)
            expected_pos_list = list(adjective_pos)
        elif expected_pos:
            expected_pos_list = [expected_pos]
        
        for candidate in candidates:
            target_orthography = candidate.target_orthography or candidate.target_word
            target_reading = candidate.target_reading
            
            if not target_orthography:
                stats["not_found"] += 1
                continue
            
            # Resolve target
            resolved_key, status, metadata = await resolve_target_word(
                session,
                target_orthography=target_orthography,
                target_reading=target_reading,
                expected_pos=expected_pos_list,
            )
            
            if status == "resolved" and resolved_key:
                # Set resolved canonical word key
                candidate.target_word = resolved_key
                # Store resolution metadata on candidate (will be written to relationship)
                candidate.target_resolution_method = metadata.get("method", "ranked_match")
                candidate.target_resolution_confidence = metadata.get("confidence", 1.0)
                resolved.append(candidate)
                stats["resolved"] += 1
            elif status == "not_found":
                stats["not_found"] += 1
                sample = f"{target_orthography}|{target_reading or ''}"
                if sample not in stats["not_found_samples"]:
                    stats["not_found_samples"].append(sample)
                logger.info(
                    "Target resolution not found",
                    target_orthography=target_orthography,
                    target_reading=target_reading,
                    expected_pos=expected_pos_list,
                )
            elif status == "ambiguous":
                stats["ambiguous"] += 1
                sample = f"{target_orthography}|{target_reading or ''}"
                if sample not in stats["ambiguous_samples"]:
                    stats["ambiguous_samples"].append(sample)
                logger.warning(
                    "Ambiguous target resolution",
                    target_orthography=target_orthography,
                    target_reading=target_reading,
                    metadata=metadata,
                )
        
        return resolved, stats
    
    async def _create_relations_with_metadata(
        self,
        session,
        candidates: List[RelationCandidate],
        ai_result,
    ) -> Dict[str, int]:
        """Create relations with full AI generation metadata."""
        stats = {"created": 0, "updated": 0, "errors": 0}
        
        prompt_version = self.prompt_builder.PROMPT_VERSION
        
        for candidate in candidates:
            try:
                query = """
                MATCH (source:Word), (target:Word)
        WHERE source.standard_orthography = $source_word
          AND target.standard_orthography = $target_word
                
                MERGE (source)-[r:LEXICAL_RELATION {
                    relation_type: $relation_type
                }]->(target)
                
                ON CREATE SET
                    r.relation_category = $relation_category,
                    r.weight = $weight,
                    r.confidence = $confidence,
                    r.emb_sim = $emb_sim,
                    r.is_symmetric = $is_symmetric,
                    r.shared_meaning_en = $shared_meaning_en,
                    r.distinction_en = $distinction_en,
                    r.usage_context_en = $usage_context_en,
                    r.when_prefer_source_en = $when_prefer_source_en,
                    r.when_prefer_target_en = $when_prefer_target_en,
                    r.register_source = $register_source,
                    r.register_target = $register_target,
                    r.formality_difference = $formality_difference,
                    r.scale_dimension = $scale_dimension,
                    r.scale_position_source = $scale_position_source,
                    r.scale_position_target = $scale_position_target,
                    r.aspect_source = $aspect_source,
                    r.aspect_target = $aspect_target,
                    r.transitivity_source = $transitivity_source,
                    r.transitivity_target = $transitivity_target,
                    r.domain_tags = $domain_tags,
                    r.domain_weights = $domain_weights,
                    r.context_tags = $context_tags,
                    r.context_weights = $context_weights,
                    r.ai_provider = $ai_provider,
                    r.ai_model = $ai_model,
                    r.ai_model_version = $ai_model_version,
                    r.ai_temperature = $ai_temperature,
                    r.ai_prompt_version = $ai_prompt_version,
                    r.ai_tokens_input = $ai_tokens_input,
                    r.ai_tokens_output = $ai_tokens_output,
                    r.ai_cost_usd = $ai_cost_usd,
                    r.ai_latency_ms = $ai_latency_ms,
                    r.ai_request_id = $ai_request_id,
                    r.ai_target_orthography_raw = $ai_target_orthography_raw,
                    r.ai_target_reading_raw = $ai_target_reading_raw,
                    r.target_resolution_method = $target_resolution_method,
                    r.target_resolution_confidence = $target_resolution_confidence,
                    r.source = 'ai_generated',
                    r.created_utc = datetime()
                
                ON MATCH SET
                    r.weight = $weight,
                    r.confidence = $confidence,
                    r.updated_utc = datetime()
                
                RETURN 
                    CASE WHEN r.created_utc = datetime() THEN 'created' ELSE 'updated' END AS action
                """
                
                result = await session.run(
                    query,
                    source_word=candidate.source_word,
                    target_word=candidate.target_word,
                    relation_type=candidate.relation_type,
                    relation_category=candidate.relation_category,
                    weight=candidate.weight,
                    confidence=candidate.confidence,
                    emb_sim=0.0,  # Will be computed separately if needed
                    is_symmetric=candidate.is_symmetric,
                    shared_meaning_en=candidate.shared_meaning_en,
                    distinction_en=candidate.distinction_en,
                    usage_context_en=candidate.usage_context_en,
                    when_prefer_source_en=candidate.when_prefer_source_en or "",
                    when_prefer_target_en=candidate.when_prefer_target_en or "",
                    register_source=candidate.register_source,
                    register_target=candidate.register_target,
                    formality_difference=candidate.formality_difference,
                    scale_dimension=candidate.scale_dimension,
                    scale_position_source=candidate.scale_position_source,
                    scale_position_target=candidate.scale_position_target,
                    aspect_source=candidate.aspect_source,
                    aspect_target=candidate.aspect_target,
                    transitivity_source=candidate.transitivity_source,
                    transitivity_target=candidate.transitivity_target,
                    domain_tags=candidate.domain_tags,
                    domain_weights=candidate.domain_weights,
                    context_tags=candidate.context_tags,
                    context_weights=candidate.context_weights,
                    ai_provider=ai_result.provider,
                    ai_model=ai_result.model,
                    ai_model_version=ai_result.model_version or ai_result.model,
                    ai_temperature=ai_result.temperature,
                    ai_prompt_version=prompt_version,
                    ai_tokens_input=ai_result.tokens_input,
                    ai_tokens_output=ai_result.tokens_output,
                    ai_cost_usd=ai_result.cost_usd,
                    ai_latency_ms=ai_result.latency_ms,
                    ai_request_id=ai_result.request_id,
                    ai_target_orthography_raw=candidate.target_orthography or "",
                    ai_target_reading_raw=candidate.target_reading or "",
                    target_resolution_method=candidate.target_resolution_method or "unknown",
                    target_resolution_confidence=candidate.target_resolution_confidence or 0.0,
                )
                
                record = await result.single()
                if record:
                    action = record.get("action", "updated")
                    if action == "created":
                        stats["created"] += 1
                    else:
                        stats["updated"] += 1
            except Exception as e:
                logger.error(
                    "Failed to create relation",
                    source=candidate.source_word,
                    target=candidate.target_word,
                    error=str(e),
                )
                stats["errors"] += 1
        
        return stats
