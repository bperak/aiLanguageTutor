#!/usr/bin/env python3
"""
Bulk lesson pre-compilation script.

Usage:
    poetry run python scripts/preload_lessons.py --level A1 --limit 5
    poetry run python scripts/preload_lessons.py --level A1 --limit 100
"""
import asyncio
import argparse
import json
import sys
import time
from pathlib import Path
from datetime import datetime

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db import init_db_connections, neo4j_driver, AsyncSessionLocal
from app.services.cando_v2_compile_service import compile_lessonroot
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def fetch_cando_list(level: str, limit: int):
    """Fetch CanDo descriptors from Neo4j"""
    if not neo4j_driver:
        raise RuntimeError("Neo4j driver not initialized")
    
    async with neo4j_driver.session() as session:
        query = """
        MATCH (c:CanDoDescriptor)
        WHERE toString(c.level) = $level
        RETURN c.uid AS uid, 
               toString(c.level) AS level,
               coalesce(toString(c.primaryTopicEn), toString(c.primaryTopic)) AS topic
        ORDER BY c.uid
        LIMIT $limit
        """
        result = await session.run(query, level=level, limit=limit)
        records = []
        async for record in result:
            records.append(dict(record))
        return records


async def compile_single_lesson(neo, pg, can_do_id: str, metalanguage: str = "en", model: str = "gpt-4o"):
    """Compile a single lesson and return result stats"""
    start_time = time.time()
    try:
        result = await compile_lessonroot(
            neo=neo,
            pg=pg,
            can_do_id=can_do_id,
            metalanguage=metalanguage,
            model=model
        )
        duration = time.time() - start_time
        return {
            "can_do_id": can_do_id,
            "status": "success",
            "lesson_id": result.get("lesson_id"),
            "version": result.get("version"),
            "duration_sec": round(duration, 2)
        }
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"Failed to compile {can_do_id}", error=str(e))
        return {
            "can_do_id": can_do_id,
            "status": "failed",
            "error": str(e),
            "duration_sec": round(duration, 2)
        }


async def main():
    parser = argparse.ArgumentParser(description="Pre-compile lessons in bulk")
    parser.add_argument("--level", required=True, help="CEFR level (e.g., A1, A2)")
    parser.add_argument("--limit", type=int, default=5, help="Number of lessons to compile")
    parser.add_argument("--metalanguage", default="en", help="Metalanguage for explanations")
    parser.add_argument("--model", default="gpt-4o", help="LLM model to use")
    parser.add_argument("--output", default="preload_report.json", help="Output report filename")
    
    args = parser.parse_args()
    
    print(f"Starting bulk lesson compilation")
    print(f"Level: {args.level}")
    print(f"Limit: {args.limit}")
    print(f"Model: {args.model}")
    print("-" * 60)
    
    # Initialize databases
    await init_db_connections()
    print("✓ Database connections initialized")
    
    # Fetch CanDo list
    candos = await fetch_cando_list(args.level, args.limit)
    print(f"✓ Found {len(candos)} CanDo descriptors for level {args.level}")
    print()
    
    # Compile each lesson
    results = []
    total_start = time.time()
    
    async with neo4j_driver.session() as neo:
        async with AsyncSessionLocal() as pg:
            for idx, cando in enumerate(candos, 1):
                print(f"[{idx}/{len(candos)}] Compiling {cando['uid']} ({cando['topic']})...")
                result = await compile_single_lesson(
                    neo=neo,
                    pg=pg,
                    can_do_id=cando['uid'],
                    metalanguage=args.metalanguage,
                    model=args.model
                )
                results.append(result)
                
                status_symbol = "✓" if result['status'] == "success" else "✗"
                print(f"  {status_symbol} {result['status']} ({result['duration_sec']}s)")
                if result['status'] == "failed":
                    print(f"     Error: {result.get('error', 'Unknown')}")
                print()
    
    total_duration = time.time() - total_start
    
    # Generate report
    success_count = sum(1 for r in results if r['status'] == 'success')
    failed_count = len(results) - success_count
    
    report = {
        "timestamp": datetime.utcnow().isoformat(),
        "parameters": {
            "level": args.level,
            "limit": args.limit,
            "metalanguage": args.metalanguage,
            "model": args.model
        },
        "summary": {
            "total": len(results),
            "success": success_count,
            "failed": failed_count,
            "total_duration_sec": round(total_duration, 2),
            "avg_duration_sec": round(total_duration / len(results), 2) if results else 0
        },
        "results": results
    }
    
    # Save report
    output_path = Path(args.output)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total lessons: {len(results)}")
    print(f"Success: {success_count}")
    print(f"Failed: {failed_count}")
    print(f"Total time: {round(total_duration, 2)}s")
    print(f"Average time per lesson: {round(total_duration / len(results), 2)}s" if results else "N/A")
    print(f"\nReport saved to: {output_path.absolute()}")


if __name__ == "__main__":
    asyncio.run(main())

