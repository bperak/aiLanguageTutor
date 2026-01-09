"""
Tests for session creation endpoint fallback behavior

Covers:
- Failure case: DB missing lesson_sessions table → session/create still returns a session id (fallback path)
- Expected use: normal session creation works
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from sqlalchemy.exc import ProgrammingError


@pytest.mark.asyncio
async def test_session_create_fallback_on_missing_table():
    """Test that session creation falls back to in-memory when DB table is missing."""
    from app.api.v1.endpoints.cando import create_lesson_session, CreateLessonSessionRequest
    from app.db import get_postgresql_session
    from sqlalchemy.ext.asyncio import AsyncSession
    
    request = CreateLessonSessionRequest(can_do_id="JF:21")
    
    # Mock Postgres session that raises error on query (table missing)
    mock_pg = AsyncMock(spec=AsyncSession)
    mock_pg.execute.side_effect = ProgrammingError(
        "relation \"lesson_sessions\" does not exist",
        None,
        None
    )
    
    # Call the endpoint
    result = await create_lesson_session(request, pg=mock_pg)
    
    # Should still return a session_id (from in-memory fallback)
    assert "session_id" in result
    assert result["session_id"] is not None
    assert len(result["session_id"]) > 0  # Should be a UUID string


@pytest.mark.asyncio
async def test_session_create_normal_flow():
    """Test that normal session creation works when DB is available."""
    from app.api.v1.endpoints.cando import create_lesson_session, CreateLessonSessionRequest
    from app.db import get_postgresql_session
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy import text
    
    request = CreateLessonSessionRequest(can_do_id="JF:21")
    
    # Mock Postgres session with successful query (no existing session)
    mock_pg = AsyncMock(spec=AsyncSession)
    mock_result = MagicMock()
    mock_result.fetchone.return_value = None  # No existing session
    mock_pg.execute.return_value = mock_result
    
    # Mock the service's _store_session to succeed
    with patch("app.api.v1.endpoints.cando.cando_lesson_sessions._store_session", new_callable=AsyncMock) as mock_store:
        mock_store.return_value = None  # Success
        
        result = await create_lesson_session(request, pg=mock_pg)
        
        # Should return a session_id
        assert "session_id" in result
        assert result["session_id"] is not None
        
        # Should have called store_session
        mock_store.assert_called_once()


@pytest.mark.asyncio
async def test_session_create_existing_session():
    """Test that existing session is returned if found."""
    from app.api.v1.endpoints.cando import create_lesson_session, CreateLessonSessionRequest
    from app.db import get_postgresql_session
    from sqlalchemy.ext.asyncio import AsyncSession
    import uuid
    
    request = CreateLessonSessionRequest(can_do_id="JF:21")
    existing_session_id = str(uuid.uuid4())
    
    # Mock Postgres session with existing session
    mock_pg = AsyncMock(spec=AsyncSession)
    mock_result = MagicMock()
    mock_result.fetchone.return_value = (existing_session_id,)  # Existing session found
    mock_pg.execute.return_value = mock_result
    
    result = await create_lesson_session(request, pg=mock_pg)
    
    # Should return the existing session_id
    assert "session_id" in result
    assert result["session_id"] == existing_session_id


@pytest.mark.asyncio
async def test_session_create_final_fallback():
    """Test that final in-memory fallback works if everything fails."""
    from app.api.v1.endpoints.cando import create_lesson_session, CreateLessonSessionRequest
    from app.db import get_postgresql_session
    from sqlalchemy.ext.asyncio import AsyncSession
    
    request = CreateLessonSessionRequest(can_do_id="JF:21")
    
    # Mock Postgres session that fails
    mock_pg = AsyncMock(spec=AsyncSession)
    mock_pg.execute.side_effect = Exception("Database completely unavailable")
    
    # Mock service's _store_session to also fail
    with patch("app.api.v1.endpoints.cando.cando_lesson_sessions._store_session", new_callable=AsyncMock) as mock_store:
        mock_store.side_effect = Exception("Storage failed")
        
        result = await create_lesson_session(request, pg=mock_pg)
        
        # Should still return a session_id from final fallback
        assert "session_id" in result
        assert result["session_id"] is not None
        assert len(result["session_id"]) > 0

