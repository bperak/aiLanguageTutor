"""
Grammar Service
==============

Service layer for managing Japanese grammar patterns from the Marugoto textbook series.
Provides high-level operations for grammar learning features.
"""

from typing import List, Optional, Dict, Any
from neo4j import AsyncSession
import logging

logger = logging.getLogger(__name__)

class GrammarService:
    """Service for managing grammar patterns and learning relationships"""
    
    def __init__(self, neo4j_session: AsyncSession):
        """Initialize with Neo4j session"""
        self.session = neo4j_session
    
    async def get_patterns(
        self,
        level: Optional[str] = None,
        classification: Optional[str] = None,
        jfs_category: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get grammar patterns with optional filtering.
        
        Args:
            level: Textbook level filter
            classification: Grammar classification filter
            jfs_category: JFS category filter
            search: Search term for patterns or examples
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of grammar pattern dictionaries
        """
        
        # Build dynamic query based on filters
        where_clauses = []
        params = {"limit": limit, "offset": offset}
        
        if level:
            where_clauses.append("g.textbook = $level")
            params["level"] = level
        
        if classification:
            where_clauses.append("g.classification = $classification")
            params["classification"] = classification
        
        if jfs_category:
            where_clauses.append("g.jfs_category = $jfs_category")
            params["jfs_category"] = jfs_category
        
        if search:
            where_clauses.append("(g.pattern CONTAINS $search OR g.example_sentence CONTAINS $search)")
            params["search"] = search
        
        where_clause = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
        
        query = f"""
        MATCH (g:GrammarPattern)
        {where_clause}
        RETURN g.id as id,
               g.sequence_number as sequence_number,
               g.pattern as pattern,
               g.pattern_romaji as pattern_romaji,
               g.textbook_form as textbook_form,
               g.textbook_form_romaji as textbook_form_romaji,
               g.example_sentence as example_sentence,
               g.example_romaji as example_romaji,
               g.classification as classification,
               g.textbook as textbook,
               g.topic as topic,
               g.lesson as lesson,
               g.jfs_category as jfs_category
        ORDER BY g.sequence_number
        SKIP $offset
        LIMIT $limit
        """
        
        try:
            result = await self.session.run(query, **params)
            patterns = []
            async for record in result:
                patterns.append(dict(record))
            
            logger.info(f"Retrieved {len(patterns)} grammar patterns")
            return patterns
            
        except Exception as e:
            logger.error(f"Error retrieving grammar patterns: {e}")
            raise
    
    async def get_pattern_by_id(self, pattern_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific grammar pattern by ID"""
        
        query = """
        MATCH (g:GrammarPattern {id: $pattern_id})
        RETURN g.id as id,
               g.sequence_number as sequence_number,
               g.pattern as pattern,
               g.pattern_romaji as pattern_romaji,
               g.textbook_form as textbook_form,
               g.textbook_form_romaji as textbook_form_romaji,
               g.example_sentence as example_sentence,
               g.example_romaji as example_romaji,
               g.classification as classification,
               g.textbook as textbook,
               g.topic as topic,
               g.lesson as lesson,
               g.jfs_category as jfs_category
        """
        
        try:
            result = await self.session.run(query, pattern_id=pattern_id)
            record = await result.single()
            
            if record:
                return dict(record)
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving pattern {pattern_id}: {e}")
            raise
    
    async def get_similar_patterns(self, pattern_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Find patterns similar to the specified pattern"""
        
        query = """
        MATCH (p:GrammarPattern {id: $pattern_id})-[s:SIMILAR_TO]->(similar:GrammarPattern)
        RETURN similar.pattern as pattern,
               similar.pattern_romaji as pattern_romaji,
               similar.example_sentence as example_sentence,
               similar.textbook as textbook,
               s.reason as similarity_reason
        ORDER BY similar.sequence_number
        LIMIT $limit
        """
        
        try:
            result = await self.session.run(query, pattern_id=pattern_id, limit=limit)
            similar_patterns = []
            async for record in result:
                similar_patterns.append(dict(record))
            
            logger.info(f"Found {len(similar_patterns)} similar patterns for {pattern_id}")
            return similar_patterns
            
        except Exception as e:
            logger.error(f"Error finding similar patterns for {pattern_id}: {e}")
            raise
    
    async def get_prerequisites(self, pattern_id: str) -> List[Dict[str, Any]]:
        """Get prerequisite patterns for the specified pattern"""
        
        query = """
        MATCH (prereq:GrammarPattern)-[:PREREQUISITE_FOR]->(target:GrammarPattern {id: $pattern_id})
        RETURN prereq.id as id,
               prereq.pattern as pattern,
               prereq.pattern_romaji as pattern_romaji,
               prereq.example_sentence as example_sentence,
               prereq.textbook as textbook,
               prereq.classification as classification
        ORDER BY prereq.sequence_number
        """
        
        try:
            result = await self.session.run(query, pattern_id=pattern_id)
            prerequisites = []
            async for record in result:
                prerequisites.append(dict(record))
            
            logger.info(f"Found {len(prerequisites)} prerequisites for {pattern_id}")
            return prerequisites
            
        except Exception as e:
            logger.error(f"Error finding prerequisites for {pattern_id}: {e}")
            raise
    
    async def get_learning_path(
        self, 
        from_pattern: str, 
        to_level: str, 
        max_depth: int = 3
    ) -> List[Dict[str, Any]]:
        """Generate learning path from a pattern to a target level"""
        
        try:
            # Simple approach: just get a few patterns from the target level
            # This will work regardless of relationship structure
            query = """
            MATCH (start:GrammarPattern {id: $from_pattern})
            MATCH (target:GrammarPattern {textbook: $to_level})
            RETURN start.id as start_id,
                   start.pattern as start_pattern,
                   collect({
                       id: target.id,
                       pattern: target.pattern,
                       sequence_number: target.sequence_number
                   })[0..5] as target_patterns
            """
            
            result = await self.session.run(
                query, 
                from_pattern=from_pattern, 
                to_level=to_level
            )
            
            record = await result.single()
            if not record:
                logger.warning(f"No data found for pattern {from_pattern} or level {to_level}")
                return []
            
            start_pattern = record["start_pattern"]
            target_patterns = record["target_patterns"]
            
            if not target_patterns:
                logger.info(f"No target patterns found for level {to_level}")
                return []
            
            # Create a simple learning path
            learning_paths = [{
                "from_pattern": start_pattern,
                "to_pattern": target_patterns[-1]["pattern"] if target_patterns else start_pattern,
                "path_length": len(target_patterns) + 1,
                "intermediate_patterns": [p["pattern"] for p in target_patterns[:-1]] if len(target_patterns) > 1 else [],
                "pattern_ids": [from_pattern] + [p["id"] for p in target_patterns]
            }]
            
            logger.info(f"Generated simple learning path with {len(target_patterns)} patterns")
            return learning_paths
            
        except Exception as e:
            logger.error(f"Error generating learning path: {e}")
            raise
    
    async def get_patterns_by_word(self, word: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get grammar patterns that use a specific word"""
        
        query = """
        MATCH (w:Word)<-[:USES_WORD]-(g:GrammarPattern)
        WHERE w.kanji = $word OR w.hiragana = $word
        RETURN g.id as id,
               g.pattern as pattern,
               g.pattern_romaji as pattern_romaji,
               g.example_sentence as example_sentence,
               g.example_romaji as example_romaji,
               g.textbook as textbook,
               g.classification as classification
        ORDER BY g.sequence_number
        LIMIT $limit
        """
        
        try:
            result = await self.session.run(query, word=word, limit=limit)
            patterns = []
            async for record in result:
                patterns.append(dict(record))
            
            logger.info(f"Found {len(patterns)} patterns using word '{word}'")
            return patterns
            
        except Exception as e:
            logger.error(f"Error finding patterns for word '{word}': {e}")
            raise
    
    async def get_personalized_recommendations(
        self,
        user_level: str,
        known_patterns: List[str],
        focus_classification: Optional[str] = None,
        limit: int = 5
    ) -> Dict[str, Any]:
        """Get personalized grammar pattern recommendations"""
        
        # Base query for recommendations
        where_clauses = ["g.textbook = $user_level"]
        params = {"user_level": user_level, "limit": limit}
        
        # Exclude known patterns
        if known_patterns:
            where_clauses.append("NOT g.id IN $known_patterns")
            params["known_patterns"] = known_patterns
        
        # Focus on specific classification
        if focus_classification:
            where_clauses.append("g.classification = $focus_classification")
            params["focus_classification"] = focus_classification
        
        where_clause = " AND ".join(where_clauses)
        
        query = f"""
        MATCH (g:GrammarPattern)
        WHERE {where_clause}
        // Prioritize patterns that are prerequisites for many others
        OPTIONAL MATCH (g)-[:PREREQUISITE_FOR]->(advanced:GrammarPattern)
        WITH g, count(advanced) as importance_score
        ORDER BY importance_score DESC, g.sequence_number
        LIMIT $limit
        RETURN g.id as id,
               g.pattern as pattern,
               g.pattern_romaji as pattern_romaji,
               g.example_sentence as example_sentence,
               g.example_romaji as example_romaji,
               g.classification as classification,
               g.textbook as textbook,
               importance_score
        """
        
        try:
            result = await self.session.run(query, **params)
            patterns = []
            total_importance = 0
            
            async for record in result:
                pattern_data = dict(record)
                importance = pattern_data.pop('importance_score', 0)
                total_importance += importance
                patterns.append(pattern_data)
            
            # Calculate difficulty match (simple heuristic)
            difficulty_match = min(1.0, len(patterns) / limit) if patterns else 0.0
            
            # Generate reasoning
            reasoning = f"Recommended {len(patterns)} patterns from {user_level} level"
            if focus_classification:
                reasoning += f" focusing on {focus_classification}"
            if known_patterns:
                reasoning += f", excluding {len(known_patterns)} known patterns"
            
            return {
                "recommended_patterns": patterns,
                "reasoning": reasoning,
                "difficulty_match": difficulty_match
            }
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            raise
    
    async def get_all_classifications(self) -> List[Dict[str, Any]]:
        """Get all available grammar classifications"""
        
        query = """
        MATCH (gc:GrammarClassification)
        OPTIONAL MATCH (gc)<-[:HAS_CLASSIFICATION]-(g:GrammarPattern)
        RETURN gc.name as name,
               gc.id as id,
               count(g) as pattern_count
        ORDER BY pattern_count DESC
        """
        
        try:
            result = await self.session.run(query)
            classifications = []
            async for record in result:
                classifications.append(dict(record))
            
            return classifications
            
        except Exception as e:
            logger.error(f"Error retrieving classifications: {e}")
            raise
    
    async def get_all_levels(self) -> List[Dict[str, Any]]:
        """Get all available textbook levels"""
        
        query = """
        MATCH (tl:TextbookLevel)
        OPTIONAL MATCH (tl)<-[:BELONGS_TO_LEVEL]-(g:GrammarPattern)
        RETURN tl.name as name,
               tl.id as id,
               tl.level_order as level_order,
               count(g) as pattern_count
        ORDER BY tl.level_order
        """
        
        try:
            result = await self.session.run(query)
            levels = []
            async for record in result:
                levels.append(dict(record))
            
            return levels
            
        except Exception as e:
            logger.error(f"Error retrieving textbook levels: {e}")
            raise
    
    async def get_all_jfs_categories(self) -> List[Dict[str, Any]]:
        """Get all available JFS categories"""
        
        query = """
        MATCH (jfs:JFSCategory)
        OPTIONAL MATCH (jfs)<-[:CATEGORIZED_AS]-(g:GrammarPattern)
        RETURN jfs.name as name,
               jfs.id as id,
               count(g) as pattern_count
        ORDER BY pattern_count DESC
        """
        
        try:
            result = await self.session.run(query)
            categories = []
            async for record in result:
                categories.append(dict(record))
            
            return categories
            
        except Exception as e:
            logger.error(f"Error retrieving JFS categories: {e}")
            raise
    
    async def get_graph_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics about the grammar graph"""
        
        try:
            # Node counts
            node_query = """
            MATCH (n)
            RETURN DISTINCT labels(n) as node_labels, count(n) as count
            ORDER BY count DESC
            """
            
            node_result = await self.session.run(node_query)
            node_stats = {}
            async for record in node_result:
                labels = ', '.join(record['node_labels'])
                node_stats[labels] = record['count']
            
            # Relationship counts
            rel_query = """
            MATCH ()-[r]->()
            RETURN type(r) as relationship_type, count(r) as count
            ORDER BY count DESC
            """
            
            rel_result = await self.session.run(rel_query)
            relationship_stats = {}
            total_relationships = 0
            
            async for record in rel_result:
                rel_type = record['relationship_type']
                count = record['count']
                relationship_stats[rel_type] = count
                total_relationships += count
            
            # Grammar-specific stats
            grammar_query = """
            MATCH (g:GrammarPattern)
            RETURN count(g) as total_patterns,
                   count(DISTINCT g.textbook) as textbook_levels,
                   count(DISTINCT g.classification) as classifications,
                   count(DISTINCT g.jfs_category) as jfs_categories
            """
            
            grammar_result = await self.session.run(grammar_query)
            grammar_stats = dict(await grammar_result.single())
            
            return {
                "nodes": node_stats,
                "relationships": relationship_stats,
                "total_relationships": total_relationships,
                "grammar_specific": grammar_stats,
                "graph_health": {
                    "total_nodes": sum(node_stats.values()),
                    "total_relationships": total_relationships,
                    "connectivity_ratio": total_relationships / sum(node_stats.values()) if sum(node_stats.values()) > 0 else 0
                }
            }
            
        except Exception as e:
            logger.error(f"Error retrieving graph statistics: {e}")
            raise
    
    async def search_patterns(self, search_term: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Full-text search across grammar patterns"""
        
        query = """
        MATCH (g:GrammarPattern)
        WHERE g.pattern CONTAINS $search_term 
           OR g.example_sentence CONTAINS $search_term
           OR g.textbook_form CONTAINS $search_term
           OR g.pattern_romaji CONTAINS $search_term
        RETURN g.id as id,
               g.pattern as pattern,
               g.pattern_romaji as pattern_romaji,
               g.example_sentence as example_sentence,
               g.textbook as textbook,
               g.classification as classification
        ORDER BY g.sequence_number
        LIMIT $limit
        """
        
        try:
            result = await self.session.run(query, search_term=search_term, limit=limit)
            patterns = []
            async for record in result:
                patterns.append(dict(record))
            
            logger.info(f"Found {len(patterns)} patterns matching '{search_term}'")
            return patterns
            
        except Exception as e:
            logger.error(f"Error searching patterns: {e}")
            raise
    
    async def get_learning_recommendations_for_user(
        self, 
        user_level: str, 
        user_strengths: List[str] = None,
        user_weaknesses: List[str] = None
    ) -> Dict[str, Any]:
        """
        Generate intelligent learning recommendations based on user profile.
        
        Args:
            user_level: Current textbook level
            user_strengths: Classifications user is strong in
            user_weaknesses: Classifications user needs work on
            
        Returns:
            Personalized recommendations with reasoning
        """
        
        recommendations = {
            "review_patterns": [],
            "new_patterns": [],
            "challenge_patterns": [],
            "vocabulary_focus": []
        }
        
        try:
            # Get patterns to review (user's current level, focus on weaknesses)
            if user_weaknesses:
                review_query = """
                MATCH (g:GrammarPattern {textbook: $user_level})
                WHERE g.classification IN $user_weaknesses
                RETURN g.id, g.pattern, g.pattern_romaji, g.classification
                ORDER BY g.sequence_number
                LIMIT 5
                """
                
                result = await self.session.run(query=review_query, user_level=user_level, user_weaknesses=user_weaknesses)
                async for record in result:
                    recommendations["review_patterns"].append(dict(record))
            
            # Get new patterns (next level, building on strengths)
            level_progression = {
                "入門(りかい)": "初級1(りかい)",
                "初級1(りかい)": "初級2(りかい)",
                "初級2(りかい)": "初中級",
                "初中級": "中級1",
                "中級1": "中級2"
            }
            
            next_level = level_progression.get(user_level)
            if next_level:
                new_query = """
                MATCH (g:GrammarPattern {textbook: $next_level})
                WHERE ($user_strengths IS NULL OR g.classification IN $user_strengths)
                RETURN g.id, g.pattern, g.pattern_romaji, g.classification
                ORDER BY g.sequence_number
                LIMIT 3
                """
                
                result = await self.session.run(
                    query=new_query, 
                    next_level=next_level, 
                    user_strengths=user_strengths
                )
                async for record in result:
                    recommendations["new_patterns"].append(dict(record))
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating user recommendations: {e}")
            raise
