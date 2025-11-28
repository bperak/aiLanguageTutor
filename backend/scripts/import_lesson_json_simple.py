#!/usr/bin/env python3
"""
Simple standalone import script for lesson JSON files.
Doesn't depend on app modules - just reads .env and imports directly.

Usage:
    python scripts/import_lesson_json_simple.py ../generated/lessons_v2/canDo_JF_105_v1.json
    python scripts/import_lesson_json_simple.py --dir ../generated/lessons_v2
"""
import asyncio
import argparse
import json
import os
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

# Load environment variables
load_dotenv()


async def get_db_session():
    """Create database session."""
    database_url = os.getenv("DATABASE_URL")
    
    if not database_url:
        raise ValueError("DATABASE_URL not found in environment")
    
    # Ensure async driver
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif not database_url.startswith("postgresql+asyncpg://"):
        # Add async driver if not present
        if "://" in database_url:
            protocol, rest = database_url.split("://", 1)
            database_url = f"postgresql+asyncpg://{rest}"
    
    engine = create_async_engine(database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    return async_session()


async def import_lesson_file(pg, file_path: Path) -> dict:
    """Import a single lesson JSON file."""
    try:
        # Read JSON
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Validate structure
        if "lesson" not in data:
            return {
                "file": str(file_path),
                "status": "failed",
                "error": "Missing 'lesson' key"
            }
        
        lesson_data = data["lesson"]
        can_do_id = lesson_data.get("meta", {}).get("can_do", {}).get("uid")
        
        if not can_do_id:
            return {
                "file": str(file_path),
                "status": "failed",
                "error": "Missing can_do uid"
            }
        
        # Check if lesson exists
        result = await pg.execute(
            text("SELECT id FROM lessons WHERE can_do_id = :cid LIMIT 1"),
            {"cid": can_do_id}
        )
        row = result.first()
        
        if row:
            lesson_id = int(row[0])
            action = "updated"
        else:
            # Create new lesson
            ins = await pg.execute(
                text("INSERT INTO lessons (can_do_id, status) VALUES (:cid, 'published') RETURNING id"),
                {"cid": can_do_id}
            )
            lesson_id = int(ins.first()[0])
            action = "created"
        
        # Get next version
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
                VALUES (:lid, :ver, :plan::jsonb, :created)
            """),
            {
                "lid": lesson_id,
                "ver": next_ver,
                "plan": json.dumps(lesson_data, ensure_ascii=False),
                "created": datetime.utcnow()
            }
        )
        
        await pg.commit()
        
        return {
            "file": str(file_path),
            "status": "success",
            "action": action,
            "can_do_id": can_do_id,
            "lesson_id": lesson_id,
            "version": next_ver
        }
        
    except Exception as e:
        return {
            "file": str(file_path),
            "status": "failed",
            "error": str(e)
        }


async def main():
    parser = argparse.ArgumentParser(description="Import lesson JSON files")
    parser.add_argument("path", nargs="?", help="Path to JSON file or directory")
    parser.add_argument("--dir", help="Directory with JSON files")
    
    args = parser.parse_args()
    
    # Determine target
    if args.dir:
        target_path = Path(args.dir)
        is_directory = True
    elif args.path:
        target_path = Path(args.path)
        is_directory = target_path.is_dir()
    else:
        target_path = Path("../generated/lessons_v2")
        is_directory = True
    
    if not target_path.exists():
        print(f"Error: Path not found: {target_path}")
        return 1
    
    print(f"Lesson Import Tool")
    print(f"=" * 60)
    print(f"Target: {target_path}")
    print("-" * 60)
    
    # Get files to import
    if is_directory:
        json_files = list(target_path.glob("*.json"))
    else:
        json_files = [target_path]
    
    if not json_files:
        print("No JSON files found")
        return 1
    
    print(f"Found {len(json_files)} file(s)")
    print()
    
    # Import
    results = []
    async with await get_db_session() as pg:
        for idx, file_path in enumerate(json_files, 1):
            print(f"[{idx}/{len(json_files)}] {file_path.name}...", end=" ")
            result = await import_lesson_file(pg, file_path)
            results.append(result)
            
            if result["status"] == "success":
                print(f"OK {result['action']} - {result['can_do_id']} (v{result['version']})")
            else:
                print(f"X {result['error']}")
    
    # Summary
    success = sum(1 for r in results if r["status"] == "success")
    failed = len(results) - success
    
    print()
    print("=" * 60)
    print(f"Total: {len(results)} | Success: {success} | Failed: {failed}")
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    exit(asyncio.run(main()))

