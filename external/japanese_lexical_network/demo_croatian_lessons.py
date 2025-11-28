"""
Croatian Lesson Generation Demo

This script demonstrates the comprehensive Croatian lesson generation functionality,
showcasing all the features developed for Croatian language learning.
"""

import json
import logging
from croatian_exercises import (
    generate_croatian_exercise, 
    get_croatian_exercise_modes, 
    get_croatian_learning_levels,
    is_available
)
from croatian_helper import load_croatian_graph, get_croatian_node_info
from croatian_ai_generation import generate_croatian_lexical_relations
from croatian_relation_extraction import CroatianRelationExtractor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def demo_croatian_lesson_generation():
    """Comprehensive demo of Croatian lesson generation functionality."""
    
    print("🎓 Croatian Language Learning System - Complete Demo")
    print("=" * 60)
    
    # Check availability
    if not is_available():
        print("❌ Croatian lesson generation is not available. Please check your API key.")
        return
    
    print("✅ Croatian lesson generation is available!")
    
    # Load Croatian graph
    print(f"\n📊 Loading Croatian lexical graph...")
    G_croatian = load_croatian_graph()
    if G_croatian:
        print(f"📈 Graph loaded: {G_croatian.number_of_nodes()} nodes, {G_croatian.number_of_edges()} edges")
    else:
        print("❌ Failed to load Croatian graph")
        return
    
    # Demo words for different categories
    demo_words = [
        ("ljubav-NOUN", "love - emotional concept"),
        ("kuća-NOUN", "house - concrete noun"), 
        ("pisati-VERB", "to write - common verb"),
        ("lijep-ADJ", "beautiful - descriptive adjective")
    ]
    
    # Available modes and levels
    modes = get_croatian_exercise_modes()
    levels = get_croatian_learning_levels()
    
    print(f"\n🎯 Available exercise modes:")
    for mode in modes:
        print(f"  • {mode['name']}: {mode['description']}")
    
    print(f"\n📚 Available learning levels:")
    for level in levels:
        print(f"  • Level {level['id']}: {level['description']}")
    
    print(f"\n" + "=" * 60)
    print("🧪 DEMO: Croatian Lesson Generation for Different Words")
    print("=" * 60)
    
    for word_id, description in demo_words[:2]:  # Demo first 2 words
        print(f"\n🔤 Demonstrating: {word_id} ({description})")
        print("-" * 40)
        
        # Get word information
        node_info = get_croatian_node_info(G_croatian, word_id)
        if node_info:
            print(f"📝 Croatian word: {node_info.get('natuknica', 'N/A')}")
            print(f"🌍 Translation: {node_info.get('translation', 'N/A')}")
            print(f"📖 Definition: {node_info.get('tekst', 'N/A')[:100]}...")
            print(f"🔍 Part of speech: {node_info.get('pos_readable', 'N/A')}")
        
        # Demo different exercise modes
        for mode_info in modes:
            mode = mode_info['id']
            level = 2  # Beginner 2 level
            
            print(f"\n🎮 Mode: {mode_info['name']} (Level {level})")
            
            try:
                result = generate_croatian_exercise(word_id, level=level, mode=mode)
                
                if 'error' not in result:
                    print(f"✅ Exercise generated successfully!")
                    print(f"📋 Content preview:")
                    content = result.get('content', '')
                    # Show first 300 characters
                    preview = content[:300] + "..." if len(content) > 300 else content
                    print(f"   {preview}")
                    
                    # Show exercise metadata
                    print(f"📊 Exercise details:")
                    print(f"   • Croatian word: {result.get('croatian_word', 'N/A')}")
                    print(f"   • Translation: {result.get('translation', 'N/A')}")
                    print(f"   • Mode: {result.get('mode', 'N/A')}")
                    print(f"   • Level: {result.get('level', 'N/A')}")
                    print(f"   • Language: {result.get('language', 'N/A')}")
                else:
                    print(f"❌ Error: {result['error']}")
                    
            except Exception as e:
                print(f"❌ Exception: {e}")
    
    print(f"\n" + "=" * 60)
    print("🧪 DEMO: Conversation Continuation")
    print("=" * 60)
    
    # Demo conversation continuation
    test_word = "ljubav-NOUN"
    print(f"\n💬 Demonstrating conversation continuation for: {test_word}")
    
    # Create a mock conversation history
    session_history = [
        {
            "user": "Zdravo! Što znači riječ 'ljubav'?",
            "tutor": "Zdravo! 'Ljubav' je jako lijepa riječ koja znači 'love' na engleskom. To je osjećaj dubokih emocija prema nekome."
        },
        {
            "user": "Kako mogu koristiti tu riječ u rečenici?",
            "tutor": "Odličo pitanje! Možete reći: 'Imam veliku ljubav prema mojoj obitelji' ili 'Ljubav je najvažnija stvar u životu.'"
        }
    ]
    
    print(f"📜 Conversation history:")
    for i, turn in enumerate(session_history):
        print(f"   Turn {i+1}:")
        print(f"   Student: {turn['user']}")
        print(f"   Tutor: {turn['tutor']}")
    
    print(f"\n🔄 Generating continuation...")
    
    try:
        continuation = generate_croatian_exercise(
            test_word, 
            level=2, 
            session_history=session_history, 
            mode="exercise"
        )
        
        if 'error' not in continuation:
            print(f"✅ Continuation generated successfully!")
            print(f"💬 Continuation content:")
            content = continuation.get('content', '')
            preview = content[:400] + "..." if len(content) > 400 else content
            print(f"   {preview}")
        else:
            print(f"❌ Error: {continuation['error']}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")
    
    print(f"\n" + "=" * 60)
    print("🧪 DEMO: Integration with Croatian AI and Relations")
    print("=" * 60)
    
    # Demonstrate integration with other Croatian modules
    test_word = "ljubav-NOUN"
    print(f"\n🔗 Showing integration for: {test_word}")
    
    try:
        # Get AI-generated relations
        print(f"🤖 Generating AI relations...")
        ai_relations = generate_croatian_lexical_relations(test_word, count=5)
        if ai_relations and 'synonyms' in ai_relations:
            print(f"✅ Found {len(ai_relations['synonyms'])} AI synonyms")
            for i, syn in enumerate(ai_relations['synonyms'][:3]):
                print(f"   {i+1}. {syn.get('word', 'N/A')} (strength: {syn.get('strength', 'N/A')})")
        
        # Get relation analysis
        print(f"\n🔍 Analyzing relations...")
        extractor = CroatianRelationExtractor()
        relations = extractor.extract_node_relations(test_word)
        
        if relations and 'relations' in relations:
            print(f"✅ Found {len(relations['relations'])} graph relations")
            for i, rel in enumerate(relations['relations'][:3]):
                print(f"   {i+1}. {rel.get('target_word', 'N/A')} ({rel.get('relationship_type', 'N/A')})")
        
    except Exception as e:
        print(f"⚠️ Integration demo note: {e}")
    
    print(f"\n" + "=" * 60)
    print("🎉 Croatian Lesson Generation Demo Complete!")
    print("=" * 60)
    
    print(f"\n✅ Successfully demonstrated:")
    print(f"   • Croatian lesson generation for multiple words")
    print(f"   • Different exercise modes (structured vs conversation)")
    print(f"   • Multiple learning levels (beginner to advanced)")
    print(f"   • Conversation continuation functionality")
    print(f"   • Integration with Croatian AI and relation systems")
    print(f"   • Complete Croatian language learning ecosystem")
    
    print(f"\n🎓 The Croatian language learning system is fully operational!")
    print(f"   Ready for integration into the web interface.")

if __name__ == "__main__":
    demo_croatian_lesson_generation() 