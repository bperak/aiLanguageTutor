#!/usr/bin/env python3
"""
Compare POS (Part of Speech) systems between Lee李 vocabulary and UniDic
"""

import unidic
import MeCab
import pandas as pd
from pathlib import Path
from collections import Counter, defaultdict
import sys

def load_lee_vocabulary():
    """Load Lee李 vocabulary and extract POS information"""
    print("=" * 60)
    print("LOADING LEE李 VOCABULARY")
    print("=" * 60)
    
    lee_file = Path("Lee李  分類語彙表学習者用goi.xlsx - Sheet1.tsv")
    
    if not lee_file.exists():
        print(f"❌ Lee李 file not found: {lee_file}")
        return None
    
    try:
        # Read the TSV file
        df = pd.read_csv(lee_file, sep='\t', encoding='utf-8')
        print(f"✅ Loaded {len(df)} entries from Lee李 vocabulary")
        
        # Get column names
        print(f"Columns: {list(df.columns)}")
        
        # Extract POS information
        pos1_col = '品詞1'  # Main POS
        pos2_col = '品詞2(詳細)'  # Detailed POS
        
        if pos1_col in df.columns and pos2_col in df.columns:
            pos1_values = df[pos1_col].dropna().unique()
            pos2_values = df[pos2_col].dropna().unique()
            
            print(f"\nLee李 POS1 (Main) categories: {len(pos1_values)}")
            for pos in sorted(pos1_values):
                count = (df[pos1_col] == pos).sum()
                print(f"  {pos}: {count} entries")
            
            print(f"\nLee李 POS2 (Detailed) categories: {len(pos2_values)}")
            for pos in sorted(pos2_values)[:20]:  # Show first 20
                count = (df[pos2_col] == pos).sum()
                print(f"  {pos}: {count} entries")
            
            if len(pos2_values) > 20:
                print(f"  ... and {len(pos2_values) - 20} more categories")
            
            return df
        else:
            print(f"❌ POS columns not found. Available columns: {list(df.columns)}")
            return None
            
    except Exception as e:
        print(f"❌ Error loading Lee李 vocabulary: {e}")
        return None

def analyze_unidic_pos():
    """Analyze UniDic POS system"""
    print("\n" + "=" * 60)
    print("ANALYZING UNIDIC POS SYSTEM")
    print("=" * 60)
    
    try:
        # Initialize MeCab with UniDic
        tagger = MeCab.Tagger()
        
        # Test words to get a sample of POS tags
        test_words = [
            "こんにちは", "愛", "アイス", "挨拶", "相手", "行く", "美しい", 
            "とても", "私", "本", "読む", "大きい", "学校", "学生", "先生",
            "食べる", "飲む", "見る", "聞く", "話す", "書く", "走る", "座る"
        ]
        
        pos1_counter = Counter()
        pos2_counter = Counter()
        pos_combinations = Counter()
        
        print("Analyzing test words with UniDic...")
        
        for word in test_words:
            try:
                result = tagger.parse(word)
                lines = result.strip().split('\n')
                
                for line in lines:
                    if line.strip() and line.strip() != 'EOS':
                        parts = line.split('\t')
                        if len(parts) >= 2:
                            surface = parts[0]
                            features = parts[1].split(',')
                            
                            if len(features) >= 2:
                                pos1 = features[0]  # Main POS
                                pos2 = features[1]  # Detailed POS
                                
                                pos1_counter[pos1] += 1
                                pos2_counter[pos2] += 1
                                pos_combinations[f"{pos1},{pos2}"] += 1
                                
            except Exception as e:
                print(f"  ❌ Error analyzing '{word}': {e}")
        
        print(f"\nUniDic POS1 (Main) categories found: {len(pos1_counter)}")
        for pos, count in pos1_counter.most_common():
            print(f"  {pos}: {count} occurrences")
        
        print(f"\nUniDic POS2 (Detailed) categories found: {len(pos2_counter)}")
        for pos, count in pos2_counter.most_common():
            print(f"  {pos}: {count} occurrences")
        
        print(f"\nUniDic POS combinations found: {len(pos_combinations)}")
        for combo, count in pos_combinations.most_common(10):
            print(f"  {combo}: {count} occurrences")
        
        return {
            'pos1': pos1_counter,
            'pos2': pos2_counter,
            'combinations': pos_combinations
        }
        
    except Exception as e:
        print(f"❌ Error analyzing UniDic POS: {e}")
        return None

def compare_pos_systems(lee_df, unidic_pos):
    """Compare POS systems between Lee李 and UniDic"""
    print("\n" + "=" * 60)
    print("COMPARING POS SYSTEMS")
    print("=" * 60)
    
    if lee_df is None or unidic_pos is None:
        print("❌ Cannot compare - missing data")
        return
    
    # Get Lee李 POS categories
    lee_pos1 = set(lee_df['品詞1'].dropna().unique())
    lee_pos2 = set(lee_df['品詞2(詳細)'].dropna().unique())
    
    # Get UniDic POS categories
    unidic_pos1 = set(unidic_pos['pos1'].keys())
    unidic_pos2 = set(unidic_pos['pos2'].keys())
    
    print("POS1 (Main) Comparison:")
    print(f"  Lee李: {len(lee_pos1)} categories")
    print(f"  UniDic: {len(unidic_pos1)} categories")
    
    print(f"\nLee李 POS1 categories:")
    for pos in sorted(lee_pos1):
        print(f"  - {pos}")
    
    print(f"\nUniDic POS1 categories:")
    for pos in sorted(unidic_pos1):
        print(f"  - {pos}")
    
    # Find common categories
    common_pos1 = lee_pos1.intersection(unidic_pos1)
    print(f"\nCommon POS1 categories: {len(common_pos1)}")
    for pos in sorted(common_pos1):
        print(f"  - {pos}")
    
    # Find unique to each system
    lee_only_pos1 = lee_pos1 - unidic_pos1
    unidic_only_pos1 = unidic_pos1 - lee_pos1
    
    print(f"\nLee李 only POS1 categories: {len(lee_only_pos1)}")
    for pos in sorted(lee_only_pos1):
        print(f"  - {pos}")
    
    print(f"\nUniDic only POS1 categories: {len(unidic_only_pos1)}")
    for pos in sorted(unidic_only_pos1):
        print(f"  - {pos}")

def analyze_specific_words(lee_df):
    """Analyze specific words with both systems"""
    print("\n" + "=" * 60)
    print("ANALYZING SPECIFIC WORDS")
    print("=" * 60)
    
    try:
        tagger = MeCab.Tagger()
        
        # Get some sample words from Lee李
        sample_words = lee_df.head(20)
        
        print("Word\tLee李 POS1\tLee李 POS2\tUniDic POS1\tUniDic POS2")
        print("-" * 80)
        
        for _, row in sample_words.iterrows():
            word = row['Standard orthography (kanji or other) 標準的な表記']
            lee_pos1 = row['品詞1']
            lee_pos2 = row['品詞2(詳細)']
            
            # Analyze with UniDic
            try:
                result = tagger.parse(word)
                lines = result.strip().split('\n')
                
                unidic_pos1 = "N/A"
                unidic_pos2 = "N/A"
                
                for line in lines:
                    if line.strip() and line.strip() != 'EOS':
                        parts = line.split('\t')
                        if len(parts) >= 2:
                            features = parts[1].split(',')
                            if len(features) >= 2:
                                unidic_pos1 = features[0]
                                unidic_pos2 = features[1]
                                break
                
                print(f"{word}\t{lee_pos1}\t{lee_pos2}\t{unidic_pos1}\t{unidic_pos2}")
                
            except Exception as e:
                print(f"{word}\t{lee_pos1}\t{lee_pos2}\tERROR\tERROR")
                
    except Exception as e:
        print(f"❌ Error analyzing specific words: {e}")

def main():
    """Main comparison function"""
    print("POS SYSTEM COMPARISON: LEE李 vs UNIDIC")
    print("=" * 60)
    
    # Load Lee李 vocabulary
    lee_df = load_lee_vocabulary()
    
    # Analyze UniDic POS system
    unidic_pos = analyze_unidic_pos()
    
    # Compare systems
    compare_pos_systems(lee_df, unidic_pos)
    
    # Analyze specific words
    if lee_df is not None:
        analyze_specific_words(lee_df)
    
    print("\n" + "=" * 60)
    print("POS COMPARISON COMPLETED")
    print("=" * 60)

if __name__ == "__main__":
    main()


