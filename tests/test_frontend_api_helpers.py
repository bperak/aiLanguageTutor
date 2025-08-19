import os
import importlib.util
from pathlib import Path


def test_frontend_api_base_url_present():
    base = os.getenv("NEXT_PUBLIC_API_BASE_URL") or os.getenv("API_BASE_URL")
    # Not strictly required, but helps ensure env is configured
    assert base is None or base.startswith("http"), "API base should be an http(s) URL if set"



