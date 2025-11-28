#!/usr/bin/env python3
"""
Working UniDic integration test
"""

import unidic
import os
import sys
from pathlib import Path

def test_mecab_simple():
    """Test MeCab with simple configuration"""
    print("=" * 60)
    print("TESTING MECAB WITH SIMPLE CONFIGURATION")
    print("=" * 60)
    
    try:
        import MeCab
        print("✅ MeCab imported successfully")
        
        # Try different MeCab configurations
        configs = [
            "",  # Default
            "-Owakati",  # Simple word segmentation
            "-Ochasen",  # ChaSen format
        ]
        
        test_word = "こんにちは"
        
        for config in configs:
            try:
                print(f"\nTrying config: '{config}'")
                tagger = MeCab.Tagger(config)
                result = tagger.parse(test_word)
                print(f"✅ Success: {result.strip()}")
                break
            except Exception as e:
                print(f"❌ Failed: {e}")
        
    except ImportError as e:
        print(f"❌ MeCab import failed: {e}")

def test_unidic_direct_access():
    """Test direct access to UniDic dictionary files"""
    print("\n" + "=" * 60)
    print("TESTING DIRECT UNIDIC ACCESS")
    print("=" * 60)
    
    dic_path = Path(unidic.DICDIR)
    print(f"UniDic dictionary path: {dic_path}")
    
    # Check if the path exists and is accessible
    if dic_path.exists():
        print("✅ Dictionary path exists")
        
        # List important files
        important_files = ['dicrc', 'feature.def', 'char.def']
        for file_name in important_files:
            file_path = dic_path / file_name
            if file_path.exists():
                print(f"✅ {file_name} exists ({file_path.stat().st_size} bytes)")
            else:
                print(f"❌ {file_name} not found")
        
        # Try to read the dicrc file
        dicrc_path = dic_path / 'dicrc'
        if dicrc_path.exists():
            try:
                with open(dicrc_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    print(f"\nDicrc content (first 200 chars):")
                    print(content[:200])
            except Exception as e:
                print(f"❌ Error reading dicrc: {e}")
    else:
        print("❌ Dictionary path does not exist")

def test_alternative_mecab_config():
    """Test alternative MeCab configuration"""
    print("\n" + "=" * 60)
    print("TESTING ALTERNATIVE MECAB CONFIG")
    print("=" * 60)
    
    try:
        import MeCab
        
        # Try with explicit path configuration
        dic_path = Path(unidic.DICDIR)
        
        # Create a temporary mecabrc file
        mecabrc_content = f"""
dicdir = {dic_path}
"""
        
        temp_mecabrc = Path("temp_mecabrc")
        try:
            with open(temp_mecabrc, 'w', encoding='utf-8') as f:
                f.write(mecabrc_content)
            
            # Try MeCab with the temp config
            tagger = MeCab.Tagger(f"-r {temp_mecabrc}")
            result = tagger.parse("こんにちは")
            print(f"✅ MeCab with temp config works: {result.strip()}")
            
        finally:
            if temp_mecabrc.exists():
                temp_mecabrc.unlink()
                
    except Exception as e:
        print(f"❌ Alternative config failed: {e}")

def test_simple_mecab():
    """Test simple MeCab without UniDic"""
    print("\n" + "=" * 60)
    print("TESTING SIMPLE MECAB")
    print("=" * 60)
    
    try:
        import MeCab
        
        # Test with default MeCab (if available)
        tagger = MeCab.Tagger()
        result = tagger.parse("こんにちは")
        print(f"✅ Simple MeCab works: {result.strip()}")
        
        # Test with different formats
        formats = ["-Owakati", "-Ochasen", "-Oyomi"]
        test_word = "愛"
        
        for fmt in formats:
            try:
                tagger = MeCab.Tagger(fmt)
                result = tagger.parse(test_word)
                print(f"✅ Format {fmt}: {result.strip()}")
            except Exception as e:
                print(f"❌ Format {fmt} failed: {e}")
                
    except Exception as e:
        print(f"❌ Simple MeCab failed: {e}")

def main():
    """Main test function"""
    print("UNIDIC WORKING INTEGRATION TEST")
    print("=" * 60)
    
    test_mecab_simple()
    test_unidic_direct_access()
    test_alternative_mecab_config()
    test_simple_mecab()
    
    print("\n" + "=" * 60)
    print("UNIDIC INTEGRATION TEST COMPLETED")
    print("=" * 60)

if __name__ == "__main__":
    main()


