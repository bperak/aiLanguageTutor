#!/usr/bin/env python3
"""
Test script for AI content generation

Tests the AI content generation service with a simple word.
"""

import asyncio
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from root .env file
project_root = Path(__file__).parent.parent
load_dotenv(project_root / ".env")

# Add the backend directory to the Python path
backend_dir = project_root / "backend"
sys.path.insert(0, str(backend_dir))

from app.services.ai_word_content_service import ai_word_content_service

async def test_ai_content_generation():
    """Test AI content generation for a simple word"""
    
    print("🧪 Testing AI Content Generation Service")
    print("=" * 50)
    
    # Test word
    test_word = "水"  # water
    
    try:
        print(f"Testing word: {test_word}")
        print("Generating AI content...")
        
        # Generate content
        content = await ai_word_content_service.generate_word_content(
            word_kanji=test_word,
            session=None,  # Will create session automatically
            force_regenerate=True
        )
        
        if content:
            print("✅ Successfully generated AI content!")
            print(f"   Confidence Score: {content.confidence_score:.2f}")
            print(f"   Model Used: {content.model_used}")
            print(f"   Generated At: {content.generated_at}")
            print()
            
            print("📝 Definitions:")
            for i, definition in enumerate(content.definitions, 1):
                print(f"   {i}. {definition}")
            print()
            
            print("💡 Examples:")
            for i, example in enumerate(content.examples, 1):
                print(f"   {i}. {example}")
            print()
            
            print("🌏 Cultural Notes:")
            print(f"   {content.cultural_notes}")
            print()
            
            print("🔤 Kanji Breakdown:")
            print(f"   {content.kanji_breakdown}")
            print()
            
            print("📚 Grammar Patterns:")
            for i, pattern in enumerate(content.grammar_patterns, 1):
                print(f"   {i}. {pattern}")
            print()
            
            print("🔗 Collocations:")
            for i, collocation in enumerate(content.collocations, 1):
                print(f"   {i}. {collocation}")
            print()
            
            print("💡 Learning Tips:")
            print(f"   {content.learning_tips}")
            
        else:
            print("❌ Failed to generate AI content")
            
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_ai_content_generation())
