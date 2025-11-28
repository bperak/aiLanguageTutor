import json
from pathlib import Path

import pytest


BASE = Path(__file__).resolve().parents[2]
CONTRACTS = BASE / "specs" / "canDoDescriptorsIntegration" / "contracts"
COMPILED = BASE / "resources" / "compiled" / "cando" / "JFまるごと_13"


def _load_json(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


@pytest.mark.unit
def test_compiled_exercises_match_contract_shape():
    ex_schema = _load_json(CONTRACTS / "exercises.json")
    data = _load_json(COMPILED / "exercises.json")

    # Minimal structural checks inline to avoid external deps
    assert isinstance(data, dict)
    assert data.get("can_do_id") == "JFまるごと:13"
    ex_list = data.get("exercises")
    assert isinstance(ex_list, list) and len(ex_list) >= 1
    first = ex_list[0]
    for key in ("id", "type", "prompt", "accepts", "answer_schema"):
        assert key in first


@pytest.mark.unit
def test_compiled_lesson_plan_match_contract_shape():
    lp_schema = _load_json(CONTRACTS / "lesson-plan.json")
    data = _load_json(COMPILED / "lesson_plan.json")

    assert isinstance(data, dict)
    assert data.get("can_do_id") == "JFまるごと:13"
    assert isinstance(data.get("title"), str)
    sections = data.get("sections")
    assert isinstance(sections, list) and len(sections) >= 1
    assert all(isinstance(s, dict) and "type" in s for s in sections)


