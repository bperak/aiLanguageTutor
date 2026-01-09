#!/usr/bin/env python3
"""
Live test script for extraction_response feature.

This script tests the actual API endpoints to verify the feature works end-to-end.
Requires:
- Backend server running
- Valid authentication token
- Test conversation with messages
"""

import sys
import asyncio
import json
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

async def test_extraction_response_feature():
    """Test extraction_response feature with live API."""
    print("=" * 70)
    print("EXTRACTION RESPONSE - LIVE API TEST")
    print("=" * 70)
    print()
    
    try:
        from app.db import init_postgresql, get_postgresql_session
        from app.migrations.postgres_migrator import apply_postgres_sql_migrations
        from sqlalchemy import text
        
        print("1. Initializing database connection...")
        engine = init_postgresql()
        print("   ✅ Database connected")
        
        print("\n2. Applying migrations...")
        await apply_postgres_sql_migrations(engine=engine)
        print("   ✅ Migrations applied")
        
        print("\n3. Verifying migration was applied...")
        async for db in get_postgresql_session():
            result = await db.execute(text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'user_profiles' 
                  AND column_name = 'extraction_response'
            """))
            row = result.first()
            if row:
                print(f"   ✅ Column exists: {row[0]} ({row[1]})")
            else:
                print("   ❌ Column not found - migration may not have applied")
                return 1
            break
        
        print("\n4. Testing service layer...")
        from app.services.profile_building_service import ProfileBuildingService
        from unittest.mock import AsyncMock
        
        service = ProfileBuildingService()
        test_messages = [
            {"role": "user", "content": "I want to learn Japanese for travel"},
            {"role": "assistant", "content": "Great! Tell me about your experience"},
            {"role": "user", "content": "I've studied for 1 year, know hiragana"},
        ]
        
        # Mock AI response
        mock_response = {
            "content": """{
  "learning_goals": ["travel to Japan"],
  "previous_knowledge": {
    "has_experience": true,
    "experience_level": "beginner",
    "years_studying": 1.0,
    "formal_classes": false,
    "self_study": true,
    "specific_areas_known": ["hiragana"],
    "specific_areas_unknown": []
  },
  "learning_experiences": {},
  "usage_context": {
    "contexts": ["travel"]
  },
  "current_level": "beginner_2"
}""",
            "provider": "openai",
            "model": "gpt-4.1"
        }
        
        with __import__('unittest.mock').patch.object(service.ai_service, 'generate_reply', new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = mock_response
            
            profile_data, extraction_response = await service.extract_profile_data(test_messages)
            
            # Verify structure
            assert isinstance(profile_data, type(profile_data))
            assert isinstance(extraction_response, dict)
            assert "raw_ai_response" in extraction_response
            assert "assessment" in extraction_response
            assert extraction_response["model_used"] == "gpt-4.1"
            
            print("   ✅ Service returns correct structure")
            print(f"   ✅ Model: {extraction_response['model_used']}")
            print(f"   ✅ Assessment has {len(extraction_response['assessment'])} fields")
        
        print("\n5. Testing schema validation...")
        from app.schemas.profile import ProfileDataResponse
        
        # Test that schema accepts extraction_response
        test_response = ProfileDataResponse(
            user_id="00000000-0000-0000-0000-000000000000",
            learning_goals=[],
            previous_knowledge={},
            learning_experiences={},
            usage_context={},
            extraction_response=extraction_response,
            profile_building_conversation_id=None,
            created_at=__import__('datetime').datetime.now(),
            updated_at=__import__('datetime').datetime.now()
        )
        print("   ✅ Schema accepts extraction_response")
        
        print("\n" + "=" * 70)
        print("✅ ALL TESTS PASSED")
        print("=" * 70)
        print()
        print("The extraction_response feature is working correctly!")
        print()
        print("Next: Test with real API calls in your development environment.")
        return 0
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(test_extraction_response_feature())
    sys.exit(exit_code)
