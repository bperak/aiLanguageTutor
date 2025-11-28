# CANDO Data Integrity Report

## Issue Analysis (2025-01-27)

### Problem Identified
The `jf_cando_clean.csv` file was severely corrupted with:
- **563 total lines** instead of the expected 604 (from source `cando.txt`)
- **548 duplicate empty entries** for row number "8"
- **Missing data** for many entries that should have been present

### Root Cause
The corruption occurred during the PDF extraction process in `make_jf_cando_csv.py`. The script's `fallback_fitz()` function had issues with:
1. Forward-fill logic for structural columns
2. Improper handling of multiline content
3. Buffer management in the flush() function

### Solution Implemented
1. **Created `regenerate_csv_from_cando.py`** - A new script that treats `cando.txt` as the authoritative source
2. **Used pandas for proper CSV parsing** instead of manual string manipulation
3. **Implemented data integrity verification** with comprehensive checks

### Results
- ✅ **603 clean entries** parsed from `cando.txt` 
- ✅ **604 total lines** in final CSV (including header)
- ✅ **No duplicate entries** found
- ✅ **No empty critical fields** detected
- ✅ **Data integrity verified** - source and output counts match

### Files Changed
- `cando/jf_cando_clean.csv` → **Replaced with clean data** (backed up corrupted version)
- `cando/jf_cando_clean_corrupted_backup.csv` → **Backup of corrupted file**
- `cando/jf_cando_regenerated.csv` → **Clean regenerated version**
- `cando/regenerate_csv_from_cando.py` → **New utility script**

### Data Structure Verified
```
Columns: No, 種別, 種類, レベル, 言語活動, カテゴリー, 第1トピック, JF Can-do (日本語), JF Can-do (English)
Total entries: 603 (plus header = 604 lines)
Source file: cando.txt (604 lines total)
Integrity: ✅ Perfect match
```

### Recommendations
1. **Use `cando.txt` as the single source of truth** for all cando data operations
2. **Run data integrity checks** before any major processing
3. **Consider updating `make_jf_cando_csv.py`** to fix the underlying PDF extraction issues
4. **Regular backup verification** to catch data corruption early

### Next Steps
- [ ] Update any scripts that depend on the CSV structure
- [ ] Verify graph generation works with clean data
- [ ] Test UI integration with corrected dataset

---
*Report generated: 2025-01-27*
*Status: ✅ RESOLVED*