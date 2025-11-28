import os
import json
import time
from urllib.parse import quote

import requests


API = os.environ.get("API_BASE_URL", "http://localhost:8000")


def _retry_get(url: str, tries: int = 5, sleep_s: float = 0.8):
    last = None
    for _ in range(tries):
        try:
            r = requests.get(url, timeout=5)
            if r.status_code == 200:
                return r
            last = r
        except Exception as e:  # pragma: no cover
            last = e
        time.sleep(sleep_s)
    raise AssertionError(f"GET retry failed for {url}: {last}")


def test_lesson_flow_activate_generate_grade_mastery():
    can = "JFまるごと:13"
    can_enc = quote(can, safe="")

    # 1) Activate lesson (compat route exists at /api/lessons/activate)
    r1 = _retry_get(f"{API}/api/lessons/activate?can_do_id={can_enc}")
    lesson = r1.json()
    assert isinstance(lesson, dict)
    assert lesson.get("meta") is not None or lesson.get("sections") is not None

    # 2) Generate minimal exercises
    r2 = requests.post(
        f"{API}/api/v1/lexical/lessons/generate-exercises?can_do_id={can_enc}&n=2",
        timeout=10,
    )
    assert r2.status_code == 200, r2.text
    ex = r2.json()
    assert ex.get("can_do_id") == can
    exercises = ex.get("exercises") or []
    assert isinstance(exercises, list) and len(exercises) >= 1

    # 3) Grade one exercise
    sample_ex = exercises[0]
    payload_grade = {"exercise": sample_ex, "answer": "きょうとに行きました。"}
    r3 = requests.post(
        f"{API}/api/v1/lexical/lessons/grade",
        headers={"Content-Type": "application/json"},
        data=json.dumps(payload_grade, ensure_ascii=False).encode("utf-8"),
        timeout=10,
    )
    assert r3.status_code == 200, r3.text
    gr = r3.json()
    assert 0.0 <= float(gr.get("score", 0.0)) <= 1.0

    # 4) Update mastery
    payload_mastery = {"user_id": "u-demo", "can_do_id": can, "score": float(gr.get("score", 0.6))}
    r4 = requests.post(
        f"{API}/api/v1/lexical/lessons/update-mastery",
        headers={"Content-Type": "application/json"},
        data=json.dumps(payload_mastery, ensure_ascii=False).encode("utf-8"),
        timeout=10,
    )
    assert r4.status_code == 200, r4.text
    um = r4.json()
    assert um.get("can_do_id") == can and um.get("user_id") == "u-demo"


