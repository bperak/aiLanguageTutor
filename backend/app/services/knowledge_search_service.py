"""
Unified Knowledge Search Service
Combines Neo4j graph traversal with PostgreSQL vector search for optimal results.
"""

import asyncio
from typing import List, Dict, Optional, Any, Union
from enum import Enum
import structlog
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_neo4j_session, get_postgresql_session
from app.services.embedding_service import EmbeddingService

logger = structlog.get_logger()


class SearchMode(str, Enum):
    """Search modes for different use cases."""
    SEMANTIC = "semantic"           # Vector similarity search
    GRAPH = "graph"                # Neo4j graph traversal
    HYBRID = "hybrid"              # Combined approach
    SYNONYM = "synonym"            # Synonym relationship search
    DOMAIN = "domain"              # Semantic domain search
    DIFFICULTY = "difficulty"      # Difficulty-based search


class SearchFilters(BaseModel):
    """Search filters for refined results."""
    difficulty_levels: Optional[List[str]] = None
    etymologies: Optional[List[str]] = None
    pos_tags: Optional[List[str]] = None
    semantic_domains: Optional[List[str]] = None
    similarity_threshold: float = 0.7
    max_results: int = 20


class SearchResult(BaseModel):
    """Individual search result."""
    word_id: str
    kanji: str
    katakana: Optional[str] = None
    hiragana: Optional[str] = None
    translation: Optional[str] = None
    difficulty_level: Optional[str] = None
    etymology: Optional[str] = None
    pos_primary: Optional[str] = None
    semantic_domains: List[str] = []
    synonyms: List[Dict[str, Any]] = []
    similarity_score: Optional[float] = None
    relevance_score: float = 0.0
    match_reasons: List[str] = []


class SearchResults(BaseModel):
    """Search results container."""
    query: str
    search_mode: SearchMode
    results: List[SearchResult]
    total_found: int
    search_time_ms: int
    filters_applied: SearchFilters


class KnowledgeSearchService:
    """Advanced search service combining graph and vector approaches."""
    
    def __init__(self):
        self.embedding_service = EmbeddingService()
    
    async def search(
        self,
        query: str,
        mode: SearchMode = SearchMode.HYBRID,
        filters: SearchFilters = None,
        neo4j_session = None,
        postgresql_session: AsyncSession = None
    ) -> SearchResults:
        """
        Unified search interface.
        
        Args:
            query: Search query
            mode: Search mode to use
            filters: Search filters
            neo4j_session: Neo4j session (optional)
            postgresql_session: PostgreSQL session (optional)
            
        Returns:
            Unified search results
        """
        import time
        start_time = time.time()
        
        if filters is None:
            filters = SearchFilters()
        
        # Get sessions if not provided
        if neo4j_session is None:
            neo4j_session = await get_neo4j_session().__aenter__()
        if postgresql_session is None:
            postgresql_session = await get_postgresql_session().__aenter__()
        
        try:
            if mode == SearchMode.SEMANTIC:
                results = await self._semantic_search(query, filters, postgresql_session)
            elif mode == SearchMode.GRAPH:
                results = await self._graph_search(query, filters, neo4j_session)
            elif mode == SearchMode.HYBRID:
                results = await self._hybrid_search(query, filters, neo4j_session, postgresql_session)
            elif mode == SearchMode.SYNONYM:
                results = await self._synonym_search(query, filters, neo4j_session)
            elif mode == SearchMode.DOMAIN:
                results = await self._domain_search(query, filters, neo4j_session)
            elif mode == SearchMode.DIFFICULTY:
                results = await self._difficulty_search(query, filters, neo4j_session)
            else:
                results = []
            
            # Calculate relevance scores and sort
            results = self._calculate_relevance_scores(query, results)
            results = sorted(results, key=lambda x: x.relevance_score, reverse=True)
            
            # Apply result limit
            results = results[:filters.max_results]
            
            end_time = time.time()
            search_time_ms = int((end_time - start_time) * 1000)
            
            return SearchResults(
                query=query,
                search_mode=mode,
                results=results,
                total_found=len(results),
                search_time_ms=search_time_ms,
                filters_applied=filters
            )
            
        except Exception as e:
            logger.error("Search failed", query=query, mode=mode, error=str(e))
            raise
    
    async def _semantic_search(
        self,
        query: str,
        filters: SearchFilters,
        postgresql_session: AsyncSession
    ) -> List[SearchResult]:
        """Perform semantic vector search."""
        # Get semantic matches from embeddings
        embeddings_results = await self.embedding_service.semantic_search(
            query=query,
            postgresql_session=postgresql_session,
            limit=filters.max_results * 2,  # Get more for filtering
            similarity_threshold=filters.similarity_threshold,
            node_types=['word']
        )
        
        if not embeddings_results:
            return []
        
        # Get Neo4j data for the matched words
        word_ids = [result['neo4j_node_id'] for result in embeddings_results]
        
        neo4j_session = await get_neo4j_session().__aenter__()
        try:
            neo4j_results = await self._get_words_by_ids(word_ids, neo4j_session)
            
            # Merge results
            results = []
            for embedding_result in embeddings_results:
                word_id = embedding_result['neo4j_node_id']
                neo4j_data = neo4j_results.get(word_id, {})
                
                if neo4j_data:
                    result = self._create_search_result(neo4j_data)
                    result.similarity_score = embedding_result['similarity']
                    result.match_reasons.append(f"Semantic similarity: {result.similarity_score:.2f}")
                    results.append(result)
            
            return self._apply_filters(results, filters)
            
        finally:
            await neo4j_session.__aexit__(None, None, None)
    
    async def _graph_search(
        self,
        query: str,
        filters: SearchFilters,
        neo4j_session
    ) -> List[SearchResult]:
        """Perform Neo4j graph-based search."""
        # Build Cypher query based on search terms
        cypher_query = """
        MATCH (w:Word)
        WHERE w.kanji CONTAINS $query 
           OR w.katakana CONTAINS $query
           OR w.hiragana CONTAINS $query
           OR w.translation CONTAINS $query
        
        // Get related data
        OPTIONAL MATCH (w)-[:HAS_DIFFICULTY]->(d:DifficultyLevel)
        OPTIONAL MATCH (w)-[:HAS_ETYMOLOGY]->(e:Etymology)
        OPTIONAL MATCH (w)-[:HAS_POS]->(p:POSTag)
        OPTIONAL MATCH (w)-[:BELONGS_TO_DOMAIN]->(sd:SemanticDomain)
        OPTIONAL MATCH (w)-[r:SYNONYM_OF]->(syn:Word)
        
        WITH w, d, e, p,
             collect(DISTINCT sd.name) as semantic_domains,
             collect(DISTINCT {
                 kanji: syn.kanji,
                 translation: syn.translation,
                 strength: r.synonym_strength
             }) as synonyms
        
        RETURN {
            kanji: w.kanji,
            katakana: w.katakana,
            hiragana: w.hiragana,
            translation: w.translation,
            difficulty_level: d.level,
            etymology: e.type,
            pos_primary: p.primary_pos,
            semantic_domains: semantic_domains,
            synonyms: synonyms
        } as word_data
        
        LIMIT $limit
        """
        
        result = await neo4j_session.run(
            cypher_query,
            query=query,
            limit=filters.max_results
        )
        
        results = []
        async for record in result:
            word_data = record['word_data']
            search_result = self._create_search_result(word_data)
            search_result.match_reasons.append("Direct text match")
            results.append(search_result)
        
        return self._apply_filters(results, filters)
    
    async def _hybrid_search(
        self,
        query: str,
        filters: SearchFilters,
        neo4j_session,
        postgresql_session: AsyncSession
    ) -> List[SearchResult]:
        """Combine semantic and graph search for optimal results."""
        # Run both searches in parallel
        semantic_task = self._semantic_search(query, filters, postgresql_session)
        graph_task = self._graph_search(query, filters, neo4j_session)
        
        semantic_results, graph_results = await asyncio.gather(
            semantic_task, graph_task, return_exceptions=True
        )
        
        # Handle exceptions
        if isinstance(semantic_results, Exception):
            logger.warning("Semantic search failed", error=str(semantic_results))
            semantic_results = []
        if isinstance(graph_results, Exception):
            logger.warning("Graph search failed", error=str(graph_results))
            graph_results = []
        
        # Merge and deduplicate results
        all_results = {}
        
        # Add semantic results
        for result in semantic_results:
            all_results[result.word_id] = result
        
        # Add graph results, combining with existing
        for result in graph_results:
            if result.word_id in all_results:
                # Combine match reasons
                existing = all_results[result.word_id]
                existing.match_reasons.extend(result.match_reasons)
                existing.match_reasons = list(set(existing.match_reasons))  # Remove duplicates
            else:
                all_results[result.word_id] = result
        
        return list(all_results.values())
    
    async def _synonym_search(
        self,
        query: str,
        filters: SearchFilters,
        neo4j_session
    ) -> List[SearchResult]:
        """Search for words with strong synonym relationships."""
        cypher_query = """
        // Find the query word first
        MATCH (query_word:Word)
        WHERE query_word.kanji = $query 
           OR query_word.translation CONTAINS $query
        
        // Find its synonyms
        MATCH (query_word)-[r:SYNONYM_OF]->(syn:Word)
        WHERE r.synonym_strength >= $min_strength
        
        // Get synonym data
        OPTIONAL MATCH (syn)-[:HAS_DIFFICULTY]->(d:DifficultyLevel)
        OPTIONAL MATCH (syn)-[:HAS_ETYMOLOGY]->(e:Etymology)
        OPTIONAL MATCH (syn)-[:HAS_POS]->(p:POSTag)
        OPTIONAL MATCH (syn)-[:BELONGS_TO_DOMAIN]->(sd:SemanticDomain)
        
        WITH syn, d, e, p, r,
             collect(DISTINCT sd.name) as semantic_domains
        
        RETURN {
            kanji: syn.kanji,
            katakana: syn.katakana,
            hiragana: syn.hiragana,
            translation: syn.translation,
            difficulty_level: d.level,
            etymology: e.type,
            pos_primary: p.primary_pos,
            semantic_domains: semantic_domains,
            synonym_strength: r.synonym_strength,
            synonym_explanation: r.synonymy_explanation
        } as word_data
        
        ORDER BY r.synonym_strength DESC
        LIMIT $limit
        """
        
        result = await neo4j_session.run(
            cypher_query,
            query=query,
            min_strength=0.7,
            limit=filters.max_results
        )
        
        results = []
        async for record in result:
            word_data = record['word_data']
            search_result = self._create_search_result(word_data)
            strength = word_data.get('synonym_strength', 0)
            explanation = word_data.get('synonym_explanation', '')
            search_result.match_reasons.append(f"Synonym (strength: {strength:.2f})")
            if explanation:
                search_result.match_reasons.append(f"Relationship: {explanation}")
            results.append(search_result)
        
        return self._apply_filters(results, filters)
    
    async def _domain_search(
        self,
        query: str,
        filters: SearchFilters,
        neo4j_session
    ) -> List[SearchResult]:
        """Search within specific semantic domains."""
        cypher_query = """
        // Find semantic domain
        MATCH (domain:SemanticDomain)
        WHERE domain.name CONTAINS $query 
           OR domain.translation CONTAINS $query
        
        // Find words in this domain
        MATCH (domain)<-[:BELONGS_TO_DOMAIN]-(w:Word)
        
        // Get word data
        OPTIONAL MATCH (w)-[:HAS_DIFFICULTY]->(d:DifficultyLevel)
        OPTIONAL MATCH (w)-[:HAS_ETYMOLOGY]->(e:Etymology)
        OPTIONAL MATCH (w)-[:HAS_POS]->(p:POSTag)
        
        RETURN {
            kanji: w.kanji,
            katakana: w.katakana,
            hiragana: w.hiragana,
            translation: w.translation,
            difficulty_level: d.level,
            etymology: e.type,
            pos_primary: p.primary_pos,
            semantic_domains: [domain.name],
            domain_match: domain.translation
        } as word_data
        
        LIMIT $limit
        """
        
        result = await neo4j_session.run(
            cypher_query,
            query=query,
            limit=filters.max_results
        )
        
        results = []
        async for record in result:
            word_data = record['word_data']
            search_result = self._create_search_result(word_data)
            domain_match = word_data.get('domain_match', '')
            search_result.match_reasons.append(f"Semantic domain: {domain_match}")
            results.append(search_result)
        
        return self._apply_filters(results, filters)
    
    async def _difficulty_search(
        self,
        query: str,
        filters: SearchFilters,
        neo4j_session
    ) -> List[SearchResult]:
        """Search words by difficulty level."""
        # Parse difficulty from query (e.g., "beginner", "N5", "1", etc.)
        difficulty_mapping = {
            'beginner': '1.初級前半',
            'elementary': '2.初級後半', 
            'intermediate': '3.中級前半',
            'upper-intermediate': '4.中級後半',
            'advanced': '5.上級前半',
            'expert': '6.上級後半'
        }
        
        target_difficulty = difficulty_mapping.get(query.lower(), query)
        
        cypher_query = """
        MATCH (w:Word)-[:HAS_DIFFICULTY]->(d:DifficultyLevel)
        WHERE d.level CONTAINS $difficulty
           OR d.numeric_level = toInteger($difficulty)
        
        // Get word data
        OPTIONAL MATCH (w)-[:HAS_ETYMOLOGY]->(e:Etymology)
        OPTIONAL MATCH (w)-[:HAS_POS]->(p:POSTag)
        OPTIONAL MATCH (w)-[:BELONGS_TO_DOMAIN]->(sd:SemanticDomain)
        
        WITH w, d, e, p,
             collect(DISTINCT sd.name) as semantic_domains
        
        RETURN {
            kanji: w.kanji,
            katakana: w.katakana,
            hiragana: w.hiragana,
            translation: w.translation,
            difficulty_level: d.level,
            difficulty_numeric: d.numeric_level,
            etymology: e.type,
            pos_primary: p.primary_pos,
            semantic_domains: semantic_domains
        } as word_data
        
        ORDER BY d.numeric_level, w.kanji
        LIMIT $limit
        """
        
        result = await neo4j_session.run(
            cypher_query,
            difficulty=target_difficulty,
            limit=filters.max_results
        )
        
        results = []
        async for record in result:
            word_data = record['word_data']
            search_result = self._create_search_result(word_data)
            level = word_data.get('difficulty_level', '')
            search_result.match_reasons.append(f"Difficulty level: {level}")
            results.append(search_result)
        
        return self._apply_filters(results, filters)
    
    def _create_search_result(self, word_data: Dict[str, Any]) -> SearchResult:
        """Create SearchResult from word data."""
        return SearchResult(
            word_id=word_data.get('kanji', ''),
            kanji=word_data.get('kanji', ''),
            katakana=word_data.get('katakana'),
            hiragana=word_data.get('hiragana'),
            translation=word_data.get('translation'),
            difficulty_level=word_data.get('difficulty_level'),
            etymology=word_data.get('etymology'),
            pos_primary=word_data.get('pos_primary'),
            semantic_domains=word_data.get('semantic_domains', []),
            synonyms=word_data.get('synonyms', [])
        )
    
    def _apply_filters(self, results: List[SearchResult], filters: SearchFilters) -> List[SearchResult]:
        """Apply search filters to results."""
        filtered = results
        
        if filters.difficulty_levels:
            filtered = [r for r in filtered if r.difficulty_level in filters.difficulty_levels]
        
        if filters.etymologies:
            filtered = [r for r in filtered if r.etymology in filters.etymologies]
        
        if filters.pos_tags:
            filtered = [r for r in filtered if r.pos_primary in filters.pos_tags]
        
        if filters.semantic_domains:
            filtered = [r for r in filtered 
                       if any(domain in r.semantic_domains for domain in filters.semantic_domains)]
        
        return filtered
    
    def _calculate_relevance_scores(self, query: str, results: List[SearchResult]) -> List[SearchResult]:
        """Calculate relevance scores for results."""
        query_lower = query.lower()
        
        for result in results:
            score = 0.0
            
            # Exact matches get highest scores
            if result.kanji == query:
                score += 10.0
            elif result.translation and query_lower in result.translation.lower():
                score += 8.0
            
            # Semantic similarity
            if result.similarity_score:
                score += result.similarity_score * 5.0
            
            # Multiple match reasons boost score
            score += len(result.match_reasons) * 1.5
            
            # Difficulty bonus (prefer easier words for learning)
            if result.difficulty_level:
                if '初級' in result.difficulty_level:
                    score += 2.0
                elif '中級' in result.difficulty_level:
                    score += 1.0
            
            result.relevance_score = score
        
        return results
    
    async def _get_words_by_ids(self, word_ids: List[str], neo4j_session) -> Dict[str, Dict]:
        """Get word data from Neo4j by IDs."""
        if not word_ids:
            return {}
        
        cypher_query = """
        MATCH (w:Word)
        WHERE w.kanji IN $word_ids
        
        OPTIONAL MATCH (w)-[:HAS_DIFFICULTY]->(d:DifficultyLevel)
        OPTIONAL MATCH (w)-[:HAS_ETYMOLOGY]->(e:Etymology)
        OPTIONAL MATCH (w)-[:HAS_POS]->(p:POSTag)
        OPTIONAL MATCH (w)-[:BELONGS_TO_DOMAIN]->(sd:SemanticDomain)
        OPTIONAL MATCH (w)-[r:SYNONYM_OF]->(syn:Word)
        
        WITH w, d, e, p,
             collect(DISTINCT sd.name) as semantic_domains,
             collect(DISTINCT {
                 kanji: syn.kanji,
                 translation: syn.translation,
                 strength: r.synonym_strength
             }) as synonyms
        
        RETURN w.kanji as word_id, {
            kanji: w.kanji,
            katakana: w.katakana,
            hiragana: w.hiragana,
            translation: w.translation,
            difficulty_level: d.level,
            etymology: e.type,
            pos_primary: p.primary_pos,
            semantic_domains: semantic_domains,
            synonyms: synonyms
        } as word_data
        """
        
        result = await neo4j_session.run(cypher_query, word_ids=word_ids)
        
        words_data = {}
        async for record in result:
            word_id = record['word_id']
            word_data = record['word_data']
            words_data[word_id] = word_data
        
        return words_data


# Utility functions for easy access
async def search_words(
    query: str,
    mode: SearchMode = SearchMode.HYBRID,
    filters: SearchFilters = None
) -> SearchResults:
    """Convenience function for word search."""
    service = KnowledgeSearchService()
    return await service.search(query, mode, filters)


async def find_similar_words(word: str, limit: int = 10) -> SearchResults:
    """Find words similar to the given word."""
    service = KnowledgeSearchService()
    filters = SearchFilters(max_results=limit)
    return await service.search(word, SearchMode.SYNONYM, filters)


async def search_by_difficulty(difficulty: str, limit: int = 20) -> SearchResults:
    """Search words by difficulty level."""
    service = KnowledgeSearchService()
    filters = SearchFilters(max_results=limit)
    return await service.search(difficulty, SearchMode.DIFFICULTY, filters)


if __name__ == "__main__":
    async def demo_search():
        """Demo the search capabilities."""
        # Test different search modes
        queries = [
            ("物", SearchMode.HYBRID),
            ("thing", SearchMode.SEMANTIC), 
            ("beginner", SearchMode.DIFFICULTY),
            ("architecture", SearchMode.DOMAIN)
        ]
        
        for query, mode in queries:
            print(f"\n=== SEARCHING: '{query}' (mode: {mode.value}) ===")
            results = await search_words(query, mode)
            
            print(f"Found {results.total_found} results in {results.search_time_ms}ms")
            
            for result in results.results[:3]:  # Show top 3
                print(f"  {result.kanji} ({result.translation}) - {result.difficulty_level}")
                print(f"    Relevance: {result.relevance_score:.2f}")
                print(f"    Reasons: {', '.join(result.match_reasons)}")
    
    asyncio.run(demo_search())
