"""
CanDoDescriptor Embedding Service
Generates and manages vector embeddings for CanDoDescriptor nodes in Neo4j.
"""

import asyncio
from typing import List, Dict, Optional, Any
from datetime import datetime
import structlog

from app.services.embedding_service import EmbeddingService
from app.core.config import settings

logger = structlog.get_logger()

# Optional import for title generation
try:
    from app.services.cando_title_service import CanDoTitleService
    TITLE_SERVICE_AVAILABLE = True
except ImportError:
    TITLE_SERVICE_AVAILABLE = False


class CanDoEmbeddingService:
    """Service for generating and managing CanDoDescriptor embeddings."""
    
    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.default_provider = "openai"
        self.embedding_dimensions = 1536
        # Default similarity threshold from settings
        self.default_similarity_threshold = settings.CANDO_SIMILARITY_THRESHOLD
        # Optional title service for generating titles if missing
        if TITLE_SERVICE_AVAILABLE:
            self.title_service = CanDoTitleService()
        else:
            self.title_service = None
    
    def generate_cando_embedding_content(
        self, 
        description_en: Optional[str] = None,
        description_ja: Optional[str] = None
    ) -> str:
        """
        Combine descriptionEn and descriptionJa into a single text for embedding.
        
        Args:
            description_en: English description
            description_ja: Japanese description
            
        Returns:
            Combined text string for embedding
        """
        parts = []
        
        if description_en:
            parts.append(f"English: {description_en}")
        
        if description_ja:
            parts.append(f"Japanese: {description_ja}")
        
        if not parts:
            raise ValueError("At least one description (en or ja) must be provided")
        
        return " | ".join(parts)
    
    async def generate_cando_embedding(
        self,
        description_en: Optional[str] = None,
        description_ja: Optional[str] = None,
        provider: str = "openai"
    ) -> List[float]:
        """
        Generate embedding for CanDoDescriptor descriptions.
        
        Args:
            description_en: English description
            description_ja: Japanese description
            provider: AI provider ("openai" or "gemini")
            
        Returns:
            Embedding vector as list of floats
        """
        content = self.generate_cando_embedding_content(description_en, description_ja)
        return await self.embedding_service.generate_content_embedding(content, provider)
    
    async def update_cando_embedding(
        self,
        neo4j_session,
        can_do_uid: str,
        description_en: Optional[str] = None,
        description_ja: Optional[str] = None,
        provider: str = "openai"
    ) -> bool:
        """
        Update embedding for a single CanDoDescriptor node.
        
        Args:
            neo4j_session: Neo4j async session
            can_do_uid: CanDoDescriptor UID
            provider: AI provider for embeddings
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Use provided descriptions or fetch from node
            if description_en is None or description_ja is None:
                result = await neo4j_session.run(
                    """
                    MATCH (c:CanDoDescriptor {uid: $uid})
                    RETURN c.descriptionEn AS descriptionEn,
                           c.descriptionJa AS descriptionJa
                    """,
                    {"uid": can_do_uid}
                )
                
                record = await result.single()
                if not record:
                    logger.warning("CanDoDescriptor not found", uid=can_do_uid)
                    return False
                
                if description_en is None:
                    description_en = record.get("descriptionEn")
                if description_ja is None:
                    description_ja = record.get("descriptionJa")
            
            # Check if titles are missing and generate them if needed
            if self.title_service:
                try:
                    title_result = await neo4j_session.run(
                        """
                        MATCH (c:CanDoDescriptor {uid: $uid})
                        RETURN c.titleEn AS titleEn, c.titleJa AS titleJa
                        """,
                        {"uid": can_do_uid}
                    )
                    title_record = await title_result.single()
                    if title_record and (not title_record.get("titleEn") or not title_record.get("titleJa")):
                        logger.info("Generating missing titles", uid=can_do_uid)
                        try:
                            titles = await self.title_service.generate_titles(
                                description_en=description_en,
                                description_ja=description_ja
                            )
                            # Update titles
                            await neo4j_session.run(
                                """
                                MATCH (c:CanDoDescriptor {uid: $uid})
                                SET c.titleEn = $titleEn, c.titleJa = $titleJa
                                """,
                                {"uid": can_do_uid, "titleEn": titles["titleEn"], "titleJa": titles["titleJa"]}
                            )
                        except Exception as e:
                            logger.warning("Failed to generate titles", uid=can_do_uid, error=str(e))
                except Exception as e:
                    # Best-effort: title generation is optional and should not block embeddings.
                    logger.warning("Failed to check/update titles", uid=can_do_uid, error=str(e))
            
            # Generate embedding
            embedding = await self.generate_cando_embedding(
                description_en=description_en,
                description_ja=description_ja,
                provider=provider
            )
            
            # Update node with embedding
            await neo4j_session.run(
                """
                MATCH (c:CanDoDescriptor {uid: $uid})
                SET c.descriptionEmbedding = $embedding
                RETURN c.uid AS uid
                """,
                {"uid": can_do_uid, "embedding": embedding}
            )
            
            logger.info("Updated CanDoDescriptor embedding", uid=can_do_uid)
            return True
            
        except Exception as e:
            logger.error("Failed to update CanDoDescriptor embedding",
                       uid=can_do_uid,
                       error=str(e))
            return False
    
    async def batch_generate_cando_embeddings(
        self,
        neo4j_session,
        batch_size: int = 50,
        provider: str = "openai",
        skip_existing: bool = True
    ) -> Dict[str, int]:
        """
        Generate embeddings for all CanDoDescriptors that don't have embeddings yet.
        
        Args:
            neo4j_session: Neo4j async session
            batch_size: Number of nodes to process at once
            provider: AI provider for embeddings
            skip_existing: Skip nodes that already have embeddings
            
        Returns:
            Statistics dict with processed, generated, skipped, errors counts
        """
        logger.info("Starting batch CanDoDescriptor embedding generation",
                   batch_size=batch_size,
                   provider=provider)
        
        stats = {
            'processed': 0,
            'generated': 0,
            'skipped': 0,
            'errors': 0
        }
        
        skip = 0
        
        while True:
            # Fetch batch of CanDoDescriptors
            query = """
            MATCH (c:CanDoDescriptor)
            WHERE (c.descriptionEn IS NOT NULL OR c.descriptionJa IS NOT NULL)
            """
            
            if skip_existing:
                query += " AND c.descriptionEmbedding IS NULL"
            
            query += """
            RETURN c.uid AS uid,
                   c.descriptionEn AS descriptionEn,
                   c.descriptionJa AS descriptionJa
            ORDER BY c.uid
            SKIP $skip
            LIMIT $limit
            """
            
            result = await neo4j_session.run(
                query,
                {"skip": skip, "limit": batch_size}
            )
            
            records = [record async for record in result]
            
            if not records:
                break
            
            # Process batch
            for record in records:
                try:
                    uid = record.get("uid")
                    description_en = record.get("descriptionEn")
                    description_ja = record.get("descriptionJa")
                    
                    stats['processed'] += 1
                    
                    # Generate embedding
                    embedding = await self.generate_cando_embedding(
                        description_en=description_en,
                        description_ja=description_ja,
                        provider=provider
                    )
                    
                    # Update node
                    await neo4j_session.run(
                        """
                        MATCH (c:CanDoDescriptor {uid: $uid})
                        SET c.descriptionEmbedding = $embedding
                        """,
                        {"uid": uid, "embedding": embedding}
                    )
                    
                    stats['generated'] += 1
                    
                    if stats['generated'] % 50 == 0:
                        logger.info("Generated CanDoDescriptor embeddings batch",
                                   generated=stats['generated'],
                                   processed=stats['processed'])
                    
                    # Small delay to avoid rate limits
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    logger.error("Error generating CanDoDescriptor embedding",
                               uid=record.get("uid"),
                               error=str(e))
                    stats['errors'] += 1
            
            skip += batch_size
        
        logger.info("Batch CanDoDescriptor embedding generation completed", **stats)
        return stats
    
    async def find_similar_candos(
        self,
        neo4j_session,
        can_do_uid: str,
        limit: int = 10,
        similarity_threshold: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Find similar CanDoDescriptors using vector similarity search.
        
        Args:
            neo4j_session: Neo4j async session
            can_do_uid: CanDoDescriptor UID to find similar ones for
            limit: Maximum number of results
            similarity_threshold: Minimum similarity score (defaults to service default)
            
        Returns:
            List of similar CanDoDescriptors with similarity scores
        """
        if similarity_threshold is None:
            similarity_threshold = self.default_similarity_threshold
        
        try:
            # Use Neo4j vector index for similarity search
            # Note: Requires Neo4j 5.11+ with vector index support
            # Query returns limit+1 to account for the source node being in results
            result = await neo4j_session.run(
                """
                MATCH (source:CanDoDescriptor {uid: $uid})
                WHERE source.descriptionEmbedding IS NOT NULL
                CALL db.index.vector.queryNodes(
                    'cando_descriptor_embeddings',
                    $limit + 1,
                    source.descriptionEmbedding
                )
                YIELD node AS target, score
                WHERE target.uid <> $uid
                  AND score >= $threshold
                RETURN target.uid AS uid,
                       target.level AS level,
                       target.primaryTopic AS topic,
                       target.skillDomain AS skillDomain,
                       target.descriptionEn AS descriptionEn,
                       target.descriptionJa AS descriptionJa,
                       score AS similarity
                ORDER BY score DESC
                LIMIT $limit
                """,
                {
                    "uid": can_do_uid,
                    "limit": limit,
                    "threshold": similarity_threshold
                }
            )
            
            similar = []
            async for record in result:
                similar.append({
                    'uid': record.get("uid"),
                    'level': record.get("level"),
                    'topic': record.get("topic"),
                    'skillDomain': record.get("skillDomain"),
                    'descriptionEn': record.get("descriptionEn"),
                    'descriptionJa': record.get("descriptionJa"),
                    'similarity': float(record.get("similarity", 0.0))
                })
            
            return similar
            
        except Exception as e:
            logger.error("Failed to find similar CanDoDescriptors",
                       uid=can_do_uid,
                       error=str(e))
            # Fallback to manual cosine similarity if vector index not available
            return await self._find_similar_candos_fallback(
                neo4j_session, can_do_uid, limit, similarity_threshold
            )
    
    async def _find_similar_candos_fallback(
        self,
        neo4j_session,
        can_do_uid: str,
        limit: int,
        similarity_threshold: float
    ) -> List[Dict[str, Any]]:
        """
        Fallback method using manual cosine similarity computation.
        """
        try:
            # Get source embedding
            result = await neo4j_session.run(
                """
                MATCH (c:CanDoDescriptor {uid: $uid})
                RETURN c.descriptionEmbedding AS embedding
                """,
                {"uid": can_do_uid}
            )
            
            record = await result.single()
            if not record:
                return []
            
            source_embedding = record.get("embedding")
            if not source_embedding:
                return []
            
            # Find all other CanDoDescriptors with embeddings
            result = await neo4j_session.run(
                """
                MATCH (c:CanDoDescriptor)
                WHERE c.uid <> $uid
                  AND c.descriptionEmbedding IS NOT NULL
                RETURN c.uid AS uid,
                       c.level AS level,
                       c.primaryTopic AS topic,
                       c.skillDomain AS skillDomain,
                       c.descriptionEn AS descriptionEn,
                       c.descriptionJa AS descriptionJa,
                       c.descriptionEmbedding AS embedding
                """,
                {"uid": can_do_uid}
            )
            
            # Compute cosine similarity manually
            similarities = []
            async for record in result:
                target_embedding = record.get("embedding")
                if not target_embedding:
                    continue
                
                # Cosine similarity
                similarity = self._cosine_similarity(source_embedding, target_embedding)
                
                if similarity >= similarity_threshold:
                    similarities.append({
                        'uid': record.get("uid"),
                        'level': record.get("level"),
                        'topic': record.get("topic"),
                        'skillDomain': record.get("skillDomain"),
                        'descriptionEn': record.get("descriptionEn"),
                        'descriptionJa': record.get("descriptionJa"),
                        'similarity': similarity
                    })
            
            # Sort by similarity and return top results
            similarities.sort(key=lambda x: x['similarity'], reverse=True)
            return similarities[:limit]
            
        except Exception as e:
            logger.error("Fallback similarity search failed",
                       uid=can_do_uid,
                       error=str(e))
            return []
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Compute cosine similarity between two vectors."""
        if len(vec1) != len(vec2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = sum(a * a for a in vec1) ** 0.5
        magnitude2 = sum(b * b for b in vec2) ** 0.5
        
        if magnitude1 == 0.0 or magnitude2 == 0.0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)
    
    async def create_similarity_relationships(
        self,
        neo4j_session,
        similarity_threshold: Optional[float] = None,
        batch_size: int = 100
    ) -> Dict[str, int]:
        """
        Compute similarity scores and create SEMANTICALLY_SIMILAR relationships.
        
        Args:
            neo4j_session: Neo4j async session
            similarity_threshold: Minimum similarity score (defaults to service default)
            batch_size: Number of relationships to create per batch
            
        Returns:
            Statistics dict with created, updated, errors counts
        """
        if similarity_threshold is None:
            similarity_threshold = self.default_similarity_threshold
        
        logger.info("Starting similarity relationship creation",
                   threshold=similarity_threshold,
                   batch_size=batch_size)
        
        stats = {
            'created': 0,
            'updated': 0,
            'errors': 0
        }
        
        try:
            # Get all CanDoDescriptors with embeddings
            result = await neo4j_session.run(
                """
                MATCH (c:CanDoDescriptor)
                WHERE c.descriptionEmbedding IS NOT NULL
                RETURN c.uid AS uid,
                       c.level AS level,
                       c.primaryTopic AS topic,
                       c.skillDomain AS skillDomain,
                       c.descriptionEmbedding AS embedding
                ORDER BY c.uid
                """
            )
            
            nodes = []
            async for record in result:
                nodes.append({
                    'uid': record.get("uid"),
                    'level': record.get("level"),
                    'topic': record.get("topic"),
                    'skillDomain': record.get("skillDomain"),
                    'embedding': record.get("embedding")
                })
            
            logger.info("Found CanDoDescriptors with embeddings", count=len(nodes))
            
            # Process in batches to create relationships
            batch = []
            
            for i, source in enumerate(nodes):
                # Use vector index if available, otherwise compute manually
                try:
                    similar = await self.find_similar_candos(
                        neo4j_session,
                        source['uid'],
                        limit=100,  # Get more candidates
                        similarity_threshold=similarity_threshold
                    )
                    
                    for target in similar:
                        # Create relationship with metadata
                        relationship_data = {
                            'source_uid': source['uid'],
                            'target_uid': target['uid'],
                            'similarity_score': target['similarity'],
                            'source_level': source.get('level'),
                            'target_level': target.get('level'),
                            'source_topic': source.get('topic'),
                            'target_topic': target.get('topic'),
                            'source_skillDomain': source.get('skillDomain'),
                            'target_skillDomain': target.get('skillDomain'),
                            'cross_domain': (
                                source.get('level') != target.get('level') or
                                source.get('topic') != target.get('topic') or
                                source.get('skillDomain') != target.get('skillDomain')
                            ),
                            'created_at': datetime.utcnow().isoformat()
                        }
                        
                        batch.append(relationship_data)
                        
                        if len(batch) >= batch_size:
                            await self._create_relationships_batch(neo4j_session, batch, stats)
                            batch.clear()
                
                except Exception as e:
                    logger.error("Error processing CanDoDescriptor",
                               uid=source['uid'],
                               error=str(e))
                    stats['errors'] += 1
                
                if (i + 1) % 50 == 0:
                    logger.info("Processed CanDoDescriptors",
                               processed=i + 1,
                               total=len(nodes),
                               created=stats['created'])
            
            # Process remaining batch
            if batch:
                await self._create_relationships_batch(neo4j_session, batch, stats)
            
            logger.info("Similarity relationship creation completed", **stats)
            return stats
            
        except Exception as e:
            logger.error("Failed to create similarity relationships", error=str(e))
            stats['errors'] += 1
            return stats
    
    async def _create_relationships_batch(
        self,
        neo4j_session,
        batch: List[Dict[str, Any]],
        stats: Dict[str, int]
    ) -> None:
        """Create a batch of SEMANTICALLY_SIMILAR relationships."""
        try:
            await neo4j_session.run(
                """
                UNWIND $relationships AS rel
                MATCH (source:CanDoDescriptor {uid: rel.source_uid})
                MATCH (target:CanDoDescriptor {uid: rel.target_uid})
                MERGE (source)-[r:SEMANTICALLY_SIMILAR]->(target)
                ON CREATE SET
                    r.similarity_score = rel.similarity_score,
                    r.source_level = rel.source_level,
                    r.target_level = rel.target_level,
                    r.source_topic = rel.source_topic,
                    r.target_topic = rel.target_topic,
                    r.source_skillDomain = rel.source_skillDomain,
                    r.target_skillDomain = rel.target_skillDomain,
                    r.cross_domain = rel.cross_domain,
                    r.created_at = rel.created_at
                ON MATCH SET
                    r.similarity_score = rel.similarity_score,
                    r.updated_at = rel.created_at
                RETURN count(r) AS count
                """,
                {"relationships": batch}
            )
            
            # Count created vs updated (simplified - assume all are created for now)
            stats['created'] += len(batch)
            
        except Exception as e:
            logger.error("Failed to create relationships batch", error=str(e))
            stats['errors'] += len(batch)
    
    async def update_similarity_for_cando(
        self,
        neo4j_session,
        can_do_uid: str,
        similarity_threshold: Optional[float] = None
    ) -> int:
        """
        Update similarity relationships for a single CanDoDescriptor.
        Called when a CanDoDescriptor is added or modified.
        
        Args:
            neo4j_session: Neo4j async session
            can_do_uid: CanDoDescriptor UID
            similarity_threshold: Minimum similarity score
            
        Returns:
            Number of relationships created/updated
        """
        if similarity_threshold is None:
            similarity_threshold = self.default_similarity_threshold
        
        try:
            # First, ensure embedding exists
            await self.update_cando_embedding(neo4j_session, can_do_uid)
            
            # Find similar CanDoDescriptors
            similar = await self.find_similar_candos(
                neo4j_session,
                can_do_uid,
                limit=100,
                similarity_threshold=similarity_threshold
            )
            
            # Get source node metadata
            result = await neo4j_session.run(
                """
                MATCH (c:CanDoDescriptor {uid: $uid})
                RETURN c.level AS level,
                       c.primaryTopic AS topic,
                       c.skillDomain AS skillDomain
                """,
                {"uid": can_do_uid}
            )
            
            record = await result.single()
            if not record:
                return 0
            
            source_level = record.get("level")
            source_topic = record.get("topic")
            source_skillDomain = record.get("skillDomain")
            
            # Create/update relationships
            relationships = []
            for target in similar:
                relationships.append({
                    'source_uid': can_do_uid,
                    'target_uid': target['uid'],
                    'similarity_score': target['similarity'],
                    'source_level': source_level,
                    'target_level': target.get('level'),
                    'source_topic': source_topic,
                    'target_topic': target.get('topic'),
                    'source_skillDomain': source_skillDomain,
                    'target_skillDomain': target.get('skillDomain'),
                    'cross_domain': (
                        source_level != target.get('level') or
                        source_topic != target.get('topic') or
                        source_skillDomain != target.get('skillDomain')
                    ),
                    'created_at': datetime.utcnow().isoformat()
                })
            
            if relationships:
                await self._create_relationships_batch(neo4j_session, relationships, {'created': 0, 'updated': 0, 'errors': 0})
            
            return len(relationships)
            
        except Exception as e:
            logger.error("Failed to update similarity for CanDoDescriptor",
                       uid=can_do_uid,
                       error=str(e))
            return 0

