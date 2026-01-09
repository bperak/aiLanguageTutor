"""
Tests for lexical endpoints
"""
import pytest

# Requires seeded graph data; skip by default.
pytestmark = pytest.mark.integration
from fastapi.testclient import TestClient
from app.main import app
from app.api.v1.endpoints.lexical import _sanitize_graph_response

client = TestClient(app)


def test_get_lexical_graph():
    """Test the lexical graph endpoint"""
    response = client.get("/api/v1/lexical/graph?center=日本&depth=1")
    assert response.status_code == 200
    data = response.json()
    assert "nodes" in data
    assert "links" in data
    assert "center" in data
    assert isinstance(data["nodes"], list)
    assert isinstance(data["links"], list)


def test_get_node_details():
    """Test the node details endpoint"""
    response = client.get("/api/v1/lexical/node/日本")
    assert response.status_code == 200
    data = response.json()
    assert "node" in data
    assert "neighbors" in data
    assert "total_connections" in data
    assert isinstance(data["neighbors"], list)


def test_get_lexical_graph_invalid_center():
    """Test graph endpoint with invalid center word"""
    response = client.get("/api/v1/lexical/graph?center=INVALID_WORD&depth=1")
    assert response.status_code == 404


def test_get_node_details_invalid_word():
    """Test node details endpoint with invalid word"""
    response = client.get("/api/v1/lexical/node/INVALID_WORD")
    assert response.status_code == 404


def test_sanitize_graph_response_filters_invalid_links():
    nodes = [
        {"id": "A"},
        {"id": "B"},
        {"id": ""},  # invalid
        {"id": "A"},  # duplicate
    ]
    links = [
        {"source": "A", "target": "B", "weight": 2},  # valid
        {"source": "A", "target": "C"},  # invalid: target not in nodes
        {"source": "", "target": "B"},   # invalid: empty source
        {"source": "A", "target": "A"},  # invalid: self-loop
        {"source": None, "target": None},   # invalid: nulls
    ]

    sanitized = _sanitize_graph_response(nodes, links)
    assert set(n["id"] for n in sanitized["nodes"]) == {"A", "B"}
    assert len(sanitized["links"]) == 1
    assert sanitized["links"][0]["source"] == "A"
    assert sanitized["links"][0]["target"] == "B"


def test_ego_graph_depth_parameter_effect():
    """Depth=2 should include >= nodes/links compared to depth=1 (when available)."""
    r1 = client.get("/api/v1/lexical/graph?center=日本&depth=1")
    r2 = client.get("/api/v1/lexical/graph?center=日本&depth=2")
    assert r1.status_code == 200
    assert r2.status_code == 200
    g1 = r1.json()
    g2 = r2.json()
    assert isinstance(g1.get("nodes", []), list)
    assert isinstance(g1.get("links", []), list)
    assert isinstance(g2.get("nodes", []), list)
    assert isinstance(g2.get("links", []), list)
    # Not strictly guaranteed, but generally depth=2 expands or equals
    assert len(g2["nodes"]) >= len(g1["nodes"])  # noqa: PLR2004
    assert len(g2["links"]) >= len(g1["links"])  # noqa: PLR2004
