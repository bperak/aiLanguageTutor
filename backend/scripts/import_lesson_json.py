#!/usr/bin/env python3
"""
Import pre-generated lesson JSON files into PostgreSQL database.

Usage:
    poetry run python scripts/import_lesson_json.py generated/lessons_v2/canDo_JF_105_v1.json
    poetry run python scripts/import_lesson_json.py --dir generated/lessons_v2
"""
import asyncio
import argparse
import json
import sys
from pathlib import Path
from datetime import datetime

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db import init_db_connections, AsyncSessionLocal
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def import_lesson_file(pg, file_path: Path) -> dict:
    """
    Import a single lesson JSON file into the database.
    
    Args:
        pg: PostgreSQL session
        file_path: Path to the lesson JSON file
        
    Returns:
        Dictionary with import result
    """
    try:
        # Read and parse JSON file
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Extract lesson data
        if "lesson" not in data:
            return {
                "file": str(file_path),
                "status": "failed",
                "error": "Missing 'lesson' key in JSON"
            }
        
        lesson_data = data["lesson"]
        
        # Extract can_do_id from meta
        can_do_id = lesson_data.get("meta", {}).get("can_do", {}).get("uid")
        if not can_do_id:
            return {
                "file": str(file_path),
                "status": "failed",
                "error": "Missing can_do uid in lesson.meta.can_do.uid"
            }
        
        lesson_id_str = lesson_data.get("meta", {}).get("lesson_id", "")
        
        # Check if lesson already exists
        result = await pg.execute(
            text("SELECT id FROM lessons WHERE can_do_id = :cid LIMIT 1"),
            {"cid": can_do_id}
        )
        row = result.first()
        
        if row:
            lesson_id = int(row[0])
            action = "updated"
        else:
            # Create new lesson record
            ins = await pg.execute(
                text("INSERT INTO lessons (can_do_id, status) VALUES (:cid, 'published') RETURNING id"),
                {"cid": can_do_id}
            )
            lesson_id = int(ins.first()[0])
            action = "created"
        
        # Get next version number
        ver_row = (
            await pg.execute(
                text("SELECT COALESCE(MAX(version), 0) FROM lesson_versions WHERE lesson_id = :lid"),
                {"lid": lesson_id}
            )
        ).first()
        next_ver = int(ver_row[0]) + 1
        
        # Insert lesson version
        await pg.execute(
            text("""
                INSERT INTO lesson_versions (lesson_id, version, lesson_plan, created_at)
                VALUES (:lid, :ver, :plan, :created)
            """),
            {
                "lid": lesson_id,
                "ver": next_ver,
                "plan": json.dumps(lesson_data, ensure_ascii=False),
                "created": datetime.utcnow()
            }
        )
        
        await pg.commit()
        
        logger.info(
            "lesson_imported",
            can_do_id=can_do_id,
            lesson_id=lesson_id,
            version=next_ver,
            action=action,
            file=str(file_path)
        )
        
        return {
            "file": str(file_path),
            "status": "success",
            "action": action,
            "can_do_id": can_do_id,
            "lesson_id": lesson_id,
            "version": next_ver
        }
        
    except Exception as e:
        logger.error("lesson_import_failed", error=str(e), file=str(file_path))
        return {
            "file": str(file_path),
            "status": "failed",
            "error": str(e)
        }


async def import_directory(pg, directory: Path) -> list:
    """Import all JSON files from a directory."""
    results = []
    json_files = list(directory.glob("*.json"))
    
    if not json_files:
        print(f"No JSON files found in {directory}")
        return results
    
    print(f"Found {len(json_files)} JSON files to import")
    print("-" * 60)
    
    for idx, file_path in enumerate(json_files, 1):
        print(f"[{idx}/{len(json_files)}] Importing {file_path.name}...")
        result = await import_lesson_file(pg, file_path)
        results.append(result)
        
        status_symbol = "✓" if result["status"] == "success" else "✗"
        if result["status"] == "success":
            print(f"  {status_symbol} {result['action']} - {result['can_do_id']} (v{result['version']})")
        else:
            print(f"  {status_symbol} Failed: {result['error']}")
        print()
    
    return results


async def main():
    parser = argparse.ArgumentParser(description="Import lesson JSON files into database")
    parser.add_argument("path", nargs="?", help="Path to JSON file or directory")
    parser.add_argument("--dir", help="Import all JSON files from directory")
    parser.add_argument("--output", default="import_report.json", help="Output report filename")
    
    args = parser.parse_args()
    
    # Determine what to import
    if args.dir:
        target_path = Path(args.dir)
        is_directory = True
    elif args.path:
        target_path = Path(args.path)
        is_directory = target_path.is_dir()
    else:
        # Default to generated/lessons_v2 directory
        target_path = Path("generated/lessons_v2")
        is_directory = True
    
    if not target_path.exists():
        print(f"Error: Path does not exist: {target_path}")
        return 1
    
    print(f"AI Language Tutor - Lesson Import Tool")
    print(f"=" * 60)
    print(f"Target: {target_path}")
    print(f"Type: {'Directory' if is_directory else 'File'}")
    print("-" * 60)
    
    # Initialize database
    await init_db_connections()
    print("✓ Database connection initialized")
    print()
    
    # Import lessons
    async with AsyncSessionLocal() as pg:
        if is_directory:
            results = await import_directory(pg, target_path)
        else:
            result = await import_lesson_file(pg, target_path)
            results = [result]
    
    # Generate summary
    success_count = sum(1 for r in results if r["status"] == "success")
    failed_count = len(results) - success_count
    
    print("=" * 60)
    print("IMPORT SUMMARY")
    print("=" * 60)
    print(f"Total files: {len(results)}")
    print(f"Success: {success_count}")
    print(f"Failed: {failed_count}")
    
    if failed_count > 0:
        print("\nFailed imports:")
        for r in results:
            if r["status"] == "failed":
                print(f"  - {Path(r['file']).name}: {r['error']}")
    
    # Save detailed report
    report = {
        "timestamp": datetime.utcnow().isoformat(),
        "target": str(target_path),
        "summary": {
            "total": len(results),
            "success": success_count,
            "failed": failed_count
        },
        "results": results
    }
    
    output_path = Path(args.output)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\nDetailed report saved to: {output_path.absolute()}")
    
    return 0 if failed_count == 0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

