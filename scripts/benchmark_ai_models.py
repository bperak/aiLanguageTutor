"""
Standalone script to benchmark AI model performance for lesson generation.

Usage:
    cd backend
    poetry run python ../scripts/benchmark_ai_models.py
    
Or from root:
    cd backend ; poetry run python ../scripts/benchmark_ai_models.py
"""

import asyncio
import os
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

# Now we can import
from tests.test_lesson_generation_benchmark import LessonGenerationBenchmark


async def main():
    """Run the benchmark."""
    benchmark = LessonGenerationBenchmark()
    
    print("\n" + "="*80)
    print("AI MODEL BENCHMARK FOR LESSON GENERATION")
    print("="*80)
    print(f"\n📋 Test Configuration:")
    print(f"   Models to test: {len(benchmark.models)}")
    for model in benchmark.models:
        print(f"      - {model['name']} ({model['provider']}:{model['model']})")
    print(f"   Test cases: {len(benchmark.test_cases)}")
    for case in benchmark.test_cases:
        print(f"      - {case['topic']} ({case['level']}): {case['description']}")
    print(f"   Total generations: {len(benchmark.test_cases) * len(benchmark.models)}")
    print()
    
    input("Press Enter to start the benchmark...")
    
    results = []
    
    # Run benchmarks
    for i, test_case in enumerate(benchmark.test_cases, 1):
        print(f"\n{'='*80}")
        print(f"TEST CASE {i}/{len(benchmark.test_cases)}: {test_case['topic']} ({test_case['level']})")
        print(f"Description: {test_case['description']}")
        print('='*80)
        
        for j, model_info in enumerate(benchmark.models, 1):
            model_name = model_info["name"]
            provider = model_info["provider"]
            model = model_info["model"]
            
            print(f"\n[{j}/{len(benchmark.models)}] Testing {model_name}...")
            print(f"     Provider: {provider}")
            print(f"     Model: {model}")
            print(f"     Generating...", end=" ", flush=True)
            
            result = await benchmark.generate_with_model(
                can_do_id=test_case["can_do_id"],
                topic=test_case["topic"],
                level=test_case["level"],
                provider=provider,
                model=model
            )
            
            # Add metadata
            result["can_do_id"] = test_case["can_do_id"]
            result["topic"] = test_case["topic"]
            result["model_name"] = model_name
            result["provider"] = provider
            
            results.append(result)
            
            # Print immediate result
            if result["success"]:
                print(f"✅ SUCCESS")
                print(f"     Duration: {result['duration_seconds']:.2f}s")
                print(f"     Content Size: {result['content_size'] / 1024:.1f}KB")
                print(f"     Sections: {result['section_count']}")
                print(f"     Generic Content: {'⚠️ YES' if result['has_generic_content'] else '✓ NO'}")
                print(f"     Valid Structure: {'✓ YES' if result['has_valid_structure'] else '✗ NO'}")
            else:
                print(f"❌ FAILED")
                print(f"     Duration: {result['duration_seconds']:.2f}s")
                print(f"     Error: {result['error']}")
    
    # Print final results
    print("\n\n")
    benchmark.print_results(results)
    
    # Save results
    import json
    output_file = Path(__file__).parent.parent / "tests" / "benchmark_results.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"📁 Detailed results saved to: {output_file}")
    
    # Recommendations
    print("\n" + "="*80)
    print("RECOMMENDATIONS")
    print("="*80 + "\n")
    
    successful_results = [r for r in results if r["success"]]
    if successful_results:
        # Find fastest model
        fastest = min(successful_results, key=lambda x: x["duration_seconds"])
        print(f"⚡ Fastest Model: {fastest['model_name']} ({fastest['duration_seconds']:.2f}s avg)")
        
        # Find most reliable
        model_success_rates = {}
        for model_info in benchmark.models:
            model_name = model_info["name"]
            model_results = [r for r in results if r["model_name"] == model_name]
            successful = sum(1 for r in model_results if r["success"])
            model_success_rates[model_name] = (successful, len(model_results))
        
        most_reliable = max(model_success_rates.items(), key=lambda x: x[1][0])
        print(f"🎯 Most Reliable: {most_reliable[0]} ({most_reliable[1][0]}/{most_reliable[1][1]} successful)")
        
        # Find best quality (no generic content)
        quality_results = [r for r in successful_results if not r.get("has_generic_content")]
        if quality_results:
            best_quality = min(quality_results, key=lambda x: x["duration_seconds"])
            print(f"✨ Best Quality: {best_quality['model_name']} (no generic content, {best_quality['duration_seconds']:.2f}s)")
        
        print(f"\n💡 Suggested configuration: Use {fastest['model_name']} for production")
    else:
        print("⚠️ No models succeeded. Please check configuration and API keys.")
    
    print()


if __name__ == "__main__":
    asyncio.run(main())

