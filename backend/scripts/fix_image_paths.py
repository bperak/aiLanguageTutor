#!/usr/bin/env python3
"""
Simple script to fix image paths in database by matching existing image files.

Usage:
    cd backend
    poetry run python scripts/fix_image_paths.py JF_105
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db import init_db_connections, AsyncSessionLocal
from sqlalchemy import text
import asyncio


async def fix_lesson_images(can_do_id: str):
    """Fix image paths for a specific lesson."""
    await init_db_connections()
    
    repo_root = Path(__file__).resolve().parents[2]
    image_dir = repo_root / "frontend" / "public" / "images" / "lessons" / "cando" / can_do_id.replace(":", "_")
    
    if not image_dir.exists():
        print(f"Image directory not found: {image_dir}")
        return
    
    # Find all PNG images
    image_files = sorted(image_dir.glob("*.png"))
    # Filter out test/placeholder images
    image_files = [f for f in image_files if "test" not in f.name.lower() and "placeholder" not in f.name.lower()]
    
    print(f"Found {len(image_files)} image files in {image_dir}")
    
    async with AsyncSessionLocal() as pg:
        # Get lesson
        result = await pg.execute(
            text("SELECT id FROM lessons WHERE can_do_id = :cid"),
            {"cid": can_do_id}
        )
        row = result.first()
        if not row:
            print(f"Lesson not found: {can_do_id}")
            return
        
        lesson_id = row[0]
        
        # Get latest version
        version_result = await pg.execute(
            text("SELECT version, lesson_plan FROM lesson_versions WHERE lesson_id = :lid ORDER BY version DESC LIMIT 1"),
            {"lid": lesson_id}
        )
        version_row = version_result.first()
        if not version_row:
            print(f"No version found for lesson {lesson_id}")
            return
        
        lesson_plan = version_row.lesson_plan
        version = version_row.version
        
        if isinstance(lesson_plan, str):
            lesson_plan = json.loads(lesson_plan)
        
        # Update image paths
        image_index = 0
        
        def update_paths(obj, path=[]):
            nonlocal image_index
            if isinstance(obj, dict):
                if "prompt" in obj and "style" in obj:
                    existing_path = obj.get("path", "")
                    # Check if needs update
                    if not existing_path or "test" in existing_path.lower():
                        if image_index < len(image_files):
                            rel_path = f"images/lessons/cando/{can_do_id.replace(':', '_')}/{image_files[image_index].name}"
                            obj["path"] = rel_path
                            print(f"  Updated: {'.'.join(path[-3:])} -> {rel_path}")
                            image_index += 1
                for key, value in obj.items():
                    update_paths(value, path + [key])
            elif isinstance(obj, list):
                for idx, item in enumerate(obj):
                    update_paths(item, path + [str(idx)])
        
        update_paths(lesson_plan)
        
        if image_index > 0:
            # Save back to database
            await pg.execute(
                text("UPDATE lesson_versions SET lesson_plan = :plan WHERE lesson_id = :lid AND version = :ver"),
                {
                    "plan": json.dumps(lesson_plan, ensure_ascii=False),
                    "lid": lesson_id,
                    "ver": version,
                }
            )
            await pg.commit()
            print(f"\n✓ Updated {image_index} image paths for {can_do_id}")
        else:
            print(f"\nNo images to update for {can_do_id}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/fix_image_paths.py <can_do_id>")
        sys.exit(1)
    
    asyncio.run(fix_lesson_images(sys.argv[1]))




