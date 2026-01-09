"""
Tests for CanDo lesson evidence tracking endpoints.
"""

import pytest
from datetime import datetime, date, timedelta
from uuid import uuid4
from unittest.mock import AsyncMock, patch, MagicMock

from app.api.v1.endpoints.cando import (
    record_cando_evidence,
    get_cando_evidence_summary,
    CanDoEvidenceRecordRequest,
)
from app.models.database_models import User, ConversationSession, ConversationMessage, ConversationInteraction


@pytest.fixture
def mock_user():
    user = User()
    user.id = uuid4()
    user.email = "test@example.com"
    user.username = "testuser"
    return user


@pytest.fixture
def sample_evidence_request():
    return CanDoEvidenceRecordRequest(
        can_do_id="JF21",
        stage="comprehension",
        interaction_type="cando_practiced",
        is_correct=True,
        user_response="こんにちは",
        attempts_count=1,
        hint_used=False,
        response_time_seconds=5,
        confidence_self_reported=4,
        rubric_scores={"pattern_used": True, "form_accurate": True, "meaning_matches": True},
        error_tags=[],
        stage_specific_data={"task_type": "meaning_discrimination"}
    )


@pytest.mark.asyncio
async def test_record_cando_evidence_new_session(mock_user, sample_evidence_request):
    """Test recording evidence creates new session if none exists."""
    mock_pg = AsyncMock()

    # Mock execute call sequence:
    # 1) session_query -> scalar_one_or_none() == None (no existing session)
    # 2) max_order_query -> scalar() == 0 (no previous messages)
    # 3) existing_query -> scalar_one_or_none() == None (no prior interaction)
    exec1 = MagicMock()
    exec1.scalar_one_or_none.return_value = None
    exec2 = MagicMock()
    exec2.scalar.return_value = 0
    exec3 = MagicMock()
    exec3.scalar_one_or_none.return_value = None
    mock_pg.execute = AsyncMock(side_effect=[exec1, exec2, exec3])

    # Track added objects so we can simulate flush assigning IDs
    added = []
    def _add(obj):
        added.append(obj)
    mock_pg.add = MagicMock(side_effect=_add)

    async def _flush():
        # Assign IDs to any newly added ORM objects that need them
        for obj in added:
            if getattr(obj, "id", None) is None:
                obj.id = uuid4()
        return None
    mock_pg.flush = AsyncMock(side_effect=_flush)
    mock_pg.commit = AsyncMock()

    response = await record_cando_evidence(
        can_do_id="JF21",
        evidence=sample_evidence_request,
        pg=mock_pg,
        current_user=mock_user
    )
    
    assert response.can_do_id == "JF21"
    assert response.stage == "comprehension"
    assert response.mastery_level >= 1
    assert response.interaction_id  # should be populated via flush()
    assert mock_pg.add.called
    assert mock_pg.commit.called


@pytest.mark.asyncio
async def test_record_cando_evidence_existing_session(mock_user, sample_evidence_request):
    """Test recording evidence uses existing session."""
    mock_pg = AsyncMock()
    
    # Mock existing session
    existing_session = ConversationSession()
    existing_session.id = uuid4()

    # execute sequence:
    # 1) session_query -> existing_session
    # 2) max_order_query -> scalar() == 1
    # 3) existing_query -> None
    exec1 = MagicMock()
    exec1.scalar_one_or_none.return_value = existing_session
    exec2 = MagicMock()
    exec2.scalar.return_value = 1
    exec3 = MagicMock()
    exec3.scalar_one_or_none.return_value = None
    mock_pg.execute = AsyncMock(side_effect=[exec1, exec2, exec3])

    added = []
    mock_pg.add = MagicMock(side_effect=lambda obj: added.append(obj))

    async def _flush():
        for obj in added:
            if getattr(obj, "id", None) is None:
                obj.id = uuid4()
        return None
    mock_pg.flush = AsyncMock(side_effect=_flush)
    mock_pg.commit = AsyncMock()

    response = await record_cando_evidence(
        can_do_id="JF21",
        evidence=sample_evidence_request,
        pg=mock_pg,
        current_user=mock_user
    )
    
    assert response.can_do_id == "JF21"
    assert response.interaction_id
    assert mock_pg.add.called


@pytest.mark.asyncio
async def test_get_cando_evidence_summary_no_evidence(mock_user):
    """Test evidence summary returns empty when no evidence exists."""
    mock_pg = AsyncMock()
    mock_neo4j = AsyncMock()
    
    # Mock Neo4j query - need to properly mock the async chain
    mock_record = MagicMock()
    mock_record.get = MagicMock(side_effect=lambda k: {
        "title_en": "Test CanDo",
        "title_ja": None,
        "topic": None
    }.get(k))
    mock_neo4j_result = AsyncMock()
    mock_neo4j_result.single = AsyncMock(return_value=mock_record)
    mock_neo4j.run = AsyncMock(return_value=mock_neo4j_result)
    
    # Mock empty interactions query
    mock_pg_result = MagicMock()
    mock_pg_result.scalars.return_value.all.return_value = []
    mock_pg.execute = AsyncMock(return_value=mock_pg_result)
    
    response = await get_cando_evidence_summary(
        can_do_id="JF21",
        limit=10,
        pg=mock_pg,
        neo4j_session=mock_neo4j,
        current_user=mock_user
    )
    
    assert response.can_do_id == "JF21"
    assert response.total_attempts == 0
    assert response.attempts_by_stage == {}
    assert response.correct_rate == 0.0
    assert response.mastery_level == 1


@pytest.mark.asyncio
async def test_get_cando_evidence_summary_with_evidence(mock_user):
    """Test evidence summary aggregates correctly."""
    mock_pg = AsyncMock()
    mock_neo4j = AsyncMock()
    
    # Mock Neo4j query - need to properly mock the async chain
    mock_record = MagicMock()
    mock_record.get = MagicMock(side_effect=lambda k: {
        "title_en": "Test CanDo",
        "title_ja": None,
        "topic": None
    }.get(k))
    mock_neo4j_result = AsyncMock()
    mock_neo4j_result.single = AsyncMock(return_value=mock_record)
    mock_neo4j.run = AsyncMock(return_value=mock_neo4j_result)
    
    # Mock interactions
    interaction1 = ConversationInteraction()
    interaction1.is_correct = True
    interaction1.mastery_level = 3
    interaction1.created_at = datetime.utcnow()
    interaction1.next_review_date = date.today() + timedelta(days=3)
    interaction1.user_response = "こんにちは"
    interaction1.evidence_metadata = {"stage": "comprehension", "error_tags": []}
    
    interaction2 = ConversationInteraction()
    interaction2.is_correct = False
    interaction2.mastery_level = 2
    interaction2.created_at = datetime.utcnow() - timedelta(days=1)
    interaction2.next_review_date = date.today() + timedelta(days=1)
    interaction2.user_response = "こんばんは"
    interaction2.evidence_metadata = {"stage": "production", "error_tags": ["form_error"]}
    
    mock_pg_result = MagicMock()
    mock_pg_result.scalars.return_value.all.return_value = [interaction1, interaction2]
    mock_pg.execute = AsyncMock(return_value=mock_pg_result)
    
    response = await get_cando_evidence_summary(
        can_do_id="JF21",
        limit=10,
        pg=mock_pg,
        neo4j_session=mock_neo4j,
        current_user=mock_user
    )
    
    assert response.can_do_id == "JF21"
    assert response.total_attempts == 2
    assert response.correct_rate == 0.5
    assert response.mastery_level == 3  # Most recent
    assert "comprehension" in response.attempts_by_stage
    assert "production" in response.attempts_by_stage
    assert len(response.common_error_tags) > 0


@pytest.mark.asyncio
async def test_record_cando_evidence_can_do_id_mismatch(mock_user, sample_evidence_request):
    """Test that can_do_id mismatch raises error."""
    mock_pg = AsyncMock()
    
    with pytest.raises(Exception):  # HTTPException
        await record_cando_evidence(
            can_do_id="JF22",  # Different from request
            evidence=sample_evidence_request,  # Has JF21
            pg=mock_pg,
            current_user=mock_user
        )

