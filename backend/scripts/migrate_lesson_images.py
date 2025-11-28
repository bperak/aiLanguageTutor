#!/usr/bin/env python3
"""
Migrate lesson images from legacy images/lessons/cando/ to frontend/public/images/lessons/cando/

This script helps transition from the old image location to the new location where
Next.js can serve them directly. After migration, images/lessons/cando/ can be removed.

Usage (PowerShell):
    cd backend
    poetry run python scripts/migrate_lesson_images.py --dry-run
    poetry run python scripts/migrate_lesson_images.py
"""

import argparse
import logging
import shutil
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Migrate lesson images from legacy images/ to frontend/public/images/")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview migration without copying files"
    )
    parser.add_argument(
        "--delete-source",
        action="store_true",
        help="Delete source files after successful migration (use with caution!)"
    )
    
    args = parser.parse_args()
    
    # Determine paths
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parents[1]
    
    source_dir = repo_root / "images" / "lessons" / "cando"
    dest_dir = repo_root / "frontend" / "public" / "images" / "lessons" / "cando"
    
    if not source_dir.exists():
        logger.info(f"Source directory not found: {source_dir}")
        logger.info("Nothing to migrate!")
        return 0
    
    logger.info(f"Source: {source_dir}")
    logger.info(f"Destination: {dest_dir}")
    logger.info(f"Dry run: {args.dry_run}")
    if args.delete_source:
        logger.warning("WILL DELETE SOURCE FILES AFTER MIGRATION!")
    logger.info("-" * 60)
    
    if args.dry_run:
        logger.info("[DRY RUN] Would migrate the following:")
    
    migrated = 0
    skipped = 0
    errors = 0
    
    # Process each lesson directory
    for lesson_dir in source_dir.iterdir():
        if not lesson_dir.is_dir():
            continue
        
        lesson_id = lesson_dir.name
        dest_lesson_dir = dest_dir / lesson_id
        dest_lesson_dir.mkdir(parents=True, exist_ok=True)
        
        # Migrate image files
        for img_file in lesson_dir.glob("*.png"):
            dest_file = dest_lesson_dir / img_file.name
            if dest_file.exists():
                logger.warning(f"Skipping (already exists): {img_file.name} in {lesson_id}/")
                skipped += 1
                continue
            
            if args.dry_run:
                logger.info(f"[DRY RUN] Would copy: {img_file.relative_to(repo_root)} -> {dest_file.relative_to(repo_root)}")
            else:
                try:
                    shutil.copy2(img_file, dest_file)
                    logger.info(f"Copied: {img_file.name} in {lesson_id}/")
                    migrated += 1
                except Exception as exc:
                    logger.error(f"Failed to copy {img_file.name}: {exc}")
                    errors += 1
        
        # Migrate manifest.json if present
        manifest_source = lesson_dir / "manifest.json"
        if manifest_source.exists():
            manifest_dest = dest_lesson_dir / "manifest.json"
            if manifest_dest.exists():
                logger.warning(f"Skipping manifest.json (already exists): {lesson_id}/")
            elif args.dry_run:
                logger.info(f"[DRY RUN] Would copy: manifest.json in {lesson_id}/")
            else:
                try:
                    shutil.copy2(manifest_source, manifest_dest)
                    logger.info(f"Copied: manifest.json in {lesson_id}/")
                    migrated += 1
                except Exception as exc:
                    logger.error(f"Failed to copy manifest.json: {exc}")
                    errors += 1
    
    logger.info("-" * 60)
    logger.info(f"Summary: {migrated} migrated, {skipped} skipped, {errors} errors")
    
    if not args.dry_run and migrated > 0 and args.delete_source:
        logger.warning("Deleting source directory as requested...")
        try:
            shutil.rmtree(source_dir)
            logger.info(f"Deleted: {source_dir}")
        except Exception as exc:
            logger.error(f"Failed to delete source directory: {exc}")
            return 1
    elif not args.dry_run and migrated > 0:
        logger.info("Migration complete. You can manually delete images/lessons/cando/ after verifying.")
    
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

