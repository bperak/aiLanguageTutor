"""
Benchmark test for CanDo lesson generation across different AI models.

This test measures generation time and success rate for:
- Gemini 2.5 Pro
- OpenAI GPT-4o-mini
- OpenAI GPT-4o

Usage:
    cd backend
    poetry run pytest tests/test_lesson_generation_benchmark.py -v -s
"""

import asyncio
import json
import time
from typing import Dict, Any, Optional
import pytest
from uuid import uuid4

from app.services.cando_lesson_session_service import CanDoLessonSessionService
from app.core.config import get_settings

settings = get_settings()


class LessonGenerationBenchmark:
    """Benchmark lesson generation across different AI models."""
    
    def __init__(self):
        self.service = CanDoLessonSessionService()
        self.test_cases = [
            {
                "can_do_id": "TEST:001",
                "topic": "人との関係",  # Relationships
                "level": "A1",
                "description": "Basic greetings and introductions"
            },
            {
                "can_do_id": "TEST:002",
                "topic": "食生活",  # Food
                "level": "A2",
                "description": "Ordering food at a restaurant"
            },
            {
                "can_do_id": "TEST:003",
                "topic": "買い物",  # Shopping
                "level": "B1",
                "description": "Shopping for clothes"
            }
        ]
        
        self.models = [
            {"name": "Gemini 2.5 Pro", "provider": "gemini", "model": "gemini-2.5-pro"},
            {"name": "GPT-4o-mini", "provider": "openai", "model": "gpt-4o-mini"},
            {"name": "GPT-4o", "provider": "openai", "model": "gpt-4o"},
        ]
    
    async def generate_with_model(
        self,
        can_do_id: str,
        topic: str,
        level: str,
        provider: str,
        model: str
    ) -> Dict[str, Any]:
        """
        Generate a master lesson with a specific model.
        
        Returns:
            Dict with keys: success, duration_seconds, error, content_size, has_generic_content
        """
        start_time = time.perf_counter()
        
        try:
            # Generate master lesson
            master = await self.service._generate_master_lesson(
                can_do_id=can_do_id,
                topic=topic,
                original_level_str=level,
                provider=provider,
                meta_extra={}
            )
            
            duration = time.perf_counter() - start_time
            
            # Validate content
            has_generic = self._check_generic_content(master, topic)
            content_size = len(json.dumps(master))
            
            # Check structure
            has_ui = "ui" in master and "sections" in master.get("ui", {})
            section_count = len(master.get("ui", {}).get("sections", []))
            
            return {
                "success": True,
                "duration_seconds": round(duration, 2),
                "error": None,
                "content_size": content_size,
                "has_generic_content": has_generic,
                "has_valid_structure": has_ui and section_count >= 5,
                "section_count": section_count,
                "model": model
            }
            
        except asyncio.TimeoutError as e:
            duration = time.perf_counter() - start_time
            return {
                "success": False,
                "duration_seconds": round(duration, 2),
                "error": f"Timeout: {str(e)}",
                "content_size": 0,
                "has_generic_content": None,
                "has_valid_structure": False,
                "section_count": 0,
                "model": model
            }
        except Exception as e:
            duration = time.perf_counter() - start_time
            return {
                "success": False,
                "duration_seconds": round(duration, 2),
                "error": str(e),
                "content_size": 0,
                "has_generic_content": None,
                "has_valid_structure": False,
                "section_count": 0,
                "model": model
            }
    
    def _check_generic_content(self, master: Dict[str, Any], expected_topic: str) -> bool:
        """Check if master lesson contains generic station/travel content."""
        generic_indicators = ["駅での案内所", "道を聞く", "乗り換えの説明"]
        travel_keywords = ["旅行", "交通", "Travel", "Transportation"]
        
        # If topic is travel, generic content is OK
        if any(kw in expected_topic for kw in travel_keywords):
            return False
        
        # Check for generic content in non-travel topics
        sections = master.get("ui", {}).get("sections", [])
        for section in sections:
            for card in section.get("cards", []):
                if card.get("body"):
                    body_jp = str(card.get("body", {}).get("jp", ""))
                    if any(ind in body_jp for ind in generic_indicators):
                        return True
        return False
    
    def print_results(self, results: list[Dict[str, Any]]):
        """Print formatted benchmark results."""
        print("\n" + "="*80)
        print("LESSON GENERATION BENCHMARK RESULTS")
        print("="*80 + "\n")
        
        # Group by test case
        for test_case in self.test_cases:
            can_do_id = test_case["can_do_id"]
            topic = test_case["topic"]
            
            print(f"📚 Test Case: {can_do_id} - {topic}")
            print(f"   Description: {test_case['description']}")
            print("-" * 80)
            
            case_results = [r for r in results if r.get("can_do_id") == can_do_id]
            
            for result in sorted(case_results, key=lambda x: x.get("duration_seconds", 999)):
                model_name = result["model_name"]
                success = "✅" if result["success"] else "❌"
                duration = result["duration_seconds"]
                
                print(f"   {success} {model_name:20s} | {duration:6.2f}s", end="")
                
                if result["success"]:
                    size_kb = result["content_size"] / 1024
                    sections = result["section_count"]
                    generic = "⚠️ GENERIC" if result["has_generic_content"] else "✓ Topic-specific"
                    structure = "✓ Valid" if result["has_valid_structure"] else "✗ Invalid"
                    
                    print(f" | {size_kb:6.1f}KB | {sections:2d} sections | {structure} | {generic}")
                else:
                    error = result["error"][:50]
                    print(f" | Error: {error}")
            
            print()
        
        # Summary statistics
        print("="*80)
        print("SUMMARY STATISTICS")
        print("="*80 + "\n")
        
        for model_info in self.models:
            model_name = model_info["name"]
            model_results = [r for r in results if r["model_name"] == model_name]
            
            total = len(model_results)
            successful = sum(1 for r in model_results if r["success"])
            success_rate = (successful / total * 100) if total > 0 else 0
            
            avg_time = sum(r["duration_seconds"] for r in model_results if r["success"]) / successful if successful > 0 else 0
            
            generic_count = sum(1 for r in model_results if r.get("has_generic_content") == True)
            
            print(f"📊 {model_name}")
            print(f"   Success Rate:    {successful}/{total} ({success_rate:.1f}%)")
            print(f"   Avg Time:        {avg_time:.2f}s")
            print(f"   Generic Content: {generic_count}/{successful} lessons")
            print()


@pytest.mark.asyncio
async def test_benchmark_lesson_generation():
    """
    Benchmark lesson generation across different AI models.
    
    This test will:
    1. Generate lessons using multiple AI models
    2. Measure generation time for each
    3. Validate content quality
    4. Report comprehensive statistics
    """
    
    benchmark = LessonGenerationBenchmark()
    results = []
    
    print("\n🚀 Starting Lesson Generation Benchmark...")
    print(f"   Testing {len(benchmark.test_cases)} cases with {len(benchmark.models)} models")
    print(f"   Total generations: {len(benchmark.test_cases) * len(benchmark.models)}\n")
    
    # Run benchmarks
    for test_case in benchmark.test_cases:
        print(f"\n📝 Testing: {test_case['topic']} ({test_case['level']})")
        
        for model_info in benchmark.models:
            model_name = model_info["name"]
            provider = model_info["provider"]
            model = model_info["model"]
            
            print(f"   Generating with {model_name}...", end=" ", flush=True)
            
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
            
            status = "✅" if result["success"] else "❌"
            print(f"{status} {result['duration_seconds']:.2f}s")
    
    # Print results
    benchmark.print_results(results)
    
    # Save results to JSON
    from pathlib import Path
    output_file = Path(__file__).parent / "benchmark_results.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"📁 Full results saved to: {output_file}\n")
    
    # Assert at least one model succeeded
    successful_models = [r for r in results if r["success"]]
    assert len(successful_models) > 0, "At least one model should successfully generate a lesson"


@pytest.mark.asyncio
async def test_single_lesson_quick():
    """
    Quick test: Generate one lesson with the default model to check basic functionality.
    """
    benchmark = LessonGenerationBenchmark()
    
    print("\n🔬 Quick Single Lesson Test...")
    
    result = await benchmark.generate_with_model(
        can_do_id="TEST:QUICK",
        topic="買い物",  # Shopping
        level="A1",
        provider="gemini",
        model="gemini-2.5-pro"
    )
    
    print(f"\n   Model: Gemini 2.5 Pro")
    print(f"   Success: {'✅' if result['success'] else '❌'}")
    print(f"   Duration: {result['duration_seconds']:.2f}s")
    
    if result["success"]:
        print(f"   Content Size: {result['content_size'] / 1024:.1f}KB")
        print(f"   Sections: {result['section_count']}")
        print(f"   Generic Content: {'Yes ⚠️' if result['has_generic_content'] else 'No ✓'}")
        print(f"   Valid Structure: {'Yes ✓' if result['has_valid_structure'] else 'No ✗'}")
    else:
        print(f"   Error: {result['error']}")
    
    print()
    
    assert result["success"], f"Lesson generation failed: {result['error']}"


if __name__ == "__main__":
    # Run benchmark directly
    asyncio.run(test_benchmark_lesson_generation())

