"""
fix_cando_csv.py
================
Fix the corrupted jf_cando_clean.csv by properly parsing cando.txt

The current CSV has data corruption with 548 duplicate empty entries for row 8.
This script will create a clean CSV from the source cando.txt file.
"""

import csv
import re
from typing import List, Dict, Any


def parse_cando_txt(file_path: str) -> List[Dict[str, Any]]:
    """
    Parse the cando.txt file and extract structured data.
    
    Args:
        file_path (str): Path to the cando.txt file
        
    Returns:
        List[Dict[str, Any]]: List of parsed cando entries
    """
    entries = []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Skip the header line
    header_line = lines[0].strip()
    print(f"Header: {header_line}")
    
    # Process each data line
    for line_num, line in enumerate(lines[1:], start=2):
        line = line.strip()
        if not line:
            continue
            
        # Split the line by comma, handling quoted fields
        # This is a simple CSV parser that handles the format we see
        fields = []
        current_field = ""
        in_quotes = False
        
        i = 0
        while i < len(line):
            char = line[i]
            
            if char == '"' and (i == 0 or line[i-1] == ','):
                # Start of quoted field
                in_quotes = True
            elif char == '"' and in_quotes and (i == len(line)-1 or line[i+1] == ','):
                # End of quoted field
                in_quotes = False
            elif char == ',' and not in_quotes:
                # Field separator
                fields.append(current_field)
                current_field = ""
                i += 1
                continue
            else:
                current_field += char
            
            i += 1
        
        # Add the last field
        fields.append(current_field)
        
        # Clean up fields - remove quotes if present
        cleaned_fields = []
        for field in fields:
            field = field.strip()
            if field.startswith('"') and field.endswith('"'):
                field = field[1:-1]  # Remove surrounding quotes
            cleaned_fields.append(field)
        
        # Ensure we have exactly 10 fields as per the header
        if len(cleaned_fields) >= 10:
            entry = {
                'No': cleaned_fields[0],
                '種別': cleaned_fields[1], 
                '種類': cleaned_fields[2],
                'レベル': cleaned_fields[3],
                '言語活動': cleaned_fields[4],
                '第1カテゴリー': cleaned_fields[5],
                'トピック': cleaned_fields[6],
                'JF': cleaned_fields[7],
                'Can-do (日本語)': cleaned_fields[8],
                'JF_en': cleaned_fields[9] if len(cleaned_fields) > 9 else '',
                'Can-do (English)': cleaned_fields[10] if len(cleaned_fields) > 10 else ''
            }
            entries.append(entry)
        else:
            print(f"Warning: Line {line_num} has {len(cleaned_fields)} fields, expected 10+")
            print(f"Line content: {line[:100]}...")
    
    return entries


def create_clean_csv(entries: List[Dict[str, Any]], output_path: str):
    """
    Create a clean CSV file from the parsed entries.
    
    Args:
        entries (List[Dict[str, Any]]): Parsed cando entries
        output_path (str): Path for the output CSV file
    """
    # Define the output column order matching the expected format
    columns = [
        "No", "種別", "種類", "レベル", "言語活動", 
        "カテゴリー", "第1トピック", 
        "JF Can-do (日本語)", "JF Can-do (English)"
    ]
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        
        # Write header
        writer.writerow(columns)
        
        # Write data rows
        for entry in entries:
            row = [
                entry.get('No', ''),
                entry.get('種別', ''),
                entry.get('種類', ''),
                entry.get('レベル', ''),
                entry.get('言語活動', ''),
                entry.get('第1カテゴリー', ''),  # Map to カテゴリー
                entry.get('トピック', ''),       # Map to 第1トピック
                entry.get('Can-do (日本語)', ''),
                entry.get('Can-do (English)', '')
            ]
            writer.writerow(row)
    
    print(f"✅ Created clean CSV with {len(entries)} entries: {output_path}")


def main():
    """Main function to fix the cando CSV data."""
    input_file = "cando/cando.txt"
    output_file = "cando/jf_cando_fixed.csv"
    
    print("🔍 Parsing cando.txt...")
    entries = parse_cando_txt(input_file)
    
    print(f"📊 Found {len(entries)} entries")
    
    # Show first few entries for verification
    if entries:
        print("\n📋 First entry:")
        for key, value in entries[0].items():
            print(f"  {key}: {value}")
    
    print(f"\n🔧 Creating clean CSV...")
    create_clean_csv(entries, output_file)
    
    print(f"\n✅ Done! Check {output_file} for the cleaned data.")


if __name__ == "__main__":
    main()