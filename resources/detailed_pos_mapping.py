#!/usr/bin/env python3
"""
Detailed POS mapping analysis between Lee李 and UniDic
"""

import unidic
import MeCab
import pandas as pd
from pathlib import Path
from collections import defaultdict, Counter
import sys

def create_pos_mapping():
    """Create a mapping between Lee李 and UniDic POS systems"""
    print("=" * 60)
    print("CREATING POS MAPPING BETWEEN LEE李 AND UNIDIC")
    print("=" * 60)
    
    # Load Lee李 vocabulary
    lee_file = Path("Lee李  分類語彙表学習者用goi.xlsx - Sheet1.tsv")
    df = pd.read_csv(lee_file, sep='\t', encoding='utf-8')
    
    # Initialize MeCab with UniDic
    tagger = MeCab.Tagger()
    
    # Create mapping dictionaries
    lee_to_unidic = defaultdict(list)
    unidic_to_lee = defaultdict(list)
    
    # Analyze a sample of words
    sample_size = min(1000, len(df))
    sample_df = df.head(sample_size)
    
    print(f"Analyzing {sample_size} words for POS mapping...")
    
    for _, row in sample_df.iterrows():
        word = row['Standard orthography (kanji or other) 標準的な表記']
        lee_pos1 = row['品詞1']
        lee_pos2 = row['品詞2(詳細)']
        
        try:
            # Analyze with UniDic
            result = tagger.parse(word)
            lines = result.strip().split('\n')
            
            for line in lines:
                if line.strip() and line.strip() != 'EOS':
                    parts = line.split('\t')
                    if len(parts) >= 2:
                        features = parts[1].split(',')
                        if len(features) >= 2:
                            unidic_pos1 = features[0]
                            unidic_pos2 = features[1]
                            
                            # Create mappings
                            lee_to_unidic[lee_pos1].append(unidic_pos1)
                            unidic_to_lee[unidic_pos1].append(lee_pos1)
                            break
                            
        except Exception as e:
            continue
    
    # Count mappings
    print("\nLee李 → UniDic POS1 Mapping:")
    for lee_pos, unidic_positions in lee_to_unidic.items():
        pos_counts = Counter(unidic_positions)
        print(f"  {lee_pos}:")
        for unidic_pos, count in pos_counts.most_common():
            print(f"    → {unidic_pos} ({count} times)")
    
    print("\nUniDic → Lee李 POS1 Mapping:")
    for unidic_pos, lee_positions in unidic_to_lee.items():
        pos_counts = Counter(lee_positions)
        print(f"  {unidic_pos}:")
        for lee_pos, count in pos_counts.most_common():
            print(f"    ← {lee_pos} ({count} times)")
    
    return lee_to_unidic, unidic_to_lee

def analyze_verb_classifications():
    """Analyze how Lee李 verb classes map to UniDic"""
    print("\n" + "=" * 60)
    print("ANALYZING VERB CLASSIFICATIONS")
    print("=" * 60)
    
    # Load Lee李 vocabulary
    lee_file = Path("Lee李  分類語彙表学習者用goi.xlsx - Sheet1.tsv")
    df = pd.read_csv(lee_file, sep='\t', encoding='utf-8')
    
    # Filter for verbs
    verb_df = df[df['品詞1'].isin(['動詞1類', '動詞2類', '動詞3類'])]
    
    print(f"Found {len(verb_df)} verbs in Lee李 vocabulary")
    print(f" 動詞1類: {len(verb_df[verb_df['品詞1'] == '動詞1類'])}")
    print(f" 動詞2類: {len(verb_df[verb_df['品詞1'] == '動詞2類'])}")
    print(f" 動詞3類: {len(verb_df[verb_df['品詞1'] == '動詞3類'])}")
    
    # Initialize MeCab
    tagger = MeCab.Tagger()
    
    # Analyze verb mappings
    verb_mappings = defaultdict(list)
    
    for _, row in verb_df.head(50).iterrows():  # Sample 50 verbs
        word = row['Standard orthography (kanji or other) 標準的な表記']
        lee_verb_class = row['品詞1']
        
        try:
            result = tagger.parse(word)
            lines = result.strip().split('\n')
            
            for line in lines:
                if line.strip() and line.strip() != 'EOS':
                    parts = line.split('\t')
                    if len(parts) >= 2:
                        features = parts[1].split(',')
                        if len(features) >= 2:
                            unidic_pos1 = features[0]
                            unidic_pos2 = features[1]
                            
                            verb_mappings[lee_verb_class].append({
                                'word': word,
                                'unidic_pos1': unidic_pos1,
                                'unidic_pos2': unidic_pos2
                            })
                            break
                            
        except Exception as e:
            continue
    
    # Show verb mappings
    for verb_class, mappings in verb_mappings.items():
        print(f"\n{verb_class} → UniDic:")
        pos_counts = Counter([m['unidic_pos1'] for m in mappings])
        for pos, count in pos_counts.most_common():
            print(f"  → {pos} ({count} times)")
            
        # Show some examples
        print(f"  Examples:")
        for mapping in mappings[:5]:
            print(f"    {mapping['word']}: {mapping['unidic_pos1']},{mapping['unidic_pos2']}")

def analyze_adjective_classifications():
    """Analyze how Lee李 adjective types map to UniDic"""
    print("\n" + "=" * 60)
    print("ANALYZING ADJECTIVE CLASSIFICATIONS")
    print("=" * 60)
    
    # Load Lee李 vocabulary
    lee_file = Path("Lee李  分類語彙表学習者用goi.xlsx - Sheet1.tsv")
    df = pd.read_csv(lee_file, sep='\t', encoding='utf-8')
    
    # Filter for adjectives
    adj_df = df[df['品詞1'].isin(['イ形容詞', 'ナ形容詞'])]
    
    print(f"Found {len(adj_df)} adjectives in Lee李 vocabulary")
    print(f" イ形容詞: {len(adj_df[adj_df['品詞1'] == 'イ形容詞'])}")
    print(f" ナ形容詞: {len(adj_df[adj_df['品詞1'] == 'ナ形容詞'])}")
    
    # Initialize MeCab
    tagger = MeCab.Tagger()
    
    # Analyze adjective mappings
    adj_mappings = defaultdict(list)
    
    for _, row in adj_df.head(30).iterrows():  # Sample 30 adjectives
        word = row['Standard orthography (kanji or other) 標準的な表記']
        lee_adj_type = row['品詞1']
        
        try:
            result = tagger.parse(word)
            lines = result.strip().split('\n')
            
            for line in lines:
                if line.strip() and line.strip() != 'EOS':
                    parts = line.split('\t')
                    if len(parts) >= 2:
                        features = parts[1].split(',')
                        if len(features) >= 2:
                            unidic_pos1 = features[0]
                            unidic_pos2 = features[1]
                            
                            adj_mappings[lee_adj_type].append({
                                'word': word,
                                'unidic_pos1': unidic_pos1,
                                'unidic_pos2': unidic_pos2
                            })
                            break
                            
        except Exception as e:
            continue
    
    # Show adjective mappings
    for adj_type, mappings in adj_mappings.items():
        print(f"\n{adj_type} → UniDic:")
        pos_counts = Counter([m['unidic_pos1'] for m in mappings])
        for pos, count in pos_counts.most_common():
            print(f"  → {pos} ({count} times)")
            
        # Show some examples
        print(f"  Examples:")
        for mapping in mappings[:5]:
            print(f"    {mapping['word']}: {mapping['unidic_pos1']},{mapping['unidic_pos2']}")

def create_mapping_table():
    """Create a comprehensive mapping table"""
    print("\n" + "=" * 60)
    print("COMPREHENSIVE POS MAPPING TABLE")
    print("=" * 60)
    
    # Define the mapping based on analysis
    mapping_table = {
        # Lee李 POS1 → UniDic POS1
        '名詞': '名詞',
        '動詞1類': '動詞',
        '動詞2類': '動詞', 
        '動詞3類': '動詞',
        'イ形容詞': '形容詞',
        'ナ形容詞': '形容詞',
        '副詞': '副詞',
        '感動詞': '感動詞',
        '接頭辞': '接頭辞',
        '接尾辞': '名詞',  # Often treated as noun in UniDic
        '代名詞': '代名詞',
        '接続詞': '名詞',  # Often treated as noun in UniDic
        '連体詞': '名詞',  # Often treated as noun in UniDic
        '定型表現': '名詞',  # Often treated as noun in UniDic
    }
    
    print("Lee李 POS1 → UniDic POS1 Mapping:")
    for lee_pos, unidic_pos in mapping_table.items():
        print(f"  {lee_pos:<15} → {unidic_pos}")
    
    # Reverse mapping
    print("\nUniDic POS1 → Lee李 POS1 Mapping:")
    reverse_mapping = defaultdict(list)
    for lee_pos, unidic_pos in mapping_table.items():
        reverse_mapping[unidic_pos].append(lee_pos)
    
    for unidic_pos, lee_positions in reverse_mapping.items():
        print(f"  {unidic_pos:<10} ← {', '.join(lee_positions)}")
    
    return mapping_table

def main():
    """Main analysis function"""
    print("DETAILED POS MAPPING ANALYSIS")
    print("=" * 60)
    
    # Create POS mappings
    lee_to_unidic, unidic_to_lee = create_pos_mapping()
    
    # Analyze verb classifications
    analyze_verb_classifications()
    
    # Analyze adjective classifications
    analyze_adjective_classifications()
    
    # Create comprehensive mapping table
    mapping_table = create_mapping_table()
    
    print("\n" + "=" * 60)
    print("POS MAPPING ANALYSIS COMPLETED")
    print("=" * 60)

if __name__ == "__main__":
    main()


