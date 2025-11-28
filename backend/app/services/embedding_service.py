"""
Enhanced Embedding Service
Generates and manages vector embeddings for the comprehensive knowledge graph.
"""

import asyncio
from typing import List, Dict, Optional, Tuple, Any
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import openai
from openai import AsyncOpenAI
from google import genai

from app.core.config import settings
from app.db import get_neo4j_session, get_postgresql_session

logger = structlog.get_logger()


class EmbeddingService:
    """Advanced embedding service for Japanese lexical knowledge graph."""
    
    def __init__(self):
        # Initialize AI clients
        self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        if settings.GEMINI_API_KEY:
            self.genai_client = genai.Client(api_key=settings.GEMINI_API_KEY)
        else:
            self.genai_client = None
        
        # Embedding dimensions (text-embedding-3-small)
        self.openai_dimensions = 1536
        self.default_provider = "openai"
    
    async def generate_content_embedding(
        self, 
        text: str, 
        provider: str = "openai"
    ) -> List[float]:
        """
        Generate embedding for text content.
        
        Args:
            text: Text to embed
            provider: AI provider ("openai" or "gemini")
            
        Returns:
            List of embedding values
        """
        try:
            if provider == "openai":
                response = await self.openai_client.embeddings.create(
                    model="text-embedding-3-small",
                    input=text
                )
                return response.data[0].embedding
            
            elif provider == "gemini":
                # Gemini embedding implementation
                if not self.genai_client:
                    raise ValueError("Gemini API key not configured")
                
                result = self.genai_client.models.embed_content(
                    model="models/embedding-001",
                    content=text
                )
                return result.embedding
            
            else:
                raise ValueError(f"Unsupported provider: {provider}")
                
        except Exception as e:
            logger.error("Failed to generate embedding", 
                        text=text[:100], 
                        provider=provider, 
                        error=str(e))
            raise
    
    async def create_word_embedding_content(
        self, 
        word_data: Dict[str, Any]
    ) -> str:
        """
        Create rich content string for word embedding.
        
        Args:
            word_data: Word data from Neo4j
            
        Returns:
            Rich content string for embedding
        """
        parts = []
        
        # Core word information
        if word_data.get('kanji'):
            parts.append(f"Word: {word_data['kanji']}")
        
        if word_data.get('katakana'):
            parts.append(f"Reading: {word_data['katakana']}")
        
        if word_data.get('hiragana'):
            parts.append(f"Hiragana: {word_data['hiragana']}")
        
        if word_data.get('translation'):
            parts.append(f"Meaning: {word_data['translation']}")
        
        # Etymology and classification
        if word_data.get('etymology'):
            etymology_map = {
                '和語': 'Native Japanese (Yamato-kotoba)',
                '漢語': 'Sino-Japanese (Kango)', 
                '外来語': 'Foreign loanword',
                '混種語': 'Hybrid word'
            }
            etymology_desc = etymology_map.get(word_data['etymology'], word_data['etymology'])
            parts.append(f"Etymology: {etymology_desc}")
        
        if word_data.get('pos_primary'):
            parts.append(f"Part of speech: {word_data['pos_primary']}")
        
        if word_data.get('difficulty_level'):
            parts.append(f"Difficulty: {word_data['difficulty_level']}")
        
        # Semantic information
        if word_data.get('semantic_domains'):
            domains = ', '.join(word_data['semantic_domains'])
            parts.append(f"Semantic domains: {domains}")
        
        if word_data.get('mutual_senses'):
            senses = ', '.join(word_data['mutual_senses'])
            parts.append(f"Related concepts: {senses}")
        
        # Synonyms
        if word_data.get('synonyms'):
            synonyms = ', '.join([f"{syn['word']} ({syn['translation']})" 
                                for syn in word_data['synonyms'][:5]])
            parts.append(f"Synonyms: {synonyms}")
        
        return '. '.join(parts)
    
    async def batch_generate_embeddings(
        self, 
        neo4j_session,
        postgresql_session: AsyncSession,
        batch_size: int = 100,
        provider: str = "openai"
    ) -> Dict[str, int]:
        """
        Generate embeddings for all words in the knowledge graph.
        
        Args:
            neo4j_session: Neo4j session
            postgresql_session: PostgreSQL session  
            batch_size: Number of words to process at once
            provider: AI provider for embeddings
            
        Returns:
            Statistics dict
        """
        logger.info("Starting batch embedding generation", 
                   batch_size=batch_size, 
                   provider=provider)
        
        stats = {
            'processed': 0,
            'generated': 0,
            'skipped': 0,
            'errors': 0
        }
        
        # Get all words with rich context
        query = """
        MATCH (w:Word)
        OPTIONAL MATCH (w)-[:HAS_DIFFICULTY]->(d:DifficultyLevel)
        OPTIONAL MATCH (w)-[:HAS_ETYMOLOGY]->(e:Etymology)  
        OPTIONAL MATCH (w)-[:HAS_POS]->(p:POSTag)
        OPTIONAL MATCH (w)-[:BELONGS_TO_DOMAIN]->(sd:SemanticDomain)
        OPTIONAL MATCH (w)-[:HAS_MUTUAL_SENSE]->(ms:MutualSense)
        OPTIONAL MATCH (w)-[r:SYNONYM_OF]->(syn:Word)
        WHERE w.kanji IS NOT NULL
        
        WITH w, d, e, p,
             collect(DISTINCT sd.name) as semantic_domains,
             collect(DISTINCT ms.sense) as mutual_senses,
             collect(DISTINCT {
                 word: syn.kanji, 
                 translation: syn.translation,
                 strength: r.synonym_strength
             }) as synonyms
        
        RETURN w.kanji as kanji,
               w.katakana as katakana, 
               w.hiragana as hiragana,
               w.translation as translation,
               e.type as etymology,
               p.primary_pos as pos_primary,
               d.level as difficulty_level,
               semantic_domains,
               mutual_senses,
               synonyms
        LIMIT $limit
        SKIP $skip
        """
        
        skip = 0
        
        while True:
            # Fetch batch from Neo4j
            result = await neo4j_session.run(query, limit=batch_size, skip=skip)
            records = [record async for record in result]
            
            if not records:
                break
            
            # Process batch
            for record in records:
                try:
                    word_data = dict(record)
                    stats['processed'] += 1
                    
                    # Check if embedding already exists
                    existing_check = await postgresql_session.execute(
                        text("""
                        SELECT id FROM knowledge_embeddings 
                        WHERE neo4j_node_id = :node_id AND node_type = 'word'
                        """),
                        {'node_id': word_data['kanji']}
                    )
                    
                    if existing_check.first():
                        stats['skipped'] += 1
                        continue
                    
                    # Create rich content for embedding
                    content = await self.create_word_embedding_content(word_data)
                    
                    # Generate embedding
                    embedding = await self.generate_content_embedding(content, provider)
                    
                    # Store in PostgreSQL
                    await postgresql_session.execute(
                        text("""
                        INSERT INTO knowledge_embeddings 
                        (neo4j_node_id, node_type, content, embedding, language_code)
                        VALUES (:node_id, :node_type, :content, :embedding, :language_code)
                        """),
                        {
                            'node_id': word_data['kanji'],
                            'node_type': 'word',
                            'content': content,
                            'embedding': embedding,
                            'language_code': 'ja'
                        }
                    )
                    
                    stats['generated'] += 1
                    
                    if stats['generated'] % 50 == 0:
                        await postgresql_session.commit()
                        logger.info("Generated embeddings batch", 
                                   generated=stats['generated'],
                                   processed=stats['processed'])
                
                except Exception as e:
                    logger.error("Error generating embedding", 
                               word=record.get('kanji'),
                               error=str(e))
                    stats['errors'] += 1
            
            skip += batch_size
            await postgresql_session.commit()
        
        logger.info("Batch embedding generation completed", **stats)
        return stats
    
    async def semantic_search(
        self,
        query: str,
        postgresql_session: AsyncSession,
        limit: int = 10,
        similarity_threshold: float = 0.7,
        node_types: List[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform semantic search across knowledge embeddings.
        
        Args:
            query: Search query
            postgresql_session: PostgreSQL session
            limit: Maximum results to return
            similarity_threshold: Minimum similarity score
            node_types: Filter by node types
            
        Returns:
            List of similar knowledge items
        """
        # Generate query embedding
        query_embedding = await self.generate_content_embedding(query)
        
        # Build SQL query
        where_clause = "WHERE 1=1"
        params = {
            'query_embedding': query_embedding,
            'similarity_threshold': similarity_threshold,
            'limit': limit
        }
        
        if node_types:
            where_clause += " AND node_type = ANY(:node_types)"
            params['node_types'] = node_types
        
        sql = f"""
        SELECT 
            neo4j_node_id,
            node_type,
            content,
            language_code,
            1 - (embedding <=> :query_embedding) as similarity,
            created_at
        FROM knowledge_embeddings
        {where_clause}
        AND 1 - (embedding <=> :query_embedding) >= :similarity_threshold
        ORDER BY embedding <=> :query_embedding
        LIMIT :limit
        """
        
        result = await postgresql_session.execute(text(sql), params)
        
        return [
            {
                'neo4j_node_id': row.neo4j_node_id,
                'node_type': row.node_type,
                'content': row.content,
                'similarity': float(row.similarity),
                'language_code': row.language_code
            }
            for row in result.fetchall()
        ]
    
    async def find_similar_words(
        self,
        word_id: str,
        postgresql_session: AsyncSession,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Find words similar to a given word using embeddings.
        
        Args:
            word_id: Neo4j node ID of the word
            postgresql_session: PostgreSQL session
            limit: Maximum results
            
        Returns:
            List of similar words
        """
        # Get the word's embedding
        result = await postgresql_session.execute(
            text("""
            SELECT embedding FROM knowledge_embeddings 
            WHERE neo4j_node_id = :word_id AND node_type = 'word'
            """),
            {'word_id': word_id}
        )
        
        word_embedding = result.scalar()
        if not word_embedding:
            return []
        
        # Find similar words
        result = await postgresql_session.execute(
            text("""
            SELECT 
                neo4j_node_id,
                content,
                1 - (embedding <=> :word_embedding) as similarity
            FROM knowledge_embeddings
            WHERE node_type = 'word' 
            AND neo4j_node_id != :word_id
            ORDER BY embedding <=> :word_embedding
            LIMIT :limit
            """),
            {
                'word_embedding': word_embedding,
                'word_id': word_id,
                'limit': limit
            }
        )
        
        return [
            {
                'neo4j_node_id': row.neo4j_node_id,
                'content': row.content,
                'similarity': float(row.similarity)
            }
            for row in result.fetchall()
        ]
    
    async def generate_and_store_message_embedding(
        self,
        message_id: str,
        content: str,
        postgresql_session: AsyncSession,
        provider: str = "openai"
    ) -> List[float]:
        """
        Generate embedding for a conversation message and store it in the database.
        
        Args:
            message_id: UUID of the conversation message
            content: Message content to embed
            postgresql_session: PostgreSQL session
            provider: AI provider for embeddings
            
        Returns:
            Embedding vector as list of floats
        """
        try:
            # Generate embedding
            embedding = await self.generate_content_embedding(content, provider)
            
            # Store in conversation_messages table
            # pgvector accepts list directly - asyncpg handles conversion
            await postgresql_session.execute(
                text("""
                UPDATE conversation_messages 
                SET content_embedding = :embedding::vector
                WHERE id = :message_id::uuid
                """),
                {
                    'message_id': message_id,
                    'embedding': embedding  # Pass list directly - asyncpg handles it
                }
            )
            
            await postgresql_session.commit()
            logger.info("Stored message embedding", message_id=message_id)
            return embedding
            
        except Exception as e:
            await postgresql_session.rollback()
            logger.error("Failed to store message embedding", 
                        message_id=message_id,
                        error=str(e))
            raise
    
    async def batch_generate_message_embeddings(
        self,
        postgresql_session: AsyncSession,
        batch_size: int = 50,
        provider: str = "openai"
    ) -> Dict[str, int]:
        """
        Generate embeddings for messages that don't have embeddings yet.
        
        Args:
            postgresql_session: PostgreSQL session
            batch_size: Number of messages to process at once
            provider: AI provider for embeddings
            
        Returns:
            Statistics dict
        """
        logger.info("Starting batch message embedding generation",
                   batch_size=batch_size,
                   provider=provider)
        
        stats = {
            'processed': 0,
            'generated': 0,
            'skipped': 0,
            'errors': 0
        }
        
        offset = 0
        
        while True:
            # Fetch batch of messages without embeddings
            result = await postgresql_session.execute(
                text("""
                SELECT id, content
                FROM conversation_messages
                WHERE content_embedding IS NULL
                AND content IS NOT NULL
                AND content != ''
                ORDER BY created_at
                LIMIT :limit
                OFFSET :offset
                """),
                {'limit': batch_size, 'offset': offset}
            )
            
            rows = result.fetchall()
            if not rows:
                break
            
            # Process batch
            for row in rows:
                try:
                    message_id = str(row.id)
                    content = row.content
                    
                    if not content or not content.strip():
                        stats['skipped'] += 1
                        continue
                    
                    stats['processed'] += 1
                    
                    # Generate and store embedding
                    await self.generate_and_store_message_embedding(
                        message_id=message_id,
                        content=content,
                        postgresql_session=postgresql_session,
                        provider=provider
                    )
                    
                    stats['generated'] += 1
                    
                    if stats['generated'] % 50 == 0:
                        logger.info("Generated message embeddings batch",
                                   generated=stats['generated'],
                                   processed=stats['processed'])
                
                except Exception as e:
                    logger.error("Error generating message embedding",
                               message_id=message_id,
                               error=str(e))
                    stats['errors'] += 1
            
            offset += batch_size
        
        logger.info("Batch message embedding generation completed", **stats)
        return stats


async def generate_all_embeddings():
    """Utility function to generate embeddings for all knowledge graph content."""
    embedding_service = EmbeddingService()
    
    async with get_neo4j_session() as neo4j_session:
        async with get_postgresql_session() as postgresql_session:
            stats = await embedding_service.batch_generate_embeddings(
                neo4j_session,
                postgresql_session,
                batch_size=100,
                provider="openai"
            )
            
            logger.info("Embedding generation completed", **stats)
            return stats


if __name__ == "__main__":
    asyncio.run(generate_all_embeddings())
