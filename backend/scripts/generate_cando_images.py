#!/usr/bin/env python3
"""
Generate images for CanDo lesson elements (words, dialogue, grammar, culture).

Scans lesson JSON files, extracts image prompts, generates images using Gemini,
and updates JSON files with image paths.

Usage (PowerShell):
    cd backend
    poetry run python scripts/generate_cando_images.py --limit 10 --dry-run
    poetry run python scripts/generate_cando_images.py --limit 10
"""

import argparse
import json
import logging
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.cando_image_service import (
    ensure_image_paths_for_lesson,
    extract_image_specs,
    generate_image_filename,
    sanitize_can_do_id,
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Try to load .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass
def process_lesson_file(
    lesson_path: Path,
    output_base_dir: Path,
    dry_run: bool = False,
) -> Tuple[int, int]:
    """
    Process a single lesson file.
    
    Returns: (images_generated, images_skipped)
    """
    logger.info(f"Processing lesson: {lesson_path}")
    
    # Load lesson JSON
    try:
        with open(lesson_path, 'r', encoding='utf-8') as f:
            lesson_data = json.load(f)
    except Exception as e:
        logger.error(f"Failed to load {lesson_path}: {e}")
        return (0, 0)
    
    # Extract can_do_id for directory structure
    can_do_id = None
    try:
        if 'lesson' in lesson_data and 'meta' in lesson_data['lesson']:
            can_do_id = lesson_data['lesson']['meta'].get('can_do', {}).get('uid')
        if not can_do_id:
            # Try to extract from filename
            filename = lesson_path.stem
            match = re.search(r'canDo[_-]([^_]+)', filename)
            if match:
                can_do_id = match.group(1)
    except Exception:
        pass
    
    if not can_do_id:
        logger.warning(f"Could not extract can_do_id from {lesson_path}, using filename")
        can_do_id = lesson_path.stem
    
    # Extract image specs
    image_specs = extract_image_specs(lesson_data)
    
    if not image_specs:
        logger.info(f"No images to generate in {lesson_path}")
        return (0, 0)
    
    logger.info(f"Found {len(image_specs)} image(s) to generate")
    
    sanitized_id = sanitize_can_do_id(can_do_id)

    if dry_run:
        for idx, (image_id, image_spec, _path_location) in enumerate(image_specs):
            prompt = image_spec.get('prompt', '')
            if not prompt:
                logger.warning(f"Skipping image {image_id}: no prompt")
                continue
            filename = generate_image_filename(image_id, idx)
            image_path_rel = f"images/lessons/cando/{sanitized_id}/{filename}"
            logger.info(f"[DRY RUN] Would generate: {image_path_rel}")
            logger.info(f"  Prompt: {prompt[:100]}...")
        return (0, len(image_specs))

    gen_count, skip_count = ensure_image_paths_for_lesson(
        lesson_data,
        can_do_id=can_do_id,
        output_base_dir=output_base_dir,
        dry_run=False,
    )

    if gen_count > 0:
        try:
            for target_path in [
                lesson_path,
                Path(lesson_path.parent.parent.parent) / "generated" / "lessons_v2" / lesson_path.name,
            ]:
                if target_path.parent.exists():
                    with open(target_path, 'w', encoding='utf-8') as f:
                        json.dump(lesson_data, f, ensure_ascii=False, indent=2)
                    logger.info(f"Updated lesson JSON: {target_path}")
                    break
        except Exception as e:
            logger.error(f"Failed to save updated lesson JSON: {e}")

    return (gen_count, skip_count)


def main():
    parser = argparse.ArgumentParser(description="Generate images for CanDo lesson elements")
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of lessons to process (default: 10)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview without generating images"
    )
    parser.add_argument(
        "--input-dir",
        type=str,
        default=None,
        help="Input directory (default: auto-detect from backend/lessons_v2 or generated/lessons_v2)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Output base directory for images (default: None = generate directly to frontend/public/images/)"
    )
    
    args = parser.parse_args()
    
    # Determine input directory
    repo_root = Path(__file__).resolve().parents[2]
    if args.input_dir:
        input_dir = Path(args.input_dir)
    else:
        # Try backend/lessons_v2 first, then generated/lessons_v2
        input_dir = repo_root / "backend" / "lessons_v2"
        if not input_dir.exists():
            input_dir = repo_root / "generated" / "lessons_v2"
    
    if not input_dir.exists():
        logger.error(f"Input directory not found: {input_dir}")
        return 1
    
    # Determine output directory (default is None, which means generate directly to frontend/public/images/)
    output_dir = Path(args.output_dir) if args.output_dir else None
    
    logger.info(f"Input directory: {input_dir}")
    if output_dir:
        logger.info(f"Output directory (override): {output_dir}")
    else:
        logger.info(f"Output directory: frontend/public/images/ (default)")
    logger.info(f"Dry run: {args.dry_run}")
    logger.info(f"Limit: {args.limit}")
    logger.info("-" * 60)
    
    # Find lesson JSON files
    lesson_files = sorted(input_dir.glob("canDo_*.json"))[:args.limit]
    
    if not lesson_files:
        logger.warning(f"No lesson files found in {input_dir}")
        return 1
    
    logger.info(f"Found {len(lesson_files)} lesson file(s) to process")
    
    total_generated = 0
    total_skipped = 0
    
    for lesson_file in lesson_files:
        generated, skipped = process_lesson_file(
            lesson_file,
            output_dir,
            dry_run=args.dry_run
        )
        total_generated += generated
        total_skipped += skipped
    
    logger.info("-" * 60)
    logger.info(f"Summary: {total_generated} generated, {total_skipped} skipped")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

