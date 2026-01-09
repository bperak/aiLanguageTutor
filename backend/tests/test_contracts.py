import json
from pathlib import Path

import pytest


def _repo_root() -> Path:
    """Find the backend repo root (supports running from monorepo or backend-only mounts)."""
    here = Path(__file__).resolve()
    for p in [here.parent, *here.parents]:
        if (p / "pyproject.toml").exists():
            return p
    return here.parents[1]


BASE = _repo_root()
CONTRACTS = BASE / "specs" / "canDoDescriptorsIntegration" / "contracts"
COMPILED = BASE / "resources" / "compiled" / "cando" / "JFまるごと_13"


def _load_json(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


@pytest.mark.unit
def test_compiled_exercises_match_contract_shape():
    if not CONTRACTS.exists() or not COMPILED.exists():
        pytest.skip("compiled contract fixtures not present in this checkout")
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
    if not CONTRACTS.exists() or not COMPILED.exists():
        pytest.skip("compiled contract fixtures not present in this checkout")
    data = _load_json(COMPILED / "lesson_plan.json")

    assert isinstance(data, dict)
    assert data.get("can_do_id") == "JFまるごと:13"
    assert isinstance(data.get("title"), str)
    sections = data.get("sections")
    assert isinstance(sections, list) and len(sections) >= 1
    assert all(isinstance(s, dict) and "type" in s for s in sections)


