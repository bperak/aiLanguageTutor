import pytest
from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


@pytest.mark.anyio
async def test_compile_then_pdf_roundtrip():
    can_do_id = "TEST:COMPILE:1"

    # Compile master lesson (idempotent)
    r1 = client.post(f"/api/v1/cando/lessons/compile?can_do_id={can_do_id}&version=1&provider=openai")
    assert r1.status_code == 200
    data = r1.json()
    assert data.get("status") == "ok"

    # Fetch PDF
    r2 = client.get(f"/api/v1/cando/lessons/pdf?can_do_id={can_do_id}&version=1")
    assert r2.status_code == 200
    assert r2.headers.get("content-type", "").startswith("application/pdf")




