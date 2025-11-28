#!/usr/bin/env python3
"""
Check the word "愛" in UniDic
"""

import MeCab
import unidic

def check_ai_word():
    """Check the word 愛 in UniDic"""
    print("=" * 60)
    print("CHECKING WORD '愛' IN UNIDIC")
    print("=" * 60)
    
    try:
        # Initialize MeCab with UniDic
        tagger = MeCab.Tagger()
        
        word = "愛"
        print(f"Analyzing word: {word}")
        
        # Get full analysis
        result = tagger.parse(word)
        print(f"\nFull UniDic analysis:")
        print(result)
        
        # Parse the result
        lines = result.strip().split('\n')
        
        print(f"\nParsed analysis:")
        for i, line in enumerate(lines):
            if line.strip() and line.strip() != 'EOS':
                parts = line.split('\t')
                if len(parts) >= 2:
                    surface = parts[0]
                    features = parts[1].split(',')
                    
                    print(f"  Entry {i+1}:")
                    print(f"    Surface: {surface}")
                    print(f"    Features: {features}")
                    
                    if len(features) >= 10:
                        print(f"    POS1: {features[0]}")
                        print(f"    POS2: {features[1]}")
                        print(f"    POS3: {features[2]}")
                        print(f"    POS4: {features[3]}")
                        print(f"    cType: {features[4]}")
                        print(f"    cForm: {features[5]}")
                        print(f"    lForm: {features[6]}")
                        print(f"    lemma: {features[7]}")
                        print(f"    orth: {features[8]}")
                        print(f"    pron: {features[9]}")
        
        # Check if there are multiple entries
        print(f"\nNumber of entries found: {len([l for l in lines if l.strip() and l.strip() != 'EOS'])}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    check_ai_word()


