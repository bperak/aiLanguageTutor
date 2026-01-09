"""
Unit tests for lexical graph endpoint resilience.

These tests do NOT require a seeded Neo4j instance.
They mock the Neo4j session dependency to force transient failures and assert
that the API returns retryable 503s (instead of 500s).
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient
from neo4j.exceptions import ServiceUnavailable

from app.db import get_neo4j_session
from app.main import app


class _FailingNeo4jSession:
    async def run(self, *args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
        raise ServiceUnavailable("neo4j down")


def _override_neo4j_session():  # type: ignore[no-untyped-def]
    async def _gen():
        yield _FailingNeo4jSession()

    return _gen


def test_lexical_graph_returns_503_when_neo4j_unavailable() -> None:
    """
    Expected use: transient Neo4j outage should yield 503 (retryable).
    """
    app.dependency_overrides[get_neo4j_session] = _override_neo4j_session()
    try:
        client = TestClient(app)
        r = client.get("/api/v1/lexical/graph?center=水&depth=1&searchField=kanji")
        assert r.status_code == 503
    finally:
        app.dependency_overrides.pop(get_neo4j_session, None)


def test_lexical_node_returns_503_when_neo4j_unavailable() -> None:
    """
    Failure case: node-details should not leak a 500 when Neo4j is down.
    """
    app.dependency_overrides[get_neo4j_session] = _override_neo4j_session()
    try:
        client = TestClient(app)
        r = client.get("/api/v1/lexical/node/水")
        assert r.status_code == 503
    finally:
        app.dependency_overrides.pop(get_neo4j_session, None)


def test_lexical_graph_empty_center_is_200() -> None:
    """
    Edge case: empty center should be handled gracefully (no Neo4j call needed).
    """
    client = TestClient(app)
    r = client.get("/api/v1/lexical/graph?center=&depth=1&searchField=kanji")
    assert r.status_code == 200
    body = r.json()
    assert body["nodes"] == []
    assert body["links"] == []


