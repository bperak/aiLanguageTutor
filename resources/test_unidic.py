#!/usr/bin/env python3
"""
Test UniDic functionality with our vocabulary
"""

import unidic
import os
import sys
from pathlib import Path

def test_unidic_basic():
    """Test basic UniDic functionality"""
    print("=" * 60)
    print("TESTING UNIDIC BASIC FUNCTIONALITY")
    print("=" * 60)
    
    print(f"UniDic version: {unidic.VERSION}")
    print(f"Dictionary directory: {unidic.DICDIR}")
    
    # Test if we can access the dictionary
    dic_path = Path(unidic.DICDIR)
    if dic_path.exists():
        print(f"✅ Dictionary directory exists: {dic_path}")
        
        # List some files in the dictionary
        files = list(dic_path.glob("*"))
        print(f"Dictionary contains {len(files)} files/directories")
        
        # Look for main dictionary files
        for file in files[:5]:  # Show first 5
            print(f"  - {file.name}")
    else:
        print(f"❌ Dictionary directory not found: {dic_path}")

def test_unidic_analysis():
    """Test UniDic morphological analysis"""
    print("\n" + "=" * 60)
    print("TESTING UNIDIC MORPHOLOGICAL ANALYSIS")
    print("=" * 60)
    
    # Test words from our vocabulary
    test_words = [
        "こんにちは",
        "愛",
        "アイス", 
        "挨拶",
        "相手",
        "六十路",
        "数多"
    ]
    
    try:
        # Try to use UniDic for analysis
        from unidic import UniDic
        
        print("Attempting to initialize UniDic analyzer...")
        ud = UniDic()
        print("✅ UniDic analyzer initialized successfully!")
        
        for word in test_words:
            print(f"\nAnalyzing: {word}")
            try:
                results = ud.analyze(word)
                print(f"  Results: {len(results)} entries")
                
                for i, result in enumerate(results[:2]):  # Show first 2 results
                    print(f"    Entry {i+1}:")
                    print(f"      Surface: {result.get('surface', 'N/A')}")
                    print(f"      Lemma: {result.get('lemma', 'N/A')}")
                    print(f"      Reading: {result.get('reading', 'N/A')}")
                    print(f"      Pronunciation: {result.get('pron', 'N/A')}")
                    print(f"      POS: {result.get('pos1', 'N/A')} - {result.get('pos2', 'N/A')}")
                    print(f"      Word type: {result.get('goshu', 'N/A')}")
                    print(f"      Accent: {result.get('aType', 'N/A')}")
                    
            except Exception as e:
                print(f"  ❌ Error analyzing '{word}': {e}")
                
    except ImportError as e:
        print(f"❌ Could not import UniDic analyzer: {e}")
        print("This might be a different UniDic package than expected.")
    except Exception as e:
        print(f"❌ Error initializing UniDic: {e}")

def test_unidic_dictionary_access():
    """Test direct dictionary file access"""
    print("\n" + "=" * 60)
    print("TESTING UNIDIC DICTIONARY ACCESS")
    print("=" * 60)
    
    dic_path = Path(unidic.DICDIR)
    
    # Look for CSV or data files
    data_files = []
    for pattern in ["*.csv", "*.tsv", "*.txt", "*.dic"]:
        data_files.extend(dic_path.glob(pattern))
    
    if data_files:
        print(f"Found {len(data_files)} potential data files:")
        for file in data_files[:5]:
            print(f"  - {file.name} ({file.stat().st_size} bytes)")
            
        # Try to read a small sample from the first file
        if data_files:
            sample_file = data_files[0]
            print(f"\nSampling from: {sample_file.name}")
            try:
                with open(sample_file, 'r', encoding='utf-8') as f:
                    lines = [f.readline().strip() for _ in range(3)]
                    for i, line in enumerate(lines):
                        if line:
                            print(f"  Line {i+1}: {line[:100]}...")
            except Exception as e:
                print(f"  ❌ Error reading file: {e}")
    else:
        print("No obvious data files found in dictionary directory")
        
        # List all files recursively
        all_files = list(dic_path.rglob("*"))
        print(f"Total files in dictionary: {len(all_files)}")
        
        # Show some examples
        for file in all_files[:10]:
            if file.is_file():
                print(f"  - {file.relative_to(dic_path)}")

def main():
    """Main test function"""
    print("UNIDIC INSTALLATION TEST")
    print("=" * 60)
    
    test_unidic_basic()
    test_unidic_analysis()
    test_unidic_dictionary_access()
    
    print("\n" + "=" * 60)
    print("UNIDIC TEST COMPLETED")
    print("=" * 60)

if __name__ == "__main__":
    main()


