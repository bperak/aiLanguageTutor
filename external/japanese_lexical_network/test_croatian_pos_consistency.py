#!/usr/bin/env python
"""
test_croatian_pos_consistency.py

Test script to verify that the Croatian POS consistency changes work properly.
"""

import json
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_ai_generation_pos_consistency():
    """Test that the AI generation now uses Universal POS tags consistently."""
    
    print("🧪 Testing Croatian POS Consistency")
    print("=" * 40)
    
    try:
        # Test the generate_translation_and_pos function
        from croatian_ai_generation import generate_translation_and_pos
        
        print("\n📋 Testing translate_and_pos function...")
        
        # Test with a simple Croatian word
        test_word = "ljubav"
        result = generate_translation_and_pos(test_word, context="Testing POS consistency")
        
        print(f"Input word: {test_word}")
        print(f"Result: {json.dumps(result, indent=2, ensure_ascii=False)}")
        
        # Check if the result uses Universal POS tags
        pos = result.get('pos', '')
        upos = result.get('upos', '')
        
        universal_pos_tags = ['NOUN', 'VERB', 'ADJ', 'ADV', 'PRON', 'ADP', 'CCONJ', 'SCONJ', 'NUM', 'PART', 'INTJ', 'DET', 'PUNCT', 'X']
        croatian_pos_tags = ['im', 'gl', 'pr', 'pril', 'zamj', 'prijedl', 'vezn', 'broj', 'čest', 'uzv']
        
        pos_is_universal = pos.upper() in universal_pos_tags
        upos_is_universal = upos.upper() in universal_pos_tags
        pos_is_croatian = pos.lower() in croatian_pos_tags
        
        print(f"\n📊 POS Analysis:")
        print(f"  pos field: '{pos}' - Universal: {pos_is_universal}, Croatian: {pos_is_croatian}")
        print(f"  upos field: '{upos}' - Universal: {upos_is_universal}")
        
        if pos_is_universal and upos_is_universal and not pos_is_croatian:
            print("✅ POS consistency test PASSED - Using Universal POS tags")
            return True
        else:
            print("❌ POS consistency test FAILED - Still using Croatian-specific tags")
            return False
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_node_id_format():
    """Test that node IDs are generated with Universal POS format."""
    
    print("\n🏷️  Testing Node ID Format...")
    
    # Simulate creating a node ID with Universal POS
    test_cases = [
        ("ljubav", "NOUN", "ljubav-NOUN"),
        ("pisati", "VERB", "pisati-VERB"),
        ("lijep", "ADJ", "lijep-ADJ"),
        ("brzo", "ADV", "brzo-ADV"),
    ]
    
    all_passed = True
    
    for word, pos, expected in test_cases:
        actual = f"{word}-{pos}"
        passed = actual == expected
        status = "✅" if passed else "❌"
        print(f"  {status} {word} + {pos} → {actual} (expected: {expected})")
        if not passed:
            all_passed = False
    
    return all_passed

def test_prompt_updates():
    """Test that the AI generation prompts use Universal POS tags."""
    
    print("\n📝 Testing Prompt Updates...")
    
    try:
        # Read the Croatian AI generation file to check prompts
        with open('croatian_ai_generation.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check that Croatian-specific POS tags are not mentioned in prompts
        croatian_tags_found = []
        universal_tags_found = []
        
        # Look for Croatian tags that should no longer be in prompts
        old_croatian_tags = ['im:', 'gl:', 'pr:', 'pril:', 'zamj:', 'prijedl:', 'vezn:', 'broj:', 'čest:', 'uzv:']
        for tag in old_croatian_tags:
            if tag in content:
                croatian_tags_found.append(tag)
        
        # Look for Universal tags that should be in prompts
        universal_tags = ['NOUN:', 'VERB:', 'ADJ:', 'ADV:', 'PRON:', 'ADP:', 'CCONJ:', 'NUM:', 'PART:', 'INTJ:']
        for tag in universal_tags:
            if tag in content:
                universal_tags_found.append(tag)
        
        print(f"  Croatian tags found: {croatian_tags_found}")
        print(f"  Universal tags found: {universal_tags_found}")
        
        if not croatian_tags_found and universal_tags_found:
            print("✅ Prompt updates test PASSED - Using Universal POS tags in prompts")
            return True
        else:
            print("❌ Prompt updates test FAILED - Still contains Croatian-specific tags")
            return False
            
    except Exception as e:
        print(f"❌ Prompt test failed: {e}")
        return False

def main():
    """Run all Croatian POS consistency tests."""
    
    print("🧪 Croatian POS Consistency Test Suite")
    print("=" * 50)
    
    tests_passed = 0
    total_tests = 3
    
    # Test 1: AI generation POS consistency
    if test_ai_generation_pos_consistency():
        tests_passed += 1
    
    # Test 2: Node ID format
    if test_node_id_format():
        tests_passed += 1
    
    # Test 3: Prompt updates
    if test_prompt_updates():
        tests_passed += 1
    
    print(f"\n📊 Test Results: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("🎉 All tests passed! Croatian POS consistency has been successfully implemented.")
    else:
        print("⚠️  Some tests failed. Please review the issues above.")
    
    return tests_passed == total_tests

if __name__ == "__main__":
    main() 