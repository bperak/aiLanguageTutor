#!/usr/bin/env python3
"""
Generate lesson illustration placeholders and manifest from prompts.

Simple workflow:
- Read prompts from resources/canDoDescriptorExample.txt (block: IllustrationGenerationPrompts)
- Create output directory under frontend/public/images/lessons/cando/{can_do_id_sanitized}/
- For each asset, create a placeholder PNG and collect manifest entries
- Write manifest.json and a per-section attachment map

Note: This scaffolds file I/O; hooking to image APIs (e.g., Gemini) is left for a later step.
Images are written to frontend/public/images/ so Next.js can serve them directly.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
import argparse
from typing import Any, Dict, List

from PIL import Image, ImageDraw  # type: ignore

ROOT = Path(__file__).resolve().parent.parent
PROMPTS_FILE = ROOT / "resources" / "canDoDescriptorExample.txt"


def extract_block(text: str, header: str) -> str:
    marker = f"\n{header}\n"
    idx = text.find(marker)
    if idx == -1:
        raise ValueError(f"Block '{header}' not found")
    start = idx + len(marker)
    # find next top-level header (--- or \n\n<Cap>)
    end = text.find("\n---\n", start)
    if end == -1:
        end = len(text)
    return text[start:end].strip()


def sanitize_dir(name: str) -> str:
    return re.sub(r"[^\w\-_.]+", "_", name)


def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def create_placeholder(path: Path, label: str, size: str) -> None:
    w, h = (1024, 1024)
    if "x" in size:
        try:
            w, h = map(int, size.lower().split("x"))
        except Exception:
            pass
    img = Image.new("RGB", (w, h), color=(245, 247, 250))
    draw = ImageDraw.Draw(img)
    draw.rectangle([(20, 20), (w - 20, h - 20)], outline=(200, 205, 210), width=3)
    draw.text((40, 40), label, fill=(80, 80, 80))
    img.save(path)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompts", help="Path to compiled illustration_prompts.json", default="")
    args = ap.parse_args()

    if args.prompts:
        data = json.loads(Path(args.prompts).read_text(encoding="utf-8"))
    else:
        text = PROMPTS_FILE.read_text(encoding="utf-8")
        block = extract_block(text, "IllustrationGenerationPrompts (for Gemini Flash Image or similar)")
        data = json.loads(block)

    can_do_id: str = data["can_do_id"]
    # Default to frontend/public/images/ so Next.js can serve them
    out_dir_raw: str = data.get("output_dir") or f"frontend/public/images/lessons/cando/{sanitize_dir(can_do_id)}/"
    out_dir = ROOT / out_dir_raw
    ensure_dir(out_dir)

    size = data.get("image_specs", {}).get("size", "1024x1024")
    assets: List[Dict[str, Any]] = data.get("assets", [])

    manifest: Dict[str, Any] = {
        "can_do_id": can_do_id,
        "images": [],
    }

    for asset in assets:
        image_id = asset["image_id"]
        filename = f"{image_id}.png"
        label = f"{can_do_id} / {image_id}"
        create_placeholder(out_dir / filename, label, size)
        manifest["images"].append(
            {
                "image_id": image_id,
                "path": filename,
                # English-only: do not include language-specific alts
                # If needed later, add a generic 'alt' field.
                "anchors": asset.get("anchors", []),
            }
        )

    # Section attachments
    post = data.get("postprocess", {})
    manifest_path = post.get("manifest_path") or str(out_dir / "manifest.json")
    attach = post.get("attach_to_sections", {})
    manifest["attach_to_sections"] = attach

    # Write manifest
    out_manifest = ROOT / manifest_path
    ensure_dir(out_manifest.parent)
    out_manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Wrote placeholders to: {out_dir}")
    print(f"Wrote manifest: {out_manifest}")


if __name__ == "__main__":
    main()


