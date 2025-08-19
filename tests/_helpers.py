import time
from typing import Any, Dict, Optional

import requests


def post_with_retry(url: str, json: Optional[Dict[str, Any]] = None, timeout: int = 15, tries: int = 5, delay: float = 0.8) -> requests.Response:
    last_exc: Optional[Exception] = None
    for _ in range(tries):
        try:
            return requests.post(url, json=json, timeout=timeout)
        except Exception as exc:  # Connection errors, timeouts, etc.
            last_exc = exc
            time.sleep(delay)
    if last_exc:
        raise last_exc
    raise RuntimeError("post_with_retry failed without exception")


def get_with_retry(url: str, headers: Optional[Dict[str, str]] = None, timeout: int = 15, tries: int = 5, delay: float = 0.8) -> requests.Response:
    last_exc: Optional[Exception] = None
    for _ in range(tries):
        try:
            return requests.get(url, headers=headers, timeout=timeout)
        except Exception as exc:
            last_exc = exc
            time.sleep(delay)
    if last_exc:
        raise last_exc
    raise RuntimeError("get_with_retry failed without exception")


def request_with_retry(method: str, url: str, *, tries: int = 5, delay: float = 0.8, timeout: int = 15, **kwargs: Any) -> requests.Response:
    last_exc: Optional(Exception) = None
    for _ in range(tries):
        try:
            return requests.request(method, url, timeout=timeout, **kwargs)
        except Exception as exc:
            last_exc = exc
            time.sleep(delay)
    if last_exc:
        raise last_exc
    raise RuntimeError("request_with_retry failed without exception")


def wait_for_health(base_url: str, timeout_seconds: int = 45) -> None:
    import time
    deadline = time.time() + timeout_seconds
    last_exc: Optional[Exception] = None
    while time.time() < deadline:
        try:
            r = requests.get(f"{base_url}/health", timeout=5)
            if r.status_code == 200:
                return
        except Exception as exc:
            last_exc = exc
        time.sleep(1.0)
    if last_exc:
        raise last_exc
    raise TimeoutError("Backend health did not become 200 in time")


