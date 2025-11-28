#!/usr/bin/env python3
"""
Cleanup script to identify and optionally remove old v1 lessons from the database.

This script identifies:
1. Lessons with uiVersion = 1 in master JSONB (old format)
2. Lesson chunks associated with old versions
3. Lessons that don't have proper v2 LessonRoot structure

Usage:
    # Dry run (identify only, no changes)
    poetry run python scripts/cleanup_old_lessons.py --dry-run
    
    # Actually delete old lessons
    poetry run python scripts/cleanup_old_lessons.py --confirm
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Dict, List, Any

from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings

load_dotenv()


def is_v1_lesson(master_json: Dict[str, Any]) -> bool:
    """Check if a lesson is v1 format (uiVersion = 1)."""
    if not master_json:
        return False
    ui_version = master_json.get("uiVersion")
    return ui_version == 1


def is_v2_lesson(lesson_plan_json: Dict[str, Any]) -> bool:
    """Check if a lesson is v2 format (has LessonRoot structure with 'lesson' key)."""
    if not lesson_plan_json:
        return False
    # V2 has structure: {"lesson": {"meta": ..., "cards": ...}}
    return "lesson" in lesson_plan_json and isinstance(lesson_plan_json["lesson"], dict)


async def identify_old_lessons(pg: AsyncSession) -> List[Dict[str, Any]]:
    """Identify old v1 lessons in the database."""
    old_lessons = []
    
    # Query all lesson versions
    result = await pg.execute(text("""
        SELECT 
            l.id AS lesson_id,
            l.can_do_id,
            lv.id AS version_id,
            lv.version,
            lv.master,
            lv.lesson_plan,
            lv.created_at
        FROM lessons l
        JOIN lesson_versions lv ON l.id = lv.lesson_id
        ORDER BY l.can_do_id, lv.version
    """))
    
    rows = result.fetchall()
    print(f"Found {len(rows)} total lesson versions")
    
    for row in rows:
        lesson_id, can_do_id, version_id, version, master, lesson_plan, created_at = row
        
        is_old = False
        reason = []
        
        # Check master column (v1 format)
        if master:
            try:
                master_json = master if isinstance(master, dict) else json.loads(master)
                if is_v1_lesson(master_json):
                    is_old = True
                    reason.append("master has uiVersion=1")
            except Exception:
                pass
        
        # Check lesson_plan column (v2 format)
        if lesson_plan:
            try:
                plan_json = lesson_plan if isinstance(lesson_plan, dict) else json.loads(lesson_plan)
                if not is_v2_lesson(plan_json):
                    # If it has data but not v2 structure, might be old
                    if master and not is_old:
                        # Check if it's empty or malformed
                        if not isinstance(plan_json, dict) or not plan_json:
                            is_old = True
                            reason.append("lesson_plan is not v2 format")
            except Exception:
                pass
        
        # If no v2 structure and has old master, it's old
        if master and not lesson_plan:
            is_old = True
            reason.append("has master but no lesson_plan")
        
        if is_old:
            old_lessons.append({
                "lesson_id": lesson_id,
                "can_do_id": can_do_id,
                "version_id": version_id,
                "version": version,
                "created_at": str(created_at),
                "reason": ", ".join(reason) if reason else "old format"
            })
    
    return old_lessons


async def identify_old_sessions(pg: AsyncSession) -> List[Dict[str, Any]]:
    """Identify old v1 sessions or expired sessions."""
    old_sessions = []
    
    # Query all sessions (including expired ones)
    result = await pg.execute(text("""
        SELECT 
            id,
            can_do_id,
            master_json,
            created_at,
            expires_at
        FROM lesson_sessions
        ORDER BY created_at DESC
    """))
    
    rows = result.fetchall()
    print(f"\nFound {len(rows)} total lesson sessions")
    
    for row in rows:
        session_id, can_do_id, master_json, created_at, expires_at = row
        
        is_old = False
        reason = []
        
        # Check if expired
        if expires_at:
            from datetime import datetime, timezone
            if expires_at < datetime.now(timezone.utc):
                is_old = True
                reason.append("expired")
        
        # Check if v1 format
        if master_json:
            try:
                master = master_json if isinstance(master_json, dict) else json.loads(master_json)
                if is_v1_lesson(master):
                    is_old = True
                    reason.append("master has uiVersion=1")
            except Exception:
                pass
        
        if is_old:
            old_sessions.append({
                "session_id": str(session_id),
                "can_do_id": can_do_id,
                "created_at": str(created_at),
                "expires_at": str(expires_at) if expires_at else None,
                "reason": ", ".join(reason)
            })
    
    return old_sessions


async def count_associated_chunks(pg: AsyncSession, lesson_id: int, version: int) -> int:
    """Count lesson chunks for a specific lesson version."""
    result = await pg.execute(text("""
        SELECT COUNT(*) FROM lesson_chunks
        WHERE lesson_id = :lesson_id AND version = :version
    """), {"lesson_id": lesson_id, "version": version})
    return result.scalar() or 0


async def delete_old_lesson_version(
    pg: AsyncSession,
    version_id: int,
    lesson_id: int,
    version: int,
    can_do_id: str,
) -> Dict[str, Any]:
    """Delete a specific lesson version and its chunks."""
    # Delete chunks first (foreign key constraint)
    chunks_count = await count_associated_chunks(pg, lesson_id, version)
    if chunks_count > 0:
        await pg.execute(text("""
            DELETE FROM lesson_chunks
            WHERE lesson_id = :lesson_id AND version = :version
        """), {"lesson_id": lesson_id, "version": version})
    
    # Delete lesson version
    await pg.execute(text("""
        DELETE FROM lesson_versions
        WHERE id = :version_id
    """), {"version_id": version_id})
    
    # Check if this was the last version for this lesson
    remaining = await pg.execute(text("""
        SELECT COUNT(*) FROM lesson_versions
        WHERE lesson_id = :lesson_id
    """), {"lesson_id": lesson_id})
    remaining_count = remaining.scalar() or 0
    
    deleted_lesson = False
    if remaining_count == 0:
        # Delete the lesson entry too
        await pg.execute(text("""
            DELETE FROM lessons
            WHERE id = :lesson_id
        """), {"lesson_id": lesson_id})
        deleted_lesson = True
    
    await pg.commit()
    
    return {
        "version_id": version_id,
        "lesson_id": lesson_id,
        "version": version,
        "can_do_id": can_do_id,
        "chunks_deleted": chunks_count,
        "lesson_deleted": deleted_lesson
    }


async def main():
    parser = argparse.ArgumentParser(description="Cleanup old v1 lessons from database")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only identify old lessons, don't delete them"
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Actually delete old lessons (requires this flag)"
    )
    args = parser.parse_args()
    
    if not args.dry_run and not args.confirm:
        print("ERROR: Must specify either --dry-run or --confirm")
        print("Use --dry-run to see what would be deleted")
        print("Use --confirm to actually delete old lessons")
        return 1
    
    # Setup database connection
    # Convert DATABASE_URL to async driver format if needed
    database_url = settings.DATABASE_URL
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif not database_url.startswith("postgresql+asyncpg://"):
        # If it's just a connection string without protocol, add asyncpg
        if "@" in database_url:
            database_url = f"postgresql+asyncpg://{database_url}"
    
    engine = create_async_engine(
        database_url,
        echo=False,
        future=True
    )
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as pg:
        print("=" * 60)
        print("Scanning database for old lesson versions...")
        print("=" * 60)
        
        old_lessons = await identify_old_lessons(pg)
        old_sessions = await identify_old_sessions(pg)
        
        if not old_lessons and not old_sessions:
            print("\n✅ No old lessons or sessions found! Database is clean.")
            return 0
        
        total_count = len(old_lessons) + len(old_sessions)
        print(f"\n⚠️  Found {len(old_lessons)} old lesson version(s) and {len(old_sessions)} old session(s):\n")
        
        if old_lessons:
            print("📚 Old Lesson Versions:")
            # Group by can_do_id
            by_cando: Dict[str, List[Dict[str, Any]]] = {}
            for lesson in old_lessons:
                can_do_id = lesson["can_do_id"]
                if can_do_id not in by_cando:
                    by_cando[can_do_id] = []
                by_cando[can_do_id].append(lesson)
            
            for can_do_id, versions in by_cando.items():
                print(f"  📋 {can_do_id}:")
                for v in sorted(versions, key=lambda x: x["version"]):
                    chunks = await count_associated_chunks(pg, v["lesson_id"], v["version"])
                    print(f"     Version {v['version']} (ID: {v['version_id']}, created: {v['created_at'][:10]})")
                    print(f"       Reason: {v['reason']}")
                    print(f"       Chunks: {chunks}")
        
        if old_sessions:
            print("\n💾 Old Lesson Sessions:")
            # Group by can_do_id
            by_cando_sessions: Dict[str, List[Dict[str, Any]]] = {}
            for session in old_sessions:
                can_do_id = session["can_do_id"]
                if can_do_id not in by_cando_sessions:
                    by_cando_sessions[can_do_id] = []
                by_cando_sessions[can_do_id].append(session)
            
            for can_do_id, sessions in by_cando_sessions.items():
                print(f"  📋 {can_do_id}: {len(sessions)} session(s)")
                for s in sessions:
                    print(f"     Session {s['session_id'][:8]}... (created: {s['created_at'][:10]})")
                    print(f"       Reason: {s['reason']}")
        
        if args.dry_run:
            print("\n" + "=" * 60)
            print("DRY RUN - No changes made")
            print(f"Use --confirm to delete:")
            if old_lessons:
                print(f"  - {len(old_lessons)} old lesson version(s)")
            if old_sessions:
                print(f"  - {len(old_sessions)} old session(s)")
            print("=" * 60)
            return 0
        
        if args.confirm:
            print("\n" + "=" * 60)
            print(f"⚠️  DELETING old data...")
            print("=" * 60)
            
            deleted_lessons = []
            if old_lessons:
                print(f"\nDeleting {len(old_lessons)} old lesson version(s)...")
                for lesson in old_lessons:
                    result = await delete_old_lesson_version(
                        pg,
                        lesson["version_id"],
                        lesson["lesson_id"],
                        lesson["version"],
                        lesson["can_do_id"],
                    )
                    deleted_lessons.append(result)
                    print(f"✓ Deleted: {lesson['can_do_id']} v{lesson['version']} (chunks: {result['chunks_deleted']})")
            
            deleted_sessions = []
            if old_sessions:
                print(f"\nDeleting {len(old_sessions)} old session(s)...")
                for session in old_sessions:
                    await pg.execute(text("""
                        DELETE FROM lesson_sessions
                        WHERE id = :session_id
                    """), {"session_id": session["session_id"]})
                    deleted_sessions.append(session)
                    print(f"✓ Deleted session: {session['session_id'][:8]}... ({session['can_do_id']})")
                await pg.commit()
            
            print("\n" + "=" * 60)
            print("✅ Cleanup complete!")
            if deleted_lessons:
                print(f"  - Deleted {len(deleted_lessons)} old lesson version(s)")
            if deleted_sessions:
                print(f"  - Deleted {len(deleted_sessions)} old session(s)")
            print("=" * 60)
    
    await engine.dispose()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

