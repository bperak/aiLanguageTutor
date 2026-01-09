"""
UNIDIC Enrichment Service

Uses fugashi/UniDic to add rich morphological data to Word nodes.
"""

from typing import Dict, List, Optional

import structlog

from app.services.lexical_network.pos_mapper import (
    should_update_canonical_pos,
    get_pos_priority,
)

logger = structlog.get_logger()


class UnidicEnrichmentService:
    """Service for enriching Word nodes with UNIDIC morphological data."""
    
    def __init__(self):
        self._tagger = None
        self._available = self._check_available()
    
    def _check_available(self) -> bool:
        """Check if fugashi/UniDic is available."""
        try:
            from fugashi import Tagger
            self._tagger = Tagger()
            return True
        except Exception as e:
            logger.warning("UniDic not available", error=str(e))
            return False
    
    @property
    def is_available(self) -> bool:
        """Check if UNIDIC is available."""
        return self._available
    
    def analyze_word(self, word: str) -> Optional[Dict]:
        """
        Get UNIDIC morphological analysis for a word.
        
        Args:
            word: Japanese word to analyze
            
        Returns:
            Dictionary with UNIDIC features, or None if unavailable
        """
        if not self._available or not self._tagger:
            return None
        
        try:
            # Parse the word
            tokens = list(self._tagger(word))
            
            if not tokens:
                return None
            
            # Get the first (main) token for single word analysis
            token = tokens[0]
            feature = token.feature
            
            # Extract UNIDIC features
            unidic_data = {}
            
            # Basic lemma and readings
            if hasattr(feature, 'lemma') and feature.lemma:
                unidic_data["unidic_lemma"] = feature.lemma
            if hasattr(feature, 'lForm') and feature.lForm:
                unidic_data["unidic_lemma_reading"] = feature.lForm
            if hasattr(feature, 'orthBase') and feature.orthBase:
                unidic_data["unidic_orth_base"] = feature.orthBase
            if hasattr(feature, 'pron') and feature.pron:
                unidic_data["unidic_pron"] = feature.pron
            
            # POS hierarchy (4 levels)
            if hasattr(feature, 'pos1') and feature.pos1:
                unidic_data["unidic_pos1"] = feature.pos1
            if hasattr(feature, 'pos2') and feature.pos2:
                unidic_data["unidic_pos2"] = feature.pos2
            if hasattr(feature, 'pos3') and feature.pos3:
                unidic_data["unidic_pos3"] = feature.pos3
            if hasattr(feature, 'pos4') and feature.pos4:
                unidic_data["unidic_pos4"] = feature.pos4
            
            # Conjugation info
            if hasattr(feature, 'cType') and feature.cType:
                unidic_data["unidic_ctype"] = feature.cType
            if hasattr(feature, 'cForm') and feature.cForm:
                unidic_data["unidic_cform"] = feature.cForm
            
            # Word origin (goshu)
            if hasattr(feature, 'goshu') and feature.goshu:
                unidic_data["unidic_goshu"] = feature.goshu
            
            # Accent
            if hasattr(feature, 'aType') and feature.aType:
                unidic_data["unidic_accent"] = feature.aType
            
            return unidic_data if unidic_data else None
            
        except Exception as e:
            logger.error("UNIDIC analysis failed", word=word, error=str(e))
            return None
    
    async def enrich_word_node(
        self,
        neo4j_session,
        word: str,
    ) -> Dict[str, any]:
        """
        Enrich a Neo4j Word node with UNIDIC data.
        
        Args:
            neo4j_session: Neo4j async session
            word: Word to enrich (standard_orthography)
            
        Returns:
            Enrichment statistics
        """
        unidic_data = self.analyze_word(word)
        if not unidic_data:
            return {"status": "skipped", "reason": "no_unidic_data", "word": word}
        
        # Normalize goshu to etymology if etymology is missing
        if unidic_data.get("unidic_goshu") and not unidic_data.get("etymology"):
            from app.services.lexical_network.column_mappings import normalize_etymology
            normalized, _ = normalize_etymology(unidic_data["unidic_goshu"], "unidic")
            if normalized:
                unidic_data["etymology"] = normalized
                unidic_data["etymology_source"] = "unidic"
        
        # Filter out None values
        props = {k: v for k, v in unidic_data.items() if v is not None}
        
        # Extract canonical POS from UniDic data
        canonical_pos = {
            "pos1": unidic_data.get("unidic_pos1"),
            "pos2": unidic_data.get("unidic_pos2"),
            "pos3": unidic_data.get("unidic_pos3"),
            "pos4": unidic_data.get("unidic_pos4"),
            "pos_primary_norm": unidic_data.get("unidic_pos1"),  # Primary is pos1
        }
        
        # First, update UniDic fields and get existing POS source
        query = """
        MATCH (w:Word)
        WHERE coalesce(w.standard_orthography, w.kanji) = $word
        SET w += $props,
            w.last_enriched_at = datetime(),
            w.sources = CASE 
                WHEN w.sources IS NULL THEN ['unidic']
                WHEN NOT 'unidic' IN w.sources 
                    THEN w.sources + ['unidic']
                ELSE w.sources
            END,
            // BACKWARD COMPATIBILITY: Also maintain old source field
            w.source = CASE 
                WHEN w.source IS NULL THEN 'unidic'
                WHEN w.source <> 'unidic' THEN w.source + '_unidic'
                ELSE w.source
            END,
            w.updated_at = datetime()
        RETURN w.standard_orthography AS word, w.pos_source AS existing_pos_source
        """
        
        result = await neo4j_session.run(query, word=word, props=props)
        record = await result.single()
        
        # Update canonical POS if UniDic has higher priority
        if record and canonical_pos.get("pos1"):
            existing_pos_source = record.get("existing_pos_source")
            if should_update_canonical_pos(existing_pos_source, "unidic"):
                update_query = """
                MATCH (w:Word)
                WHERE coalesce(w.standard_orthography, w.kanji) = $word
                SET w.pos1 = $pos1,
                    w.pos2 = $pos2,
                    w.pos3 = $pos3,
                    w.pos4 = $pos4,
                    w.pos_primary_norm = $pos_primary_norm,
                    w.pos_source = 'unidic',
                    w.pos_confidence = 1.0,
                    w.updated_at = datetime()
                """
                await neo4j_session.run(
                    update_query,
                    word=word,
                    pos1=canonical_pos.get("pos1"),
                    pos2=canonical_pos.get("pos2"),
                    pos3=canonical_pos.get("pos3"),
                    pos4=canonical_pos.get("pos4"),
                    pos_primary_norm=canonical_pos.get("pos_primary_norm"),
                )
        
        return {
            "status": "enriched" if record else "not_found",
            "word": word,
            "properties_added": list(props.keys()),
        }
    
    async def batch_enrich(
        self,
        neo4j_session,
        limit: int = 1000,
        pos_filter: Optional[str] = None,
    ) -> Dict[str, int]:
        """
        Batch enrich Word nodes missing UNIDIC data.
        
        Args:
            neo4j_session: Neo4j async session
            limit: Maximum words to process
            pos_filter: Optional POS filter
            
        Returns:
            Statistics
        """
        if not self._available:
            return {"enriched": 0, "skipped": 0, "errors": 0, "reason": "unidic_not_available"}
        
        stats = {"enriched": 0, "skipped": 0, "errors": 0}
        
        # Find words missing UNIDIC data
        query = """
        MATCH (w:Word)
        WHERE w.unidic_lemma IS NULL
        AND ($pos_filter IS NULL OR coalesce(w.pos_primary_norm, w.pos_primary) = $pos_filter)
        RETURN coalesce(w.standard_orthography, w.kanji) AS word
        LIMIT $limit
        """
        
        result = await neo4j_session.run(
            query, pos_filter=pos_filter, limit=limit
        )
        words = [record["word"] for record in await result.data()]
        
        logger.info("Starting UNIDIC batch enrichment", word_count=len(words))
        
        for word in words:
            try:
                result = await self.enrich_word_node(neo4j_session, word)
                if result["status"] == "enriched":
                    stats["enriched"] += 1
                else:
                    stats["skipped"] += 1
                    
                # Progress logging
                if (stats["enriched"] + stats["skipped"]) % 100 == 0:
                    logger.info(
                        "UNIDIC enrichment progress",
                        enriched=stats["enriched"],
                        skipped=stats["skipped"],
                    )
            except Exception as e:
                logger.error("Enrichment failed", word=word, error=str(e))
                stats["errors"] += 1
        
        logger.info("UNIDIC batch enrichment complete", **stats)
        return stats
