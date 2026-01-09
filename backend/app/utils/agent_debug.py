"""
Minimal NDJSON debug logging for Cursor DEBUG MODE.

This module sends small JSON payloads to the provisioned ingest endpoint.
It intentionally avoids secrets/PII and never raises (best-effort).
"""

from __future__ import annotations

import json
import time
import urllib.request
from typing import Any, Dict, Optional


_LOG_PATH = "/home/benedikt/.cursor/debug.log"
_DEFAULT_ENDPOINTS = [
    # Prefer explicit override (useful outside Docker too).
    None,
    # Fallback for non-container execution (host ingest).
    "http://127.0.0.1:7244/ingest/94f31c73-1922-4afb-bace-ef57ea878c05",
]


def agent_debug_log(
    *,
    hypothesisId: str,
    location: str,
    message: str,
    data: Optional[Dict[str, Any]] = None,
    sessionId: str = "debug-session",
    runId: str = "run4",
) -> None:
    """
    Emit a small NDJSON-compatible payload to the DEBUG MODE ingest endpoint.

    Args:
        hypothesisId (str): Hypothesis identifier (A/B/C/...) to map logs to ideas.
        location (str): File:line style marker.
        message (str): Short, stable message key.
        data (dict | None): Small structured data (no secrets/PII).
        sessionId (str): Debug session ID.
        runId (str): Run ID to separate pre-fix/post-fix.
    """
    payload = {
        "timestamp": int(time.time() * 1000),
        "sessionId": sessionId,
        "runId": runId,
        "hypothesisId": hypothesisId,
        "location": location,
        "message": message,
        "data": data or {},
    }

    # Prefer direct NDJSON append (Debug Mode requirement). This works because docker-compose
    # mounts /home/benedikt/.cursor into the backend container.
    try:
        with open(_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:
        pass

    try:
        endpoint_override = None
        try:
            endpoint_override = __import__("os").getenv("DEBUG_INGEST_ENDPOINT")
        except Exception:
            endpoint_override = None

        endpoints = [endpoint_override] + [e for e in _DEFAULT_ENDPOINTS if e]
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")

        for endpoint in endpoints:
            if not endpoint:
                continue
            try:
                req = urllib.request.Request(
                    endpoint,
                    data=body,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                urllib.request.urlopen(req, timeout=1.0).read()
                break
            except Exception:
                continue
    except Exception:
        # Best-effort only; never impact runtime.
        pass


