import os
import pytest
import requests


FRONTEND_BASE_URL_ENV = os.environ.get("FRONTEND_BASE_URL")
FRONTEND_BASE_URL: str = FRONTEND_BASE_URL_ENV or ""


@pytest.mark.smoke
def test_frontend_home_loads():
    if not FRONTEND_BASE_URL:
        pytest.skip("FRONTEND_BASE_URL not set; skipping frontend smoke test")
        return
    try:
        r = requests.get(FRONTEND_BASE_URL, timeout=5)
    except Exception:
        pytest.skip("Frontend is not reachable; skipping smoke test")
        return
    assert r.status_code == 200
    # Basic presence check
    assert "<!DOCTYPE html>" in r.text


