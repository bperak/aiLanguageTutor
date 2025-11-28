#!/usr/bin/env python
"""
check_croatian_translations.py

Simple script to check the current state of Croatian translations in the graph.
This script helps you understand how many nodes need translations before running
the batch translation script.
"""

import logging
from croatian_helper import load_croatian_graph
from croatian_ai_generation import is_available

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def analyze_croatian_graph():
    """Analyze the current state of Croatian translations."""
    print("🔍 Analyzing Croatian Graph Translation Status")
    print("=" * 50)
    
    # Check API availability
    if not is_available():
        print("❌ Gemini API not available - translation generation will not work")
        print("   Please check your API key configuration")
    else:
        print("✅ Gemini API available - ready for translation generation")
    
    # Load Croatian graph
    G = load_croatian_graph()
    if G is None:
        print("❌ Failed to load Croatian graph")
        return
    
    print(f"✅ Croatian graph loaded: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    
    # Analyze translations
    total_nodes = G.number_of_nodes()
    nodes_with_translation = 0
    nodes_without_translation = 0
    empty_translations = 0
    nodes_with_pos = 0
    nodes_without_pos = 0
    
    sample_nodes_without_translation = []
    sample_nodes_with_translation = []
    
    for node_id, attrs in G.nodes(data=True):
        translation = attrs.get('translation', '').strip()
        pos = attrs.get('pos', '').strip()
        upos = attrs.get('UPOS', '').strip()
        
        if translation:
            nodes_with_translation += 1
            if len(sample_nodes_with_translation) < 5:
                sample_nodes_with_translation.append((node_id, translation))
        else:
            nodes_without_translation += 1
            if len(sample_nodes_without_translation) < 10:
                natuknica = attrs.get('natuknica', '')
                sample_nodes_without_translation.append((node_id, natuknica))
        
        if pos or upos:
            nodes_with_pos += 1
        else:
            nodes_without_pos += 1
    
    # Print statistics
    print(f"\n📊 TRANSLATION STATISTICS")
    print("-" * 30)
    print(f"Total nodes: {total_nodes}")
    print(f"Nodes with translation: {nodes_with_translation} ({(nodes_with_translation/total_nodes)*100:.1f}%)")
    print(f"Nodes without translation: {nodes_without_translation} ({(nodes_without_translation/total_nodes)*100:.1f}%)")
    
    print(f"\n📊 POS INFORMATION STATISTICS")
    print("-" * 30)
    print(f"Nodes with POS info: {nodes_with_pos} ({(nodes_with_pos/total_nodes)*100:.1f}%)")
    print(f"Nodes without POS info: {nodes_without_pos} ({(nodes_without_pos/total_nodes)*100:.1f}%)")
    
    # Show samples
    if sample_nodes_with_translation:
        print(f"\n✅ SAMPLE NODES WITH TRANSLATIONS:")
        for node_id, translation in sample_nodes_with_translation:
            print(f"  {node_id} -> {translation}")
    
    if sample_nodes_without_translation:
        print(f"\n❌ SAMPLE NODES WITHOUT TRANSLATIONS:")
        for node_id, natuknica in sample_nodes_without_translation:
            print(f"  {node_id} ({natuknica})")
    
    # Provide recommendations
    print(f"\n💡 RECOMMENDATIONS")
    print("-" * 30)
    
    if nodes_without_translation > 0:
        print(f"🔧 Run batch translation to add {nodes_without_translation} missing translations:")
        print(f"   python batch_translate_croatian.py --batch-size 100 --max-batches 5 --dry-run")
        print(f"   (Remove --dry-run to actually make changes)")
        
        # Calculate estimated time
        estimated_time = (nodes_without_translation * 0.5) / 60  # 0.5 seconds per translation
        print(f"   Estimated time: {estimated_time:.1f} minutes for all translations")
        
        # Suggest batch sizes
        if nodes_without_translation > 1000:
            print(f"   Suggestion: Process in multiple sessions of 500-1000 nodes each")
        elif nodes_without_translation > 100:
            print(f"   Suggestion: Use batch size of 50-100 for optimal performance")
        else:
            print(f"   Suggestion: Can process all {nodes_without_translation} nodes in one session")
    else:
        print("🎉 All nodes already have translations!")
    
    print(f"\n🔧 EXAMPLE COMMANDS:")
    print("   # Check current status:")
    print("   python check_croatian_translations.py")
    print("   ")
    print("   # Test with a small batch (dry run):")
    print("   python batch_translate_croatian.py --batch-size 10 --max-batches 1 --dry-run")
    print("   ")
    print("   # Process first 100 nodes:")
    print("   python batch_translate_croatian.py --batch-size 100 --max-batches 1")
    print("   ")
    print("   # Process multiple batches:")
    print("   python batch_translate_croatian.py --batch-size 50 --max-batches 10")
    print("   ")
    print("   # Continue from where you left off:")
    print("   python batch_translate_croatian.py --start-from 500 --batch-size 100 --max-batches 5")

if __name__ == "__main__":
    analyze_croatian_graph() 