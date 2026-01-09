#!/usr/bin/env python3
"""
Sync existing image files from filesystem back to lesson database records.

This script scans the filesystem for generated images and updates the lesson_plan
JSON in the database to point to the correct image paths.

Usage (PowerShell):
    cd backend
    poetry run python scripts/sync_existing_images.py --can-do-id JF_105
    poetry run python scripts/sync_existing_images.py  # Sync all lessons
"""

import argparse
import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text
from app.db import init_db_connections, AsyncSessionLocal
import asyncio

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def sanitize_can_do_id(can_do_id: str) -> str:
    """Sanitize can_do_id for use in directory names."""
    return re.sub(r"[^\w\-_.]+", "_", can_do_id)


def find_images_in_directory(image_dir: Path) -> Dict[str, Path]:
    """Find all image files in a directory, indexed by a simplified key."""
    images = {}
    if not image_dir.exists():
        return images
    
    for img_file in image_dir.glob("*.png"):
        # Extract a key from filename (e.g., "000-lesson-cards-words-items-1-image" -> "words-items-1")
        key = img_file.stem
        images[key] = img_file
    return images


def update_image_paths_in_lesson(
    lesson_data: Dict[str, Any],
    image_dir: Path,
    can_do_id: str,
) -> int:
    """
    Update image paths in lesson data structure to point to existing files.
    
    Returns number of paths updated.
    """
    images_found = find_images_in_directory(image_dir)
    if not images_found:
        logger.warning(f"No images found in {image_dir}")
        return 0
    
    # Sort images by index (they should be numbered like 000-, 001-, etc.)
    sorted_images = sorted(images_found.items(), key=lambda x: x[0])
    
    updated_count = 0
    image_index = 0
    
    def traverse_and_update(obj: Any, path: List[str]) -> None:
        nonlocal updated_count, image_index
        if isinstance(obj, dict):
            if "prompt" in obj and "style" in obj:
                # Check if path is missing or invalid
                existing_path = obj.get("path", "")
                needs_update = (
                    not existing_path or 
                    "test" in existing_path.lower() or 
                    "placeholder" in existing_path.lower() or
                    not (image_dir / existing_path.replace(f"images/lessons/cando/{sanitize_can_do_id(can_do_id)}/", "")).exists() if existing_path else False
                )
                
                if needs_update and image_index < len(sorted_images):
                    # Use the next available image in order
                    img_key, img_path = sorted_images[image_index]
                    rel_path = f"images/lessons/cando/{sanitize_can_do_id(can_do_id)}/{img_path.name}"
                    obj["path"] = rel_path
                    updated_count += 1
                    image_index += 1
                    logger.info(f"Updated image path at {'.'.join(path[-3:])} -> {rel_path}")
            
            for key, value in obj.items():
                traverse_and_update(value, path + [key])
        elif isinstance(obj, list):
            for idx, item in enumerate(obj):
                traverse_and_update(item, path + [str(idx)])
    
    traverse_and_update(lesson_data, [])
    return updated_count


async def sync_lesson_images(can_do_id: Optional[str] = None) -> Dict[str, int]:
    """Sync images for one or all lessons."""
    # Initialize database connections
    await init_db_connections()
    
    repo_root = Path(__file__).resolve().parents[2]
    image_base_dir = repo_root / "frontend" / "public" / "images" / "lessons" / "cando"
    
    async with AsyncSessionLocal() as pg:
        # Find lessons
        if can_do_id:
            query = text("SELECT id, can_do_id FROM lessons WHERE can_do_id = :cid")
            result = await pg.execute(query, {"cid": can_do_id})
        else:
            query = text("SELECT id, can_do_id FROM lessons")
            result = await pg.execute(query)
        
        lessons = result.fetchall()
        
        if not lessons:
            logger.warning(f"No lessons found" + (f" for can_do_id={can_do_id}" if can_do_id else ""))
            return {}
        
        stats = {}
        
        for lesson_id, lesson_can_do_id in lessons:
            logger.info(f"Processing lesson: {lesson_can_do_id} (ID: {lesson_id})")
            
            # Get latest version
            version_query = text("""
                SELECT version, lesson_plan 
                FROM lesson_versions 
                WHERE lesson_id = :lid 
                ORDER BY version DESC LIMIT 1
            """)
            version_result = await pg.execute(version_query, {"lid": lesson_id})
            version_row = version_result.first()
            
            if not version_row:
                logger.warning(f"No version found for lesson {lesson_id}")
                continue
            
            lesson_plan = version_row.lesson_plan
            version = version_row.version
            
            if isinstance(lesson_plan, str):
                lesson_plan = json.loads(lesson_plan)
            
            if not lesson_plan:
                logger.warning(f"Empty lesson plan for {lesson_can_do_id}")
                continue
            
            # Find image directory
            sanitized_id = sanitize_can_do_id(lesson_can_do_id)
            image_dir = image_base_dir / sanitized_id
            
            # Update image paths
            updated_count = update_image_paths_in_lesson(lesson_plan, image_dir, lesson_can_do_id)
            
            if updated_count > 0:
                # Save back to database
                update_query = text("""
                    UPDATE lesson_versions 
                    SET lesson_plan = :plan 
                    WHERE lesson_id = :lid AND version = :ver
                """)
                await pg.execute(
                    update_query,
                    {
                        "plan": json.dumps(lesson_plan, ensure_ascii=False),
                        "lid": lesson_id,
                        "ver": version,
                    }
                )
                await pg.commit()
                logger.info(f"Updated {updated_count} image paths for {lesson_can_do_id}")
                stats[lesson_can_do_id] = updated_count
            else:
                logger.info(f"No images to update for {lesson_can_do_id}")
                stats[lesson_can_do_id] = 0
        
        return stats


def main():
    parser = argparse.ArgumentParser(description="Sync existing images to lesson database")
    parser.add_argument(
        "--can-do-id",
        type=str,
        default=None,
        help="CanDo ID to sync (default: sync all lessons)"
    )
    
    args = parser.parse_args()
    
    logger.info(f"Starting image sync" + (f" for can_do_id={args.can_do_id}" if args.can_do_id else " (all lessons)"))
    
    stats = asyncio.run(sync_lesson_images(args.can_do_id))
    
    logger.info("-" * 60)
    logger.info("Summary:")
    total_updated = sum(stats.values())
    for can_do_id, count in stats.items():
        logger.info(f"  {can_do_id}: {count} images updated")
    logger.info(f"Total: {total_updated} image paths updated")


if __name__ == "__main__":
    main()

