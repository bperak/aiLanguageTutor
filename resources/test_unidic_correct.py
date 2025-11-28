#!/usr/bin/env python3
"""
Test the correct UniDic functionality
"""

import unidic
import os
import sys
from pathlib import Path

def test_unidic_package():
    """Test what's actually available in the unidic package"""
    print("=" * 60)
    print("TESTING UNIDIC PACKAGE STRUCTURE")
    print("=" * 60)
    
    print(f"UniDic version: {unidic.VERSION}")
    print(f"Dictionary directory: {unidic.DICDIR}")
    
    # Check what's in the unidic module
    print(f"\nUniDic module contents:")
    for item in dir(unidic):
        if not item.startswith('_'):
            print(f"  - {item}")
    
    # Check the unidic.unidic submodule
    print(f"\nUniDic.unidic submodule contents:")
    for item in dir(unidic.unidic):
        if not item.startswith('_'):
            print(f"  - {item}")

def test_dictionary_files():
    """Test access to dictionary files"""
    print("\n" + "=" * 60)
    print("TESTING DICTIONARY FILES")
    print("=" * 60)
    
    dic_path = Path(unidic.DICDIR)
    print(f"Dictionary path: {dic_path}")
    
    if dic_path.exists():
        # List all files
        all_files = list(dic_path.rglob("*"))
        print(f"Total files: {len(all_files)}")
        
        # Show file types
        file_types = {}
        for file in all_files:
            if file.is_file():
                ext = file.suffix or 'no_extension'
                file_types[ext] = file_types.get(ext, 0) + 1
        
        print(f"\nFile types:")
        for ext, count in sorted(file_types.items()):
            print(f"  {ext}: {count} files")
        
        # Show some example files
        print(f"\nExample files:")
        for file in all_files[:10]:
            if file.is_file():
                size = file.stat().st_size
                print(f"  {file.name} ({size:,} bytes)")

def test_mecab_integration():
    """Test if we can use MeCab with UniDic"""
    print("\n" + "=" * 60)
    print("TESTING MECAB INTEGRATION")
    print("=" * 60)
    
    try:
        import MeCab
        print("✅ MeCab is available")
        
        # Try to create a MeCab tagger with UniDic
        try:
            tagger = MeCab.Tagger(f"-d {unidic.DICDIR}")
            print("✅ MeCab tagger created with UniDic dictionary")
            
            # Test with some words
            test_words = ["こんにちは", "愛", "アイス", "挨拶"]
            
            for word in test_words:
                print(f"\nAnalyzing: {word}")
                result = tagger.parse(word)
                print(f"Result: {result.strip()}")
                
        except Exception as e:
            print(f"❌ Error creating MeCab tagger: {e}")
            
    except ImportError:
        print("❌ MeCab not available - need to install MeCab")
        print("You can install it with: pip install mecab-python3")

def test_alternative_approach():
    """Test alternative approaches to access UniDic data"""
    print("\n" + "=" * 60)
    print("TESTING ALTERNATIVE APPROACHES")
    print("=" * 60)
    
    # Check if there are any CSV or text files we can read directly
    dic_path = Path(unidic.DICDIR)
    
    # Look for data files
    data_patterns = ["*.csv", "*.tsv", "*.txt", "*.dic"]
    data_files = []
    
    for pattern in data_patterns:
        data_files.extend(dic_path.glob(pattern))
        data_files.extend(dic_path.glob(f"**/{pattern}"))
    
    if data_files:
        print(f"Found {len(data_files)} potential data files:")
        for file in data_files:
            size = file.stat().st_size
            print(f"  {file.name} ({size:,} bytes)")
            
        # Try to read a small sample
        sample_file = data_files[0]
        print(f"\nTrying to read sample from: {sample_file.name}")
        
        try:
            # Try different encodings
            for encoding in ['utf-8', 'shift_jis', 'euc-jp', 'cp932']:
                try:
                    with open(sample_file, 'r', encoding=encoding) as f:
                        line = f.readline()
                        if line:
                            print(f"  Success with {encoding}: {line[:100]}...")
                            break
                except UnicodeDecodeError:
                    continue
            else:
                print("  Could not decode with any common Japanese encoding")
                
        except Exception as e:
            print(f"  Error reading file: {e}")
    else:
        print("No obvious data files found")

def main():
    """Main test function"""
    print("UNIDIC CORRECT PACKAGE TEST")
    print("=" * 60)
    
    test_unidic_package()
    test_dictionary_files()
    test_mecab_integration()
    test_alternative_approach()
    
    print("\n" + "=" * 60)
    print("UNIDIC TEST COMPLETED")
    print("=" * 60)

if __name__ == "__main__":
    main()


