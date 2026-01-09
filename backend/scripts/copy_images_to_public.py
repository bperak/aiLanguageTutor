#!/usr/bin/env python3
"""
[LEGACY/DEPRECATED] Copy generated lesson images from images/lessons/cando/ to frontend/public/images/lessons/cando/

NOTE: This script is deprecated. Images are now generated directly to frontend/public/images/
by the image generation service. This script is kept for:
- Migrating existing images from the old images/ directory
- Manual operations if needed

Usage:
    poetry run python scripts/copy_images_to_public.py
    poetry run python scripts/copy_images_to_public.py --clean  # Remove old images first
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
    parser = argparse.ArgumentParser(description="Copy lesson images to frontend public directory")
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Remove existing images in public directory before copying"
    )
    parser.add_argument(
        "--source",
        type=str,
        default=None,
        help="Source directory (default: repo_root/images/lessons/cando)"
    )
    parser.add_argument(
        "--dest",
        type=str,
        default=None,
        help="Destination directory (default: repo_root/frontend/public/images/lessons/cando)"
    )
    
    args = parser.parse_args()
    
    # Determine paths
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parents[1]
    
    source_dir = Path(args.source) if args.source else repo_root / "images" / "lessons" / "cando"
    dest_dir = Path(args.dest) if args.dest else repo_root / "frontend" / "public" / "images" / "lessons" / "cando"
    
    if not source_dir.exists():
        logger.error(f"Source directory not found: {source_dir}")
        return 1
    
    logger.info(f"Source: {source_dir}")
    logger.info(f"Destination: {dest_dir}")
    
    # Clean destination if requested
    if args.clean and dest_dir.exists():
        logger.info(f"Cleaning destination directory: {dest_dir}")
        shutil.rmtree(dest_dir)
    
    # Create destination structure
    dest_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy images
    copied = 0
    skipped = 0
    
    for can_do_dir in source_dir.iterdir():
        if not can_do_dir.is_dir():
            continue
        
        dest_can_do_dir = dest_dir / can_do_dir.name
        dest_can_do_dir.mkdir(parents=True, exist_ok=True)
        
        for img_file in can_do_dir.glob("*.png"):
            dest_file = dest_can_do_dir / img_file.name
            if not dest_file.exists() or args.clean:
                shutil.copy2(img_file, dest_file)
                logger.info(f"Copied: {img_file.name} -> {dest_file}")
                copied += 1
            else:
                skipped += 1
    
    logger.info("-" * 60)
    logger.info(f"Summary: {copied} copied, {skipped} skipped")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

