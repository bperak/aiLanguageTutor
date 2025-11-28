#!/usr/bin/env python3
"""
Inject media references into LessonPlan JSON inside resources/canDoDescriptorExample.txt
based on frontend/public/images/lessons/cando/{can_do_id}/manifest.json attach_to_sections.

This helper is tailored for the example file and demonstrates the wiring.
Looks for manifest.json in frontend/public/images/ (new location) or images/ (legacy fallback).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict
import argparse

ROOT = Path(__file__).resolve().parent.parent
EXAMPLE = ROOT / "resources" / "canDoDescriptorExample.txt"


def extract_json_after(header: str, text: str) -> tuple[str, int, int]:
    marker = f"\n{header}\n"
    i = text.find(marker)
    if i == -1:
        raise ValueError(f"Header not found: {header}")
    start = i + len(marker)
    # find closing brace using simple bracket counting
    j = start
    brace = 0
    in_json = False
    while j < len(text):
        if text[j] == '{':
            brace += 1
            in_json = True
        elif text[j] == '}':
            brace -= 1
            if in_json and brace == 0:
                j += 1
                break
        j += 1
    json_str = text[start:j].strip()
    return json_str, start, j


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lesson", help="Path to compiled lesson_plan.json; if omitted, updates example block", default="")
    ap.add_argument("--manifest", help="Path to manifest.json; inferred from can_do_id if omitted", default="")
    args = ap.parse_args()

    if args.lesson:
        lesson_path = Path(args.lesson)
        lesson_plan = json.loads(lesson_path.read_text(encoding="utf-8"))
        can_do_id = lesson_plan.get("can_do_id")
        sanitized_id = can_do_id.replace(":", "_")
        
        if args.manifest:
            manifest_path = Path(args.manifest)
        else:
            # Try frontend/public/images/ first (new location)
            manifest_path = ROOT / "frontend" / "public" / "images" / "lessons" / "cando" / sanitized_id / "manifest.json"
            if not manifest_path.exists():
                # Fallback to legacy images/ directory
                manifest_path = ROOT / "images" / "lessons" / "cando" / sanitized_id / "manifest.json"
        
        if not manifest_path.exists():
            print(f"Manifest not found: {manifest_path}")
            return
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        attach = manifest.get("attach_to_sections", {})
        image_ids = sorted({iid for ids in attach.values() for iid in ids})
        lesson_plan["illustrations"] = [{"image_id": iid} for iid in image_ids]
        for section in lesson_plan.get("sections", []):
            stype = section.get("type")
            ids = attach.get(stype, [])
            if ids:
                section["media"] = [{"image_id": iid} for iid in ids]
        lesson_path.write_text(json.dumps(lesson_plan, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Updated compiled lesson with media: {lesson_path}")
        return

    # Fallback: update example file block
    raw = EXAMPLE.read_text(encoding="utf-8")
    lp_str, lp_start, lp_end = extract_json_after("LessonPlan JSON (ActivateCanDo output)", raw)
    lesson_plan = json.loads(lp_str)
    can_do_id = lesson_plan.get("can_do_id")
    sanitized_id = can_do_id.replace(":", "_")
    
    # Try frontend/public/images/ first (new location)
    manifest_path = ROOT / "frontend" / "public" / "images" / "lessons" / "cando" / sanitized_id / "manifest.json"
    if not manifest_path.exists():
        # Fallback to legacy images/ directory
        manifest_path = ROOT / "images" / "lessons" / "cando" / sanitized_id / "manifest.json"
    
    if not manifest_path.exists():
        print(f"Manifest not found: {manifest_path}")
        return
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    attach = manifest.get("attach_to_sections", {})
    image_ids = sorted({iid for ids in attach.values() for iid in ids})
    lesson_plan["illustrations"] = [{"image_id": iid} for iid in image_ids]
    for section in lesson_plan.get("sections", []):
        stype = section.get("type")
        ids = attach.get(stype, [])
        if ids:
            section["media"] = [{"image_id": iid} for iid in ids]
    new_lp_str = json.dumps(lesson_plan, ensure_ascii=False, indent=2)
    new_raw = raw[:lp_start] + "\n" + new_lp_str + "\n" + raw[lp_end:]
    EXAMPLE.write_text(new_raw, encoding="utf-8")
    print("LessonPlan updated with media references in example file.")


if __name__ == "__main__":
    main()


