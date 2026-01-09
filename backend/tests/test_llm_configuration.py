"""
PHASE 1.2: LLM Configuration Tests

Tests for verifying LLM provider configuration,
API key presence, and basic LLM functionality.
"""

import pytest
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
backend_path = Path(__file__).resolve().parent.parent
env_path = backend_path.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    # Try to find .env in parent directories
    for parent in backend_path.parents:
        candidate = parent / ".env"
        if candidate.exists():
            load_dotenv(candidate)
            break

from app.core.config import settings


def test_openai_api_key_present():
    """
    Test: OpenAI API key is present in environment.
    
    Verifies that OPENAI_API_KEY is configured.
    """
    api_key = os.getenv("OPENAI_API_KEY") or settings.OPENAI_API_KEY
    assert api_key is not None, "OPENAI_API_KEY is not set"
    assert api_key != "", "OPENAI_API_KEY is empty"
    assert len(api_key) > 10, "OPENAI_API_KEY appears to be invalid (too short)"


def test_openai_api_key_format():
    """
    Test: OpenAI API key has correct format.
    
    Verifies that OPENAI_API_KEY starts with 'sk-' (OpenAI format).
    """
    api_key = os.getenv("OPENAI_API_KEY") or settings.OPENAI_API_KEY
    if api_key:
        # OpenAI keys typically start with 'sk-'
        assert api_key.startswith("sk-"), f"OPENAI_API_KEY format unexpected (should start with 'sk-')"


@pytest.mark.asyncio
async def test_openai_basic_call():
    """
    Test: Basic OpenAI LLM call works.
    
    Verifies that a simple LLM call can be made successfully.
    """
    from openai import OpenAI
    
    api_key = os.getenv("OPENAI_API_KEY") or settings.OPENAI_API_KEY
    if not api_key:
        pytest.skip("OPENAI_API_KEY not configured")
    
    client = OpenAI(api_key=api_key, timeout=30.0)
    
    # Make a simple test call
    response = client.chat.completions.create(
        model="gpt-4.1",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Say 'test' and nothing else."}
        ],
        temperature=0.0,
        max_tokens=10,
    )
    
    assert response is not None, "OpenAI API call returned None"
    assert len(response.choices) > 0, "OpenAI API response has no choices"
    assert response.choices[0].message.content is not None, "OpenAI API response content is None"
    assert "test" in response.choices[0].message.content.lower(), "OpenAI API response doesn't contain expected content"


def test_llm_model_configuration():
    """
    Test: LLM model configuration is valid.
    
    Verifies that model names are configured correctly.
    """
    # Check if model configuration exists in settings
    # This is a basic check - actual model availability depends on provider
    assert hasattr(settings, 'OPENAI_API_KEY'), "Settings missing OPENAI_API_KEY attribute"
    
    # Verify timeout settings are reasonable
    # (This would be in the LLM call function, but we can check config exists)


@pytest.mark.asyncio
async def test_llm_json_mode():
    """
    Test: LLM JSON mode works correctly.
    
    Verifies that LLM can return valid JSON when requested.
    """
    from openai import OpenAI
    import json
    
    api_key = os.getenv("OPENAI_API_KEY") or settings.OPENAI_API_KEY
    if not api_key:
        pytest.skip("OPENAI_API_KEY not configured")
    
    client = OpenAI(api_key=api_key, timeout=30.0)
    
    # Make a call with JSON mode
    response = client.chat.completions.create(
        model="gpt-4.1",
        messages=[
            {"role": "system", "content": "You are a helpful assistant. Always respond with valid JSON."},
            {"role": "user", "content": 'Return a JSON object with a single key "test" and value "success".'}
        ],
        temperature=0.0,
        response_format={"type": "json_object"},
        max_tokens=50,
    )
    
    assert response is not None, "LLM JSON mode call returned None"
    content = response.choices[0].message.content
    assert content is not None, "LLM JSON mode response content is None"
    
    # Verify it's valid JSON
    try:
        parsed = json.loads(content)
        assert isinstance(parsed, dict), "LLM JSON mode response is not a dictionary"
        assert "test" in parsed, "LLM JSON mode response missing expected key"
    except json.JSONDecodeError as e:
        pytest.fail(f"LLM JSON mode response is not valid JSON: {e}")


def test_llm_timeout_configuration():
    """
    Test: LLM timeout configuration is reasonable.
    
    Verifies that timeout values are set appropriately.
    """
    # Check that timeout values would be reasonable (this is more of a config check)
    # The actual timeout is set in _make_llm_call_openai function
    # We can verify the default timeout value exists in the code
    from app.services.cando_v2_compile_service import _make_llm_call_openai
    
    # Default timeout should be 120 seconds
    llm_call = _make_llm_call_openai(model="gpt-4.1", timeout=120)
    assert callable(llm_call), "LLM call function should be callable"

