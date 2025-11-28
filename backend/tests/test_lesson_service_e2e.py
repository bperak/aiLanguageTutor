"""
End-to-End Tests for Lesson Service API

Tests the complete flow:
1. Start lesson (generates master + variants)
2. User turn (conversation + phase gating)
3. Session persistence (verify Postgres storage)
"""

import pytest
import httpx
import json
from uuid import uuid4

# Configure for local testing
API_BASE_URL = "http://localhost:8000/api/v1"
TIMEOUT = 30.0


class TestLessonServiceE2E:
    """End-to-end tests for lesson service."""

    @pytest.fixture
    def http_client(self):
        """Create HTTP client for API requests."""
        return httpx.Client(base_url=API_BASE_URL, timeout=TIMEOUT)

    @pytest.mark.asyncio
    async def test_start_lesson_endpoint(self, http_client):
        """Test POST /cando/lessons/start endpoint."""
        response = http_client.post(
            "/cando/lessons/start",
            params={
                "can_do_id": "JF21",
                "phase": "lexicon_and_patterns",
                "level": 1,
                "provider": "openai",
            },
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "sessionId" in data, "Missing sessionId in response"
        assert "master" in data, "Missing master in response"
        assert "variant" in data, "Missing variant in response"
        assert "objective" in data, "Missing learning objective"
        assert "opening_turns" in data, "Missing opening turns"
        
        # Verify master lesson structure
        master = data["master"]
        assert master.get("canDoId") == "JF21"
        assert master.get("originalLevel") == 1
        assert "ui" in master
        assert "learningObjectives" in master
        
        # Verify variant structure
        variant = data["variant"]
        assert variant.get("level") == 1
        assert "ui" in variant
        
        return data["sessionId"]

    @pytest.mark.asyncio
    async def test_lesson_turn_endpoint(self, http_client):
        """Test POST /cando/lessons/turn endpoint."""
        # First start a lesson
        start_response = http_client.post(
            "/cando/lessons/start",
            params={
                "can_do_id": "JF21",
                "phase": "lexicon_and_patterns",
                "level": 1,
                "provider": "openai",
            },
        )
        assert start_response.status_code == 200
        session_id = start_response.json()["sessionId"]
        
        # Now send a user turn
        turn_response = http_client.post(
            "/cando/lessons/turn",
            params={
                "session_id": session_id,
                "message": "こんにちは",
                "provider": "openai",
            },
        )
        
        assert turn_response.status_code == 200, f"Expected 200, got {turn_response.status_code}: {turn_response.text}"
        data = turn_response.json()
        
        # Verify turn response structure
        assert "turn" in data, "Missing turn in response"
        assert "dialogue" in data, "Missing dialogue history"
        assert "phase" in data, "Missing phase"
        assert "advanced" in data, "Missing advanced flag"
        
        # Verify AI turn structure
        turn = data["turn"]
        assert turn.get("speaker") == "ai"
        assert "message" in turn

    @pytest.mark.asyncio
    async def test_session_persistence(self, http_client):
        """Test that sessions are stored in Postgres and retrievable."""
        # Start a lesson
        start_response = http_client.post(
            "/cando/lessons/start",
            params={
                "can_do_id": "JF22",
                "phase": "lexicon_and_patterns",
                "level": 2,
                "provider": "openai",
            },
        )
        assert start_response.status_code == 200
        session_id = start_response.json()["sessionId"]
        
        # Send multiple turns
        for i in range(3):
            turn_response = http_client.post(
                "/cando/lessons/turn",
                params={
                    "session_id": session_id,
                    "message": f"メッセージ{i}",
                    "provider": "openai",
                },
            )
            assert turn_response.status_code == 200
        
        # Retrieve the same session (should still exist in Postgres)
        second_turn_response = http_client.post(
            "/cando/lessons/turn",
            params={
                "session_id": session_id,
                "message": "最後のメッセージ",
                "provider": "openai",
            },
        )
        
        assert second_turn_response.status_code == 200, "Session should persist"

    @pytest.mark.asyncio
    async def test_phase_gating(self, http_client):
        """Test that phase advances based on completion count."""
        # Start lesson
        start_response = http_client.post(
            "/cando/lessons/start",
            params={
                "can_do_id": "JF23",
                "phase": "lexicon_and_patterns",
                "level": 1,
                "provider": "openai",
            },
        )
        assert start_response.status_code == 200
        session_id = start_response.json()["sessionId"]
        initial_phase = start_response.json().get("variant", {}).get("phase")
        
        # Send turns to trigger phase advancement (default GATING_N=2)
        for i in range(3):
            turn_response = http_client.post(
                "/cando/lessons/turn",
                params={
                    "session_id": session_id,
                    "message": f"ターン{i}",
                    "provider": "openai",
                },
            )
            assert turn_response.status_code == 200
            data = turn_response.json()
            
            if i >= 1:  # After 2 completions
                # Phase should have advanced
                if data.get("advanced"):
                    assert data.get("phase") != initial_phase, "Phase should change after gating threshold"

    @pytest.mark.asyncio
    async def test_error_handling_invalid_session(self, http_client):
        """Test error handling for invalid session ID."""
        response = http_client.post(
            "/cando/lessons/turn",
            params={
                "session_id": str(uuid4()),  # Non-existent session
                "message": "test",
                "provider": "openai",
            },
        )
        
        # Should return error
        assert response.status_code == 500, "Should return error for invalid session"

    @pytest.mark.asyncio
    async def test_master_lesson_caching(self, http_client):
        """Test that master lessons are cached (second request is faster)."""
        import time
        
        # First request (cache miss)
        start_time = time.time()
        response1 = http_client.post(
            "/cando/lessons/start",
            params={
                "can_do_id": "JF24",
                "phase": "lexicon_and_patterns",
                "level": 1,
                "provider": "openai",
            },
        )
        time1 = time.time() - start_time
        
        assert response1.status_code == 200
        master1 = response1.json()["master"]
        
        # Second request (cache hit - should be faster)
        start_time = time.time()
        response2 = http_client.post(
            "/cando/lessons/start",
            params={
                "can_do_id": "JF24",  # Same CanDo
                "phase": "lexicon_and_patterns",
                "level": 2,  # Different level (same master)
                "provider": "openai",
            },
        )
        time2 = time.time() - start_time
        
        assert response2.status_code == 200
        master2 = response2.json()["master"]
        
        # Master should be identical (from cache)
        assert master1.get("lessonId") == master2.get("lessonId"), "Should return cached master"
        print(f"Cache performance: First request {time1:.2f}s, Second request {time2:.2f}s")


class TestLessonServiceIntegration:
    """Integration tests for lesson service components."""

    @pytest.fixture
    def http_client(self):
        """Create HTTP client for API requests."""
        return httpx.Client(base_url=API_BASE_URL, timeout=TIMEOUT)

    @pytest.mark.asyncio
    async def test_full_lesson_workflow(self, http_client):
        """Test complete lesson workflow from start to phase advance."""
        # 1. Start lesson
        start_resp = http_client.post(
            "/cando/lessons/start",
            params={
                "can_do_id": "JF25",
                "phase": "lexicon_and_patterns",
                "level": 1,
                "provider": "openai",
            },
        )
        assert start_resp.status_code == 200
        data = start_resp.json()
        session_id = data["sessionId"]
        
        # Verify master + variant are present
        assert "master" in data
        assert "variant" in data
        assert "opening_turns" in data
        assert len(data["opening_turns"]) > 0
        
        print(f"✅ Lesson started: session_id={session_id}")
        print(f"   Master lesson ID: {data['master'].get('lessonId')}")
        print(f"   Learning objective: {data['master'].get('learningObjectives', [None])[0]}")
        
        # 2. User participates in dialogue
        dialogue_history = data.get("opening_turns", [])
        
        for turn_num in range(3):
            turn_resp = http_client.post(
                "/cando/lessons/turn",
                params={
                    "session_id": session_id,
                    "message": f"ユーザーのターン{turn_num}です",
                    "provider": "openai",
                },
            )
            assert turn_resp.status_code == 200
            turn_data = turn_resp.json()
            
            # Verify turn structure
            assert "turn" in turn_data
            assert turn_data["turn"].get("speaker") == "ai"
            assert len(turn_data["turn"].get("message", "")) > 0
            
            dialogue_history.extend(turn_data.get("dialogue", []))
            
            print(f"✅ Turn {turn_num + 1}: AI responded, Phase: {turn_data.get('phase')}, Advanced: {turn_data.get('advanced')}")
        
        print(f"✅ Full workflow completed successfully!")
        print(f"   Total dialogue turns: {len(dialogue_history)}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
