#!/usr/bin/env python3
"""
Parse named JSON blocks from resources/canDoDescriptorExample.txt and write compiled artifacts.

Blocks extracted (header → output filename):
- LessonPlan JSON (ActivateCanDo output) → lesson_plan.json
- ExerciseBundle JSON (GenerateExercises output — sample) → exercises.json
- SampleDialog JSON (conventional expressions) → sample_dialog.json
- StagedExercises JSON (phased integration) → stages.json
- PragmaticPatterns (instances) → pragmatic_patterns.json
- IllustrationGenerationPrompts (for Gemini Flash Image or similar) → illustration_prompts.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "resources" / "canDoDescriptorExample.txt"

HEADERS = [
    ("LessonPlan JSON (ActivateCanDo output)", "lesson_plan.json"),
    ("ExerciseBundle JSON (GenerateExercises output — sample)", "exercises.json"),
    ("SampleDialog JSON (conventional expressions)", "sample_dialog.json"),
    ("StagedExercises JSON (phased integration)", "stages.json"),
    ("PragmaticPatterns (instances)", "pragmatic_patterns.json"),
    ("IllustrationGenerationPrompts (for Gemini Flash Image or similar)", "illustration_prompts.json"),
]


def extract_json_block(text: str, header: str) -> str:
    marker = f"\n{header}\n"
    i = text.find(marker)
    if i == -1:
        raise ValueError(f"Header not found: {header}")
    start = i + len(marker)
    # find JSON object from start using brace counting
    j = start
    # skip leading whitespace/newlines
    while j < len(text) and text[j] in " \t\r\n":
        j += 1
    if j >= len(text) or text[j] != '{':
        raise ValueError(f"JSON block not found after header: {header}")
    brace = 0
    k = j
    while k < len(text):
        if text[k] == '{':
            brace += 1
        elif text[k] == '}':
            brace -= 1
            if brace == 0:
                k += 1
                break
        k += 1
    return text[j:k]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default=str(SRC))
    ap.add_argument("--can-do-id", default="JFまるごと:13")
    args = ap.parse_args()

    src = Path(args.file)
    text = src.read_text(encoding="utf-8")
    out_dir = ROOT / "resources" / "compiled" / "cando" / args.can_do_id.replace(":", "_")
    out_dir.mkdir(parents=True, exist_ok=True)

    for header, fname in HEADERS:
        try:
            block = extract_json_block(text, header)
            # validate JSON
            _ = json.loads(block)
            (out_dir / fname).write_text(json.dumps(json.loads(block), ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"Wrote {fname}")
        except Exception as e:  # noqa: BLE001
            print(f"Skip {fname}: {e}")

    print(f"Compiled artifacts in: {out_dir}")


if __name__ == "__main__":
    main()


