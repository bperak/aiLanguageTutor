from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.services.image_generation_service import (
    generate_image_from_prompt,
    save_image_bytes,
)


logger = logging.getLogger(__name__)


def _repo_root() -> Path:
    """Get the repository root directory (aiLanguageTutor)."""
    # This file is at: backend/app/services/cando_image_service.py
    # We need to go up 4 levels: services -> app -> backend -> repo_root
    return Path(__file__).resolve().parents[3]


def sanitize_can_do_id(can_do_id: str) -> str:
    """Sanitize can_do_id for use in directory names."""
    return re.sub(r"[^\w\-_.]+", "_", can_do_id)


def extract_image_specs(lesson_data: Dict[str, Any]) -> List[Tuple[str, Dict[str, Any], List[str]]]:
    """Extract image specs lacking a path or with invalid/placeholder paths from a lesson JSON structure."""
    images: List[Tuple[str, Dict[str, Any], List[str]]] = []
    repo_root = _repo_root()

    def is_valid_image_path(path: str) -> bool:
        """Check if image path is valid (exists and is not a test/placeholder)."""
        if not path:
            return False
        
        # Filter out test/placeholder paths
        if "test" in path.lower() or "placeholder" in path.lower():
            return False
        
        # Check if file actually exists
        # Paths are relative from repo root, e.g., "images/lessons/cando/JF_105/image.png"
        # But images are stored in frontend/public/images/...
        image_path = repo_root / "frontend" / "public" / path
        return image_path.exists() and image_path.is_file()

    def traverse(obj: Any, path: List[str]) -> None:
        if isinstance(obj, dict):
            if "prompt" in obj and "style" in obj:
                existing_path = obj.get("path")
                # Include images without paths OR with invalid/placeholder paths
                if not existing_path or not is_valid_image_path(existing_path):
                    image_id = "-".join(path)
                    images.append((image_id, obj, path.copy()))
            for key, value in obj.items():
                traverse(value, path + [key])
        elif isinstance(obj, list):
            for idx, item in enumerate(obj):
                traverse(item, path + [str(idx)])

    traverse(lesson_data, [])
    return images


def generate_image_filename(image_id: str, index: int, extension: str = "png") -> str:
    """Generate a deterministic filename for an image."""
    safe_id = re.sub(r"[^\w\-_.]+", "_", image_id)
    if len(safe_id) > 50:
        safe_id = safe_id[:50]
    return f"{index:03d}-{safe_id}.{extension}"


def update_image_path(lesson_data: Dict[str, Any], path_location: List[str], image_path: str) -> None:
    """Update lesson structure with the generated image path."""
    current: Any = lesson_data
    for key in path_location[:-1]:
        if isinstance(current, dict):
            current = current.get(key)
        elif isinstance(current, list) and key.isdigit():
            current = current[int(key)]
        else:
            return
    if isinstance(current, dict) and path_location[-1] in current:
        image_obj = current[path_location[-1]]
        if isinstance(image_obj, dict):
            image_obj["path"] = image_path


def ensure_image_paths_for_lesson(
    lesson_data: Dict[str, Any],
    *,
    can_do_id: str,
    output_base_dir: Optional[Path] = None,
    dry_run: bool = False,
) -> Tuple[int, int]:
    """Generate images for any ImageSpec missing a path and update the lesson structure.
    
    Images are generated directly to frontend/public/images/lessons/cando/{can_do_id}/
    so Next.js can serve them without needing a copy step.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    image_specs = extract_image_specs(lesson_data)
    if not image_specs:
        return (0, 0)

    sanitized_id = sanitize_can_do_id(can_do_id)
    # Generate directly to frontend/public/images/ so Next.js can serve them
    repo_root = _repo_root()
    if output_base_dir is None:
        image_dir = repo_root / "frontend" / "public" / "images" / "lessons" / "cando" / sanitized_id
    else:
        # Allow override for testing or special cases
        image_dir = output_base_dir / "lessons" / "cando" / sanitized_id
    image_dir.mkdir(parents=True, exist_ok=True)

    if dry_run:
        for idx, (image_id, image_spec, _) in enumerate(image_specs):
            if image_spec.get("prompt"):
                filename = generate_image_filename(image_id or f"image_{idx}", idx)
                rel_path = f"images/lessons/cando/{sanitized_id}/{filename}"
                logger.info("[DRY RUN] Would generate %s", rel_path)
        return (0, len(image_specs))

    def generate_single_image(idx: int, image_id: str, image_spec: Dict[str, Any], path_location: List[str]) -> Optional[Tuple[str, bytes, List[str]]]:
        """Generate a single image (called in parallel)."""
        prompt = image_spec.get("prompt", "")
        if not prompt:
            return None
        
        try:
            filename = generate_image_filename(image_id or f"image_{idx}", idx)
            rel_path = f"images/lessons/cando/{sanitized_id}/{filename}"
            abs_path = image_dir / filename
            
            image_bytes = generate_image_from_prompt(
                prompt=prompt,
                negative_prompt=image_spec.get("negative_prompt"),
                size=image_spec.get("size", "1024x1024"),
            )
            return (rel_path, image_bytes, path_location)
        except Exception as exc:
            logger.warning("Failed to generate image '%s': %s", image_id, exc)
            return None

    generated = 0
    skipped = 0

    # Generate all images in parallel (max 5 concurrent to respect rate limits)
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(generate_single_image, idx, image_id, image_spec, path_location): idx
            for idx, (image_id, image_spec, path_location) in enumerate(image_specs)
        }
        
        for future in as_completed(futures):
            result = future.result()
            if result:
                rel_path, image_bytes, path_location = result
                try:
                    abs_path = image_dir / Path(rel_path).name
                    save_image_bytes(image_bytes, abs_path)
                    update_image_path(lesson_data, path_location, rel_path)
                    generated += 1
                    logger.info("Generated image: %s", rel_path)
                except Exception as exc:
                    logger.warning("Failed to save image: %s", exc)
                    skipped += 1
            else:
                skipped += 1

    return generated, skipped


__all__ = [
    "ensure_image_paths_for_lesson",
    "extract_image_specs",
    "generate_image_filename",
    "sanitize_can_do_id",
]

