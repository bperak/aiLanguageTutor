"""
regenerate_csv_from_cando.py
=============================
Regenerate a clean CSV from cando.txt as the authoritative source.

This script properly parses the cando.txt file and creates a clean CSV 
that matches the expected format for the cando system.
"""

import csv
import pandas as pd
from pathlib import Path


def parse_cando_txt_properly(file_path: str) -> list:
    """
    Parse cando.txt file properly, treating it as the authoritative source.
    
    Returns:
        List of parsed entries
    """
    entries = []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        # Read all lines
        lines = f.readlines()
    
    print(f"📁 Total lines in cando.txt: {len(lines)}")
    
    # The first line is the header
    header = lines[0].strip()
    print(f"📋 Header: {header}")
    
    # Split header to understand column structure
    header_cols = header.split(',')
    print(f"📊 Header columns ({len(header_cols)}): {header_cols}")
    
    # Process each data line (skip header)
    for line_num, line in enumerate(lines[1:], start=2):
        line = line.strip()
        if not line:
            continue
        
        # Parse CSV line properly using pandas
        try:
            # Use pandas to parse the CSV line properly
            from io import StringIO
            
            # Create a small CSV with header and this line
            csv_content = header + '\n' + line
            df = pd.read_csv(StringIO(csv_content))
            
            if len(df) > 0:
                row = df.iloc[0]
                
                # Create entry with standardized column names
                entry = {
                    'No': str(row.iloc[0]) if pd.notna(row.iloc[0]) else '',
                    '種別': str(row.iloc[1]) if pd.notna(row.iloc[1]) else '',
                    '種類': str(row.iloc[2]) if pd.notna(row.iloc[2]) else '',
                    'レベル': str(row.iloc[3]) if pd.notna(row.iloc[3]) else '',
                    '言語活動': str(row.iloc[4]) if pd.notna(row.iloc[4]) else '',
                    '第1カテゴリー': str(row.iloc[5]) if pd.notna(row.iloc[5]) else '',
                    'トピック': str(row.iloc[6]) if pd.notna(row.iloc[6]) else '',
                    'JF': str(row.iloc[7]) if pd.notna(row.iloc[7]) else '',
                    'Can-do (日本語)': str(row.iloc[8]) if pd.notna(row.iloc[8]) else '',
                    'JF_en': str(row.iloc[9]) if len(row) > 9 and pd.notna(row.iloc[9]) else '',
                    'Can-do (English)': str(row.iloc[10]) if len(row) > 10 and pd.notna(row.iloc[10]) else ''
                }
                
                entries.append(entry)
                
        except Exception as e:
            print(f"⚠️  Error parsing line {line_num}: {e}")
            print(f"   Line content: {line[:100]}...")
            continue
    
    print(f"✅ Successfully parsed {len(entries)} entries")
    return entries


def create_standardized_csv(entries: list, output_path: str):
    """
    Create a clean, standardized CSV file.
    
    Args:
        entries: List of parsed entries
        output_path: Output file path
    """
    # Define standard column order matching expected format
    output_columns = [
        "No", "種別", "種類", "レベル", "言語活動", 
        "カテゴリー", "第1トピック", 
        "JF Can-do (日本語)", "JF Can-do (English)"
    ]
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        
        # Write header
        writer.writerow(output_columns)
        
        # Write data rows
        for entry in entries:
            row = [
                entry.get('No', '').replace('nan', ''),
                entry.get('種別', '').replace('nan', ''),
                entry.get('種類', '').replace('nan', ''),
                entry.get('レベル', '').replace('nan', ''),
                entry.get('言語活動', '').replace('nan', ''),
                entry.get('第1カテゴリー', '').replace('nan', ''),  # Maps to カテゴリー
                entry.get('トピック', '').replace('nan', ''),       # Maps to 第1トピック
                entry.get('Can-do (日本語)', '').replace('nan', ''),
                entry.get('Can-do (English)', '').replace('nan', '')
            ]
            writer.writerow(row)
    
    print(f"✅ Created standardized CSV: {output_path}")
    print(f"📊 Total entries: {len(entries)}")


def verify_data_integrity(original_file: str, csv_file: str):
    """
    Verify data integrity between source and CSV.
    """
    print(f"\n🔍 Data Integrity Check:")
    
    # Count original lines (excluding header)
    with open(original_file, 'r', encoding='utf-8') as f:
        original_lines = len([line for line in f.readlines()[1:] if line.strip()])
    
    # Count CSV lines (excluding header)
    df = pd.read_csv(csv_file)
    csv_entries = len(df)
    
    print(f"📄 Original file entries: {original_lines}")
    print(f"📊 CSV file entries: {csv_entries}")
    
    if original_lines == csv_entries:
        print("✅ Data integrity verified - counts match!")
    else:
        print(f"⚠️  Count mismatch: {original_lines - csv_entries} entries lost/gained")
    
    # Check for duplicates
    duplicate_nos = df[df.duplicated(subset=['No'], keep=False)]['No'].unique()
    if len(duplicate_nos) > 0:
        print(f"⚠️  Found {len(duplicate_nos)} duplicate No. values: {duplicate_nos}")
    else:
        print("✅ No duplicate entries found")
    
    # Check for empty critical fields
    empty_no = df[df['No'].isna() | (df['No'] == '')].shape[0]
    empty_japanese = df[df['JF Can-do (日本語)'].isna() | (df['JF Can-do (日本語)'] == '')].shape[0]
    
    print(f"📋 Empty 'No' fields: {empty_no}")
    print(f"📋 Empty Japanese Can-do fields: {empty_japanese}")


def main():
    """Main function to regenerate CSV from cando.txt."""
    input_file = "cando/cando.txt"
    output_file = "cando/jf_cando_regenerated.csv"
    
    # Verify input file exists
    if not Path(input_file).exists():
        print(f"❌ Input file not found: {input_file}")
        return
    
    print("🚀 Regenerating CSV from cando.txt...")
    print("=" * 50)
    
    # Parse the source file
    entries = parse_cando_txt_properly(input_file)
    
    if not entries:
        print("❌ No entries found!")
        return
    
    # Show sample entry for verification
    print(f"\n📋 Sample entry (first):")
    for key, value in entries[0].items():
        print(f"  {key}: {value[:100]}{'...' if len(str(value)) > 100 else ''}")
    
    # Create clean CSV
    print(f"\n🔧 Creating standardized CSV...")
    create_standardized_csv(entries, output_file)
    
    # Verify integrity
    verify_data_integrity(input_file, output_file)
    
    print(f"\n🎉 Done! Clean CSV created: {output_file}")
    print(f"🔄 You can now replace the corrupted jf_cando_clean.csv with this file.")


if __name__ == "__main__":
    main()