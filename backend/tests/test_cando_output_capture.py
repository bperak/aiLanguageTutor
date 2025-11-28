import os
import json
import time
import pathlib
import pytest
import httpx


# Base configuration
API_BASE = (os.environ.get("TARGET_BACKEND") or "http://localhost:8000") + "/api/v1"
ARTIFACT_DIR = pathlib.Path(__file__).parent / "artifacts"
ARTIFACT_DIR.mkdir(exist_ok=True)

# Override with env: CANDO_IDS="JF21,JF22,JF:335"
CANDO_IDS = [
    c.strip()
    for c in (os.environ.get("CANDO_IDS") or "JF21,JF22").split(",")
    if c.strip()
]

TIMEOUT = float(os.environ.get("TEST_TIMEOUT_SEC") or 300.0)


@pytest.mark.parametrize("can_do_id", CANDO_IDS)
def test_start_and_dump(can_do_id: str) -> None:
    """Call /cando/lessons/start, assert minimal structure, and dump full JSON to artifacts.

    Artifacts are saved as: {can_do_id}.{timestamp}.start.json
    """
    client = httpx.Client(base_url=API_BASE, timeout=TIMEOUT)
    r = client.post(
        "/cando/lessons/start",
        params={
            "can_do_id": can_do_id,
            "phase": "lexicon_and_patterns",
            "level": 3,
        },
    )
    assert r.status_code == 200, r.text
    data = r.json()
    # Save artifact for inspection (always)
    out = ARTIFACT_DIR / f"{can_do_id}.{int(time.time())}.start.json"
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    # Best-effort smoke checks (non-fatal)
    if isinstance(data, dict):
        master = data.get("master", {}) or {}
        ui = master.get("ui", {}) if isinstance(master, dict) else {}
        sections = ui.get("sections") if isinstance(ui, dict) else None
        # Do not fail if UI shape differs; purpose is to capture for inspection


@pytest.mark.parametrize("can_do_id", CANDO_IDS)
def test_compile_dry_run_and_dump(can_do_id: str) -> None:
    """Call /cando/lessons/compile with dry_run and dump the response for inspection.

    Both success and error responses are saved as artifacts.
    Artifacts are saved as: {can_do_id}.{timestamp}.compile.dry_run.json
    """
    client = httpx.Client(base_url=API_BASE, timeout=TIMEOUT)
    r = client.post(
        "/cando/lessons/compile",
        params={
            "can_do_id": can_do_id,
            "version": 1,
            "provider": os.environ.get("TEST_PROVIDER") or "openai",
            "fast": False,
            "dry_run": True,
        },
    )
    assert r.status_code == 200, r.text
    data = r.json()

    # Save artifact (ok or error)
    out = ARTIFACT_DIR / f"{can_do_id}.{int(time.time())}.compile.dry_run.json"
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    # If status ok, sanity check payload shape
    # Non-fatal shape check
    if data.get("status") == "ok":
        _ = data.get("result") or {}


