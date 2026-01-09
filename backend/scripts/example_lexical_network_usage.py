#!/usr/bin/env python3
"""
Example usage of Lexical Network Builder.

Demonstrates how to use the services programmatically.
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.db import get_neo4j_session
from app.schemas.lexical_network import JobConfig
from app.services.lexical_network.job_manager_service import job_manager
from app.services.lexical_network.relation_builder_service import (
    RelationBuilderService,
)
from app.services.lexical_network.ai_provider_config import (
    get_recommended_model,
    list_available_models,
)


async def example_build_relations_for_word():
    """Example: Build relations for a single word."""
    print("=" * 60)
    print("Example 1: Build Relations for a Single Word")
    print("=" * 60)
    
    word = "美しい"  # beautiful (adjective)
    
    config = JobConfig(
        job_type="relation_building",
        source="word_list",
        word_list=[word],
        relation_types=["SYNONYM", "NEAR_SYNONYM"],
        model="gpt-4o-mini",  # Cost-effective default
        max_words=1,
        batch_size=10,
        min_confidence=0.7,
    )
    
    builder = RelationBuilderService()
    
    async for neo4j_session in get_neo4j_session():
        try:
            print(f"\nBuilding relations for: {word}")
            print(f"Model: {config.model}")
            print(f"Temperature: 0.0 (always)")
            print(f"Relation types: {config.relation_types}")
            
            result = await builder.build_relations_for_word(
                neo4j_session, word, config
            )
            
            print(f"\n✓ Results:")
            print(f"  - Candidates found: {result.candidates_found}")
            print(f"  - Relations created: {result.relations_created}")
            print(f"  - Relations updated: {result.relations_updated}")
            print(f"  - Errors: {result.errors}")
            print(f"  - Tokens (input/output): {result.tokens_input}/{result.tokens_output}")
            print(f"  - Cost: ${result.cost_usd:.6f}")
            print(f"  - Latency: {result.latency_ms}ms")
            print(f"  - Model used: {result.model_used}")
            
        except Exception as e:
            print(f"\n✗ Error: {e}")
            import traceback
            traceback.print_exc()
        break


async def example_create_job():
    """Example: Create and start a background job."""
    print("\n" + "=" * 60)
    print("Example 2: Create Background Job")
    print("=" * 60)
    
    # Get recommended model for batch processing
    recommended_model = get_recommended_model("batch")
    print(f"\nRecommended model for batch: {recommended_model}")
    
    config = JobConfig(
        job_type="relation_building",
        source="pos_filter",
        pos_filter="形容詞",  # Adjectives
        relation_types=["SYNONYM", "NEAR_SYNONYM", "GRADABLE_ANTONYM"],
        model=recommended_model,
        max_words=10,  # Small batch for example
        batch_size=5,
        min_confidence=0.7,
    )
    
    print(f"\nCreating job with config:")
    print(f"  - Source: {config.source}")
    print(f"  - POS filter: {config.pos_filter}")
    print(f"  - Model: {config.model}")
    print(f"  - Max words: {config.max_words}")
    print(f"  - Relation types: {config.relation_types}")
    
    job_id = await job_manager.create_job(config)
    print(f"\n✓ Job created: {job_id}")
    
    # Start the job
    started = await job_manager.start_job(job_id)
    if started:
        print(f"✓ Job started")
        
        # Check status
        status = await job_manager.get_job_status(job_id)
        print(f"\nJob status: {status.status}")
        print(f"Progress: {status.progress * 100:.1f}%")
    else:
        print("✗ Failed to start job")


async def example_list_models():
    """Example: List available AI models."""
    print("\n" + "=" * 60)
    print("Example 3: List Available AI Models")
    print("=" * 60)
    
    models = list_available_models()
    
    print(f"\nFound {len(models)} available models:\n")
    
    for model in models:
        print(f"  {model.model_id}")
        print(f"    Provider: {model.provider}")
        print(f"    Display: {model.display_name}")
        print(f"    Cost: ${model.input_cost_per_1k:.6f}/1K input, ${model.output_cost_per_1k:.6f}/1K output")
        print(f"    Max tokens: {model.max_tokens}")
        print(f"    JSON mode: {model.supports_json_mode}")
        print(f"    Recommended for: {', '.join(model.recommended_for)}")
        print()


async def example_query_relations():
    """Example: Query existing relations from Neo4j."""
    print("\n" + "=" * 60)
    print("Example 4: Query Existing Relations")
    print("=" * 60)
    
    async for neo4j_session in get_neo4j_session():
        try:
            # Query relations by provider
            query = """
            MATCH ()-[r:LEXICAL_RELATION]->()
            WHERE r.ai_provider IS NOT NULL
            RETURN r.ai_provider AS provider,
                   r.ai_model AS model,
                   count(*) AS count,
                   avg(r.ai_cost_usd) AS avg_cost,
                   avg(r.ai_latency_ms) AS avg_latency
            ORDER BY count DESC
            LIMIT 10
            """
            
            result = await neo4j_session.run(query)
            records = await result.data()
            
            if records:
                print(f"\nFound relations by provider:\n")
                for rec in records:
                    print(f"  {rec['provider']} / {rec['model']}")
                    print(f"    Count: {rec['count']}")
                    print(f"    Avg cost: ${rec['avg_cost']:.6f}")
                    print(f"    Avg latency: {rec['avg_latency']:.1f}ms")
                    print()
            else:
                print("\nNo relations found yet. Create some using Example 1 or 2!")
            
        except Exception as e:
            print(f"\n✗ Error: {e}")
        break


async def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("Lexical Network Builder - Usage Examples")
    print("=" * 60)
    print("\nThese examples demonstrate how to use the lexical network builder.")
    print("Make sure Neo4j is running and configured in .env\n")
    
    examples = [
        ("List Models", example_list_models),
        ("Query Relations", example_query_relations),
        # Uncomment to test actual AI calls (requires API keys):
        # ("Build Relations (Single Word)", example_build_relations_for_word),
        # ("Create Background Job", example_create_job),
    ]
    
    for name, example_func in examples:
        try:
            await example_func()
        except Exception as e:
            print(f"\n✗ Example '{name}' failed: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("Examples completed")
    print("=" * 60)
    print("\nTo test AI generation:")
    print("1. Ensure API keys are set in .env (OPENAI_API_KEY, GEMINI_API_KEY)")
    print("2. Uncomment the AI examples in this script")
    print("3. Run: python3 scripts/example_lexical_network_usage.py")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
