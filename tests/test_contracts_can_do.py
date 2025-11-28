import json
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACTS_DIR = REPO_ROOT / "specs" / "canDoDescriptorsIntegration" / "contracts"
COMPILED_DIR = REPO_ROOT / "resources" / "compiled" / "cando" / "JFまるごと_13"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.mark.unit
def test_compiled_exercises_shape():
    # Ensure compiled exercises match minimal contract expectations
    _ = load_json(CONTRACTS_DIR / "exercises.json")  # loaded for existence
    data = load_json(COMPILED_DIR / "exercises.json")

    assert isinstance(data, dict)
    assert data.get("can_do_id") == "JFまるごと:13"
    ex_list = data.get("exercises")
    assert isinstance(ex_list, list) and len(ex_list) >= 1

    first = ex_list[0]
    for key in ("id", "type", "prompt", "accepts", "answer_schema"):
        assert key in first


@pytest.mark.unit
def test_compiled_lesson_plan_shape():
    # Ensure compiled lesson plan matches minimal contract expectations
    _ = load_json(CONTRACTS_DIR / "lesson-plan.json")  # loaded for existence
    data = load_json(COMPILED_DIR / "lesson_plan.json")

    assert isinstance(data, dict)
    assert data.get("can_do_id") == "JFまるごと:13"
    assert isinstance(data.get("title"), str)

    sections = data.get("sections")
    assert isinstance(sections, list) and len(sections) >= 1
    assert all(isinstance(s, dict) and "type" in s for s in sections)


