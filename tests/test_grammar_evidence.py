"""
Tests for grammar evidence tracking endpoints.
"""

import pytest
from datetime import datetime, date, timedelta
from uuid import uuid4

from app.models.database_models import User, ConversationSession, ConversationMessage, ConversationInteraction


@pytest.mark.asyncio
async def test_record_grammar_evidence_success(client, test_user, auth_headers, db_session):
    """Test successful evidence recording"""
    pattern_id = "test_pattern_001"
    
    response = await client.post(
        "/api/v1/grammar/evidence/record",
        json={
            "pattern_id": pattern_id,
            "stage": "comprehension",
            "interaction_type": "grammar_practiced",
            "is_correct": True,
            "user_response": "私は学生です",
            "attempts_count": 1,
            "hint_used": False,
            "response_time_seconds": 5,
            "confidence_self_reported": 4,
            "rubric_scores": {
                "pattern_used": True,
                "form_accurate": True,
                "meaning_matches": True
            },
            "error_tags": [],
            "stage_specific_data": {
                "question_type": "multiple_choice",
                "difficulty": "basic"
            }
        },
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["pattern_id"] == pattern_id
    assert data["stage"] == "comprehension"
    assert data["mastery_level"] >= 1
    assert "interaction_id" in data


@pytest.mark.asyncio
async def test_record_grammar_evidence_unauthorized(client):
    """Test evidence recording without authentication"""
    response = await client.post(
        "/api/v1/grammar/evidence/record",
        json={
            "pattern_id": "test_pattern_001",
            "stage": "comprehension",
            "interaction_type": "grammar_practiced"
        }
    )
    
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_evidence_summary_success(client, test_user, auth_headers, db_session):
    """Test successful evidence summary retrieval"""
    pattern_id = "test_pattern_001"
    
    # First record some evidence
    await client.post(
        "/api/v1/grammar/evidence/record",
        json={
            "pattern_id": pattern_id,
            "stage": "comprehension",
            "interaction_type": "grammar_practiced",
            "is_correct": True,
            "user_response": "私は学生です"
        },
        headers=auth_headers
    )
    
    # Then get summary
    response = await client.get(
        f"/api/v1/grammar/evidence/summary?pattern_id={pattern_id}",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["pattern_id"] == pattern_id
    assert data["total_attempts"] >= 1
    assert "attempts_by_stage" in data
    assert "correct_rate" in data
    assert "mastery_level" in data


@pytest.mark.asyncio
async def test_get_evidence_summary_no_evidence(client, test_user, auth_headers):
    """Test evidence summary for pattern with no evidence"""
    pattern_id = "nonexistent_pattern"
    
    response = await client.get(
        f"/api/v1/grammar/evidence/summary?pattern_id={pattern_id}",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["pattern_id"] == pattern_id
    assert data["total_attempts"] == 0
    assert data["correct_rate"] == 0.0
    assert data["mastery_level"] == 1


@pytest.mark.asyncio
async def test_get_evidence_summary_unauthorized(client):
    """Test evidence summary without authentication"""
    response = await client.get(
        "/api/v1/grammar/evidence/summary?pattern_id=test_pattern_001"
    )
    
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_record_evidence_multiple_stages(client, test_user, auth_headers, db_session):
    """Test recording evidence across different stages"""
    pattern_id = "test_pattern_002"
    
    stages = ["presentation", "comprehension", "production", "interaction"]
    
    for stage in stages:
        response = await client.post(
            "/api/v1/grammar/evidence/record",
            json={
                "pattern_id": pattern_id,
                "stage": stage,
                "interaction_type": "grammar_practiced",
                "is_correct": True,
                "user_response": f"Test response for {stage}"
            },
            headers=auth_headers
        )
        assert response.status_code == 200
    
    # Check summary includes all stages
    response = await client.get(
        f"/api/v1/grammar/evidence/summary?pattern_id={pattern_id}",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["total_attempts"] == len(stages)
    assert len(data["attempts_by_stage"]) == len(stages)
    for stage in stages:
        assert stage in data["attempts_by_stage"]


@pytest.mark.asyncio
async def test_evidence_rubric_scores(client, test_user, auth_headers, db_session):
    """Test evidence recording with rubric scores"""
    pattern_id = "test_pattern_003"
    
    response = await client.post(
        "/api/v1/grammar/evidence/record",
        json={
            "pattern_id": pattern_id,
            "stage": "production",
            "interaction_type": "grammar_practiced",
            "is_correct": False,
            "user_response": "私は学生",
            "rubric_scores": {
                "pattern_used": True,
                "form_accurate": False,
                "meaning_matches": True
            },
            "error_tags": ["form_accuracy"]
        },
        headers=auth_headers
    )
    
    assert response.status_code == 200
    # Verify the evidence was stored with rubric scores
    # (This would require querying the DB directly in a real test)

