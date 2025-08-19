"""
Knowledge Graph API Endpoints
Expose the enhanced lexical knowledge graph and AI content generation.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.db import get_neo4j_session, get_postgresql_session
from app.services.knowledge_search_service import (
    KnowledgeSearchService, SearchMode, SearchFilters, SearchResults
)
from app.services.ai_content_generator import (
    AIContentGenerator, ContentType, GeneratedContent
)
from app.services.embedding_service import EmbeddingService

router = APIRouter()


# Request/Response Models
class SearchRequest(BaseModel):
    """Search request model."""
    query: str
    mode: SearchMode = SearchMode.HYBRID
    difficulty_levels: Optional[List[str]] = None
    etymologies: Optional[List[str]] = None
    pos_tags: Optional[List[str]] = None
    semantic_domains: Optional[List[str]] = None
    similarity_threshold: float = 0.7
    max_results: int = 20


class ContentGenerationRequest(BaseModel):
    """Content generation request model."""
    word_kanji: str
    content_types: List[ContentType]
    ai_provider: str = "openai"


class EmbeddingRequest(BaseModel):
    """Embedding generation request model."""
    batch_size: int = 100
    provider: str = "openai"


# Search Endpoints
@router.post("/search", response_model=SearchResults)
async def search_knowledge_graph(
    request: SearchRequest,
    neo4j_session=Depends(get_neo4j_session),
    postgresql_session: AsyncSession = Depends(get_postgresql_session)
):
    """
    Search the comprehensive knowledge graph.
    
    Supports multiple search modes:
    - semantic: Vector similarity search
    - graph: Neo4j graph traversal
    - hybrid: Combined approach (recommended)
    - synonym: Synonym relationship search
    - domain: Semantic domain search
    - difficulty: Difficulty-based search
    """
    try:
        service = KnowledgeSearchService()
        
        filters = SearchFilters(
            difficulty_levels=request.difficulty_levels,
            etymologies=request.etymologies,
            pos_tags=request.pos_tags,
            semantic_domains=request.semantic_domains,
            similarity_threshold=request.similarity_threshold,
            max_results=request.max_results
        )
        
        results = await service.search(
            query=request.query,
            mode=request.mode,
            filters=filters,
            neo4j_session=neo4j_session,
            postgresql_session=postgresql_session
        )
        
        return results
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/search/quick/{query}")
async def quick_search(
    query: str,
    mode: SearchMode = SearchMode.HYBRID,
    limit: int = 10,
    neo4j_session=Depends(get_neo4j_session),
    postgresql_session: AsyncSession = Depends(get_postgresql_session)
):
    """Quick search endpoint for simple queries."""
    service = KnowledgeSearchService()
    filters = SearchFilters(max_results=limit)
    
    results = await service.search(
        query=query,
        mode=mode,
        filters=filters,
        neo4j_session=neo4j_session,
        postgresql_session=postgresql_session
    )
    
    return results


@router.get("/word/{word_kanji}/similar")
async def find_similar_words(
    word_kanji: str,
    limit: int = 10,
    neo4j_session=Depends(get_neo4j_session),
    postgresql_session: AsyncSession = Depends(get_postgresql_session)
):
    """Find words similar to the given word using embeddings and graph relationships."""
    service = KnowledgeSearchService()
    filters = SearchFilters(max_results=limit)
    
    # Use synonym search mode for better results
    results = await service.search(
        query=word_kanji,
        mode=SearchMode.SYNONYM,
        filters=filters,
        neo4j_session=neo4j_session,
        postgresql_session=postgresql_session
    )
    
    return results


@router.get("/difficulty/{level}")
async def search_by_difficulty(
    level: str,
    limit: int = 20,
    neo4j_session=Depends(get_neo4j_session)
):
    """Search words by difficulty level (e.g., 'beginner', '1', '初級前半')."""
    service = KnowledgeSearchService()
    filters = SearchFilters(max_results=limit)
    
    results = await service.search(
        query=level,
        mode=SearchMode.DIFFICULTY,
        filters=filters,
        neo4j_session=neo4j_session
    )
    
    return results


@router.get("/domain/{domain}")
async def search_by_semantic_domain(
    domain: str,
    limit: int = 20,
    neo4j_session=Depends(get_neo4j_session)
):
    """Search words within a semantic domain."""
    service = KnowledgeSearchService()
    filters = SearchFilters(max_results=limit)
    
    results = await service.search(
        query=domain,
        mode=SearchMode.DOMAIN,
        filters=filters,
        neo4j_session=neo4j_session
    )
    
    return results


# Content Generation Endpoints
@router.post("/generate-content", response_model=List[GeneratedContent])
async def generate_learning_content(
    request: ContentGenerationRequest,
    neo4j_session=Depends(get_neo4j_session)
):
    """
    Generate comprehensive learning content for a word.
    
    Leverages the rich knowledge graph to create:
    - Grammar explanations
    - Usage examples with context
    - Cultural notes
    - Synonym explanations
    - Practice exercises
    - Mnemonics
    """
    try:
        generator = AIContentGenerator()
        
        content_items = await generator.generate_comprehensive_content(
            neo4j_session=neo4j_session,
            word_kanji=request.word_kanji,
            content_types=request.content_types,
            provider=request.ai_provider
        )
        
        return content_items
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Content generation failed: {str(e)}"
        )


@router.get("/word/{word_kanji}/content")
async def get_word_content(
    word_kanji: str,
    content_types: Optional[str] = None,  # Comma-separated list
    ai_provider: str = "openai",
    neo4j_session=Depends(get_neo4j_session)
):
    """Generate content for a specific word with optional content type filtering."""
    generator = AIContentGenerator()
    
    # Parse content types
    if content_types:
        requested_types = [
            ContentType(ct.strip()) 
            for ct in content_types.split(',')
            if ct.strip() in [ct.value for ct in ContentType]
        ]
    else:
        requested_types = [
            ContentType.GRAMMAR_EXPLANATION,
            ContentType.USAGE_EXAMPLES,
            ContentType.CULTURAL_NOTES,
            ContentType.SYNONYM_EXPLANATION
        ]
    
    content_items = await generator.generate_comprehensive_content(
        neo4j_session=neo4j_session,
        word_kanji=word_kanji,
        content_types=requested_types,
        provider=ai_provider
    )
    
    return content_items


@router.get("/word/{word_kanji}/context")
async def get_word_context(
    word_kanji: str,
    neo4j_session=Depends(get_neo4j_session)
):
    """Get rich context for a word from the knowledge graph."""
    generator = AIContentGenerator()
    
    context = await generator.get_word_context(neo4j_session, word_kanji)
    
    if not context:
        raise HTTPException(status_code=404, detail="Word not found in knowledge graph")
    
    return context


# Embedding Management Endpoints
@router.post("/embeddings/generate")
async def generate_embeddings(
    request: EmbeddingRequest,
    background_tasks: BackgroundTasks,
    neo4j_session=Depends(get_neo4j_session),
    postgresql_session: AsyncSession = Depends(get_postgresql_session)
):
    """
    Generate embeddings for all words in the knowledge graph.
    
    This is a background task that can take several minutes to complete.
    Use this to populate the vector search index.
    """
    embedding_service = EmbeddingService()
    
    # Run as background task
    background_tasks.add_task(
        embedding_service.batch_generate_embeddings,
        neo4j_session,
        postgresql_session,
        request.batch_size,
        request.provider
    )
    
    return {"message": "Embedding generation started as background task"}


@router.get("/embeddings/status")
async def get_embedding_status(
    postgresql_session: AsyncSession = Depends(get_postgresql_session)
):
    """Get the status of embedding generation."""
    from sqlalchemy import text
    
    # Count total embeddings
    result = await postgresql_session.execute(
        text("SELECT COUNT(*) as total FROM knowledge_embeddings WHERE node_type = 'word'")
    )
    total_embeddings = result.scalar()
    
    # Count total words
    result = await postgresql_session.execute(
        text("SELECT COUNT(*) as total FROM knowledge_embeddings")
    )
    total_nodes = result.scalar()
    
    return {
        "word_embeddings": total_embeddings,
        "total_embeddings": total_nodes,
        "status": "ready" if total_embeddings > 0 else "not_generated"
    }


# Statistics Endpoints
@router.get("/stats")
async def get_knowledge_graph_stats(
    neo4j_session=Depends(get_neo4j_session)
):
    """Get comprehensive statistics about the knowledge graph."""
    # Node counts
    node_query = """
    MATCH (n) 
    RETURN labels(n)[0] as NodeType, count(n) as Count 
    ORDER BY Count DESC
    """
    
    node_result = await neo4j_session.run(node_query)
    node_stats = {record['NodeType']: record['Count'] async for record in node_result}
    
    # Relationship counts  
    rel_query = """
    MATCH ()-[r]->() 
    RETURN type(r) as RelType, count(r) as Count 
    ORDER BY Count DESC
    """
    
    rel_result = await neo4j_session.run(rel_query)
    rel_stats = {record['RelType']: record['Count'] async for record in rel_result}
    
    # Difficulty distribution
    diff_query = """
    MATCH (w:Word)-[:HAS_DIFFICULTY]->(d:DifficultyLevel)
    WITH d, count(w) as WordCount
    RETURN d.level as Level, WordCount
    ORDER BY d.numeric_level
    """
    
    diff_result = await neo4j_session.run(diff_query)
    difficulty_stats = {record['Level']: record['WordCount'] async for record in diff_result}
    
    # Etymology distribution
    etym_query = """
    MATCH (w:Word)-[:HAS_ETYMOLOGY]->(e:Etymology)
    WITH e, count(w) as WordCount
    RETURN e.type as Etymology, WordCount
    ORDER BY WordCount DESC
    """
    
    etym_result = await neo4j_session.run(etym_query)
    etymology_stats = {record['Etymology']: record['WordCount'] async for record in etym_result}
    
    return {
        "node_counts": node_stats,
        "relationship_counts": rel_stats,
        "difficulty_distribution": difficulty_stats,
        "etymology_distribution": etymology_stats,
        "total_nodes": sum(node_stats.values()),
        "total_relationships": sum(rel_stats.values())
    }


@router.get("/health")
async def knowledge_service_health(
    neo4j_session=Depends(get_neo4j_session),
    postgresql_session: AsyncSession = Depends(get_postgresql_session)
):
    """Health check for knowledge services."""
    try:
        # Test Neo4j
        neo4j_result = await neo4j_session.run("MATCH (n) RETURN count(n) as total LIMIT 1")
        neo4j_count = await neo4j_result.single()
        neo4j_healthy = neo4j_count is not None
        
        # Test PostgreSQL
        from sqlalchemy import text
        pg_result = await postgresql_session.execute(text("SELECT 1"))
        pg_healthy = pg_result is not None
        
        return {
            "status": "healthy" if (neo4j_healthy and pg_healthy) else "unhealthy",
            "neo4j": "connected" if neo4j_healthy else "disconnected",
            "postgresql": "connected" if pg_healthy else "disconnected",
            "services": {
                "search": "available",
                "content_generation": "available",
                "embeddings": "available"
            }
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }
