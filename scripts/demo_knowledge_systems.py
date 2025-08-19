"""
Demo script for the enhanced knowledge graph systems.
Tests vector search, AI content generation, and unified search.
"""

import asyncio
import json
from pathlib import Path
import sys

# Add the backend to the path
sys.path.append(str(Path(__file__).parent.parent / "backend"))

from app.services.knowledge_search_service import (
    KnowledgeSearchService, SearchMode, SearchFilters
)
from app.services.ai_content_generator import (
    AIContentGenerator, ContentType
)
from app.services.embedding_service import EmbeddingService
from app.db import get_neo4j_session, get_postgresql_session


async def demo_search_capabilities():
    """Demo the advanced search capabilities."""
    print("🔍 ENHANCED KNOWLEDGE GRAPH SEARCH DEMO")
    print("=" * 60)
    
    service = KnowledgeSearchService()
    
    # Test queries with different modes
    test_queries = [
        ("物", SearchMode.HYBRID, "Hybrid search for '物' (thing/object)"),
        ("architecture", SearchMode.DOMAIN, "Domain search for architecture"),
        ("beginner", SearchMode.DIFFICULTY, "Difficulty search for beginner words"),
        ("食べる", SearchMode.SYNONYM, "Synonym search for '食べる' (to eat)"),
        ("learning", SearchMode.SEMANTIC, "Semantic search for 'learning'")
    ]
    
    async with get_neo4j_session() as neo4j_session:
        async with get_postgresql_session() as postgresql_session:
            
            for query, mode, description in test_queries:
                print(f"\n--- {description} ---")
                
                try:
                    filters = SearchFilters(max_results=5)
                    results = await service.search(
                        query=query,
                        mode=mode,
                        filters=filters,
                        neo4j_session=neo4j_session,
                        postgresql_session=postgresql_session
                    )
                    
                    print(f"Found {results.total_found} results in {results.search_time_ms}ms")
                    
                    for i, result in enumerate(results.results[:3], 1):
                        print(f"  {i}. {result.kanji} ({result.translation})")
                        print(f"     Difficulty: {result.difficulty_level}")
                        print(f"     Relevance: {result.relevance_score:.2f}")
                        print(f"     Reasons: {', '.join(result.match_reasons)}")
                        
                        if result.synonyms:
                            synonyms = [f"{s.get('kanji', '')} ({s.get('translation', '')})" 
                                      for s in result.synonyms[:2]]
                            print(f"     Synonyms: {', '.join(synonyms)}")
                
                except Exception as e:
                    print(f"  ❌ Error: {e}")


async def demo_content_generation():
    """Demo AI content generation using knowledge graph context."""
    print("\n\n🤖 AI CONTENT GENERATION DEMO")
    print("=" * 60)
    
    generator = AIContentGenerator()
    
    # Test words with different characteristics
    test_words = [
        "物",      # Should have many relationships
        "食べる",   # Common verb
        "建築",     # Architecture domain
        "愛"       # Cultural concept
    ]
    
    async with get_neo4j_session() as neo4j_session:
        
        for word in test_words:
            print(f"\n--- Content for '{word}' ---")
            
            try:
                # Get word context first
                context = await generator.get_word_context(neo4j_session, word)
                
                if not context:
                    print(f"  ❌ No context found for '{word}'")
                    continue
                
                print(f"  📊 Context richness:")
                print(f"     Translation: {context.get('translation', 'N/A')}")
                print(f"     Difficulty: {context.get('difficulty', 'N/A')}")
                print(f"     Etymology: {context.get('etymology', 'N/A')}")
                print(f"     Synonyms: {len(context.get('synonyms', []))}")
                print(f"     Domains: {len(context.get('semantic_domains', []))}")
                
                # Generate different types of content
                content_types = [ContentType.USAGE_EXAMPLES, ContentType.GRAMMAR_EXPLANATION]
                
                content_items = await generator.generate_comprehensive_content(
                    neo4j_session=neo4j_session,
                    word_kanji=word,
                    content_types=content_types,
                    provider="openai"
                )
                
                for item in content_items:
                    print(f"\n  🎯 {item.content_type.value.upper()}:")
                    print(f"     Provider: {item.ai_provider} ({item.ai_model})")
                    print(f"     Confidence: {item.confidence_score}")
                    print(f"     Content preview: {item.content[:200]}...")
                
            except Exception as e:
                print(f"  ❌ Error generating content: {e}")


async def demo_embedding_search():
    """Demo semantic embedding search."""
    print("\n\n🧠 SEMANTIC EMBEDDING SEARCH DEMO")
    print("=" * 60)
    
    embedding_service = EmbeddingService()
    
    # Check if embeddings exist
    async with get_postgresql_session() as postgresql_session:
        from sqlalchemy import text
        
        result = await postgresql_session.execute(
            text("SELECT COUNT(*) FROM knowledge_embeddings WHERE node_type = 'word'")
        )
        embedding_count = result.scalar()
        
        print(f"📊 Available embeddings: {embedding_count:,}")
        
        if embedding_count == 0:
            print("⚠️  No embeddings found. Generating sample embeddings...")
            
            # Generate embeddings for a small sample
            async with get_neo4j_session() as neo4j_session:
                try:
                    stats = await embedding_service.batch_generate_embeddings(
                        neo4j_session=neo4j_session,
                        postgresql_session=postgresql_session,
                        batch_size=50,  # Small sample for demo
                        provider="openai"
                    )
                    print(f"✅ Generated {stats['generated']} embeddings")
                    
                except Exception as e:
                    print(f"❌ Failed to generate embeddings: {e}")
                    return
        
        # Test semantic search
        test_queries = [
            "Japanese traditional food",
            "learning and education", 
            "family relationships",
            "business and work"
        ]
        
        for query in test_queries:
            print(f"\n--- Semantic search: '{query}' ---")
            
            try:
                results = await embedding_service.semantic_search(
                    query=query,
                    postgresql_session=postgresql_session,
                    limit=3,
                    similarity_threshold=0.6
                )
                
                print(f"Found {len(results)} semantic matches:")
                
                for result in results:
                    print(f"  • {result['neo4j_node_id']}")
                    print(f"    Similarity: {result['similarity']:.3f}")
                    print(f"    Content: {result['content'][:150]}...")
                
            except Exception as e:
                print(f"  ❌ Error: {e}")


async def demo_comprehensive_workflow():
    """Demo a complete workflow combining all systems."""
    print("\n\n🚀 COMPREHENSIVE WORKFLOW DEMO")
    print("=" * 60)
    
    # Scenario: A user wants to learn about "食べ物" (food)
    query = "食べ物"
    print(f"📝 Learning scenario: User wants to learn about '{query}'")
    
    async with get_neo4j_session() as neo4j_session:
        async with get_postgresql_session() as postgresql_session:
            
            # Step 1: Search for the word and related concepts
            print(f"\n1️⃣ Searching for '{query}' and related concepts...")
            
            search_service = KnowledgeSearchService()
            search_results = await search_service.search(
                query=query,
                mode=SearchMode.HYBRID,
                filters=SearchFilters(max_results=3),
                neo4j_session=neo4j_session,
                postgresql_session=postgresql_session
            )
            
            print(f"   Found {search_results.total_found} related words:")
            target_words = []
            
            for result in search_results.results:
                print(f"   • {result.kanji} ({result.translation}) - {result.difficulty_level}")
                target_words.append(result.kanji)
            
            # Step 2: Generate learning content for the main word
            if target_words:
                main_word = target_words[0]
                print(f"\n2️⃣ Generating learning content for '{main_word}'...")
                
                generator = AIContentGenerator()
                content_items = await generator.generate_comprehensive_content(
                    neo4j_session=neo4j_session,
                    word_kanji=main_word,
                    content_types=[ContentType.USAGE_EXAMPLES, ContentType.CULTURAL_NOTES],
                    provider="openai"
                )
                
                for item in content_items:
                    print(f"   ✅ Generated {item.content_type.value}")
                    print(f"      Confidence: {item.confidence_score}")
                    print(f"      Preview: {item.content[:100]}...")
            
            # Step 3: Find similar words for expanded learning
            if target_words:
                print(f"\n3️⃣ Finding similar words for expanded learning...")
                
                similar_results = await search_service.search(
                    query=main_word,
                    mode=SearchMode.SYNONYM,
                    filters=SearchFilters(max_results=3),
                    neo4j_session=neo4j_session,
                    postgresql_session=postgresql_session
                )
                
                print(f"   Similar words for practice:")
                for result in similar_results.results:
                    print(f"   • {result.kanji} ({result.translation})")
                    if result.synonyms:
                        strength = result.synonyms[0].get('strength', 0)
                        print(f"     Relationship strength: {strength:.2f}")
            
            print(f"\n✅ Complete learning workflow demonstrated!")


async def main():
    """Run all demos."""
    print("🎓 AI LANGUAGE TUTOR - KNOWLEDGE SYSTEMS DEMO")
    print("=" * 80)
    
    # Run demos in sequence
    demos = [
        demo_search_capabilities,
        demo_content_generation,
        demo_embedding_search,
        demo_comprehensive_workflow
    ]
    
    for demo in demos:
        try:
            await demo()
        except Exception as e:
            print(f"❌ Demo failed: {e}")
        
        print("\n" + "─" * 80)
    
    print("\n🎉 Demo completed! Your knowledge graph systems are ready!")
    print("\n📚 Available API endpoints:")
    print("   • POST /api/v1/knowledge/search - Advanced search")
    print("   • GET  /api/v1/knowledge/quick/{query} - Quick search")
    print("   • POST /api/v1/knowledge/generate-content - AI content generation")
    print("   • GET  /api/v1/knowledge/word/{word}/similar - Find similar words")
    print("   • GET  /api/v1/knowledge/stats - Knowledge graph statistics")


if __name__ == "__main__":
    asyncio.run(main())
