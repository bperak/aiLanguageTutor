#!/usr/bin/env python
"""
check_croatian_pos_status.py

Simple script to check the current status of Croatian POS tags
without running into NetworkX version issues.
"""

import logging
from collections import Counter

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Croatian POS tag mappings (old format -> Universal POS)
CROATIAN_TO_UNIVERSAL_POS = {
    'im': 'NOUN',          # imenica (noun)
    'gl': 'VERB',          # glagol (verb)
    'pr': 'ADJ',           # pridjev (adjective)
    'pril': 'ADV',         # prilog (adverb)
    'zamj': 'PRON',        # zamjenica (pronoun)
    'prijedl': 'ADP',      # prijedlog (preposition)
    'vezn': 'CCONJ',       # veznik (conjunction)
    'broj': 'NUM',         # broj (numeral)
    'čest': 'PART',        # čestica (particle)
    'uzv': 'INTJ',         # uzvik (interjection)
}

def check_croatian_pos_status():
    """Check the current status of Croatian POS tags."""
    try:
        # Use the existing Croatian helper to load the graph
        from croatian_helper import load_croatian_graph
        
        G = load_croatian_graph()
        if not G:
            print("❌ Failed to load Croatian graph")
            return
        
        total_nodes = G.number_of_nodes()
        print(f"📊 Total Croatian nodes: {total_nodes}")
        
        # Analyze node ID patterns
        croatian_pos_count = 0
        universal_pos_count = 0
        no_pos_count = 0
        
        croatian_pos_examples = []
        universal_pos_examples = []
        no_pos_examples = []
        
        pos_tag_distribution = Counter()
        
        for node_id in G.nodes():
            if '-' in node_id:
                parts = node_id.split('-')
                if len(parts) == 2:
                    word, pos = parts
                    pos_tag_distribution[pos] += 1
                    
                    # Check if it's a Croatian-specific POS tag
                    if pos.lower() in CROATIAN_TO_UNIVERSAL_POS:
                        croatian_pos_count += 1
                        if len(croatian_pos_examples) < 5:
                            croatian_pos_examples.append(node_id)
                    # Check if it's a Universal POS tag
                    elif pos.upper() in ['NOUN', 'VERB', 'ADJ', 'ADV', 'PRON', 'ADP', 'CCONJ', 'SCONJ', 'NUM', 'PART', 'INTJ', 'DET', 'PUNCT', 'X']:
                        universal_pos_count += 1
                        if len(universal_pos_examples) < 5:
                            universal_pos_examples.append(node_id)
                    else:
                        # Unknown POS format
                        if len(no_pos_examples) < 5:
                            no_pos_examples.append(node_id)
                else:
                    no_pos_count += 1
                    if len(no_pos_examples) < 5:
                        no_pos_examples.append(node_id)
            else:
                no_pos_count += 1
                if len(no_pos_examples) < 5:
                    no_pos_examples.append(node_id)
        
        print(f"\n📈 POS Tag Analysis:")
        print(f"  Nodes with Croatian POS tags (im, gl, pr, etc.): {croatian_pos_count}")
        print(f"  Nodes with Universal POS tags (NOUN, VERB, ADJ, etc.): {universal_pos_count}")
        print(f"  Nodes without clear POS tags: {no_pos_count}")
        
        if croatian_pos_examples:
            print(f"\n🇭🇷 Croatian POS Examples:")
            for example in croatian_pos_examples:
                print(f"    {example}")
        
        if universal_pos_examples:
            print(f"\n🌍 Universal POS Examples:")
            for example in universal_pos_examples:
                print(f"    {example}")
        
        if no_pos_examples:
            print(f"\n❓ No Clear POS Examples:")
            for example in no_pos_examples:
                print(f"    {example}")
        
        print(f"\n📊 POS Tag Distribution:")
        for pos, count in pos_tag_distribution.most_common(10):
            tag_type = ""
            if pos.lower() in CROATIAN_TO_UNIVERSAL_POS:
                tag_type = f" (Croatian -> {CROATIAN_TO_UNIVERSAL_POS[pos.lower()]})"
            elif pos.upper() in ['NOUN', 'VERB', 'ADJ', 'ADV', 'PRON', 'ADP', 'CCONJ', 'SCONJ', 'NUM', 'PART', 'INTJ', 'DET', 'PUNCT', 'X']:
                tag_type = " (Universal)"
            
            print(f"    {pos}: {count}{tag_type}")
        
        # Summary and recommendation
        print(f"\n💡 Summary:")
        inconsistency_percentage = (croatian_pos_count / total_nodes * 100) if total_nodes > 0 else 0
        print(f"  {inconsistency_percentage:.1f}% of nodes use Croatian-specific POS tags")
        
        if croatian_pos_count > 0:
            print(f"  ⚠️  INCONSISTENCY DETECTED: {croatian_pos_count} nodes need migration")
            print(f"  📋 Recommendation: Run migration to convert Croatian POS tags to Universal format")
        else:
            print(f"  ✅ All nodes use consistent Universal POS tags")
            
    except Exception as e:
        print(f"❌ Error checking Croatian POS status: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🔍 Croatian POS Tag Status Check")
    print("=" * 40)
    check_croatian_pos_status() 