# Network Generation Updates for POS Normalization

## Summary
Updated all network generation code to use canonical POS fields (`pos_primary_norm`, `pos1`) with fallback to legacy `pos_primary` for backward compatibility.

## Files Updated

### 1. `relation_builder_service.py`
**Changes:**
- **Line 144**: Updated `_fetch_word_data()` to fetch canonical POS:
  ```cypher
  coalesce(w.pos_primary_norm, w.pos1, w.pos_primary, "名詞") AS pos_primary
  ```
- **Line 174**: Updated `_get_embedding_candidates()` to filter by canonical POS:
  ```cypher
  WHERE ($pos_filter IS NULL OR coalesce(target.pos_primary_norm, target.pos1, target.pos_primary) = $pos_filter)
  ```
- **Line 178**: Updated to return canonical POS in results
- **Line 357**: Updated adjective POS set to include "形状詞" (UniDic canonical format)

### 2. `word_resolution.py`
**Changes:**
- **Line 267**: Updated query to filter by canonical POS:
  ```cypher
  AND ($expected_pos IS NULL OR coalesce(w.pos_primary_norm, w.pos1, w.pos_primary) IN $expected_pos)
  ```
- **Line 273**: Updated to return canonical POS:
  ```cypher
  coalesce(w.pos_primary_norm, w.pos1, w.pos_primary) AS pos_primary
  ```
- **Lines 135, 168, 210**: Updated to use canonical POS from query results (already canonical)

### 3. `job_manager_service.py`
**Changes:**
- **Line 409**: Updated POS filter to use canonical POS:
  ```cypher
  where_clauses.append("coalesce(w.pos_primary_norm, w.pos1, w.pos_primary) = $pos")
  ```

### 4. `relation_types.py`
**Changes:**
- **Line 69**: Added "形状詞" to `POS_TO_RELATIONS` mapping (UniDic canonical format for na-adjectives)
- **Lines 115, 123, 131, 139**: Added "形状詞" to universal relation `applicable_pos` lists
- **Lines 211, 219, 227, 235**: Added "形状詞" to adjective relation `applicable_pos` lists
- **Line 317**: Updated docstring to mention "形状詞" format

## Benefits

1. **Consistent POS Usage**: All network generation now uses canonical UniDic POS format
2. **Backward Compatible**: Falls back to legacy `pos_primary` for words without canonical POS
3. **Better Matching**: Canonical format improves word resolution accuracy
4. **Future-Proof**: Supports POS hierarchy (pos1-pos4) for future enhancements
5. **Format Support**: Handles both legacy ("形容動詞") and canonical ("形状詞") na-adjective formats

## Testing Recommendations

1. Test network generation with words that have:
   - Canonical POS only (pos_primary_norm/pos1)
   - Legacy POS only (pos_primary)
   - Both canonical and legacy POS
   
2. Test adjective matching with:
   - "形容詞" (i-adjectives)
   - "形状詞" (na-adjectives - UniDic canonical)
   - "形容動詞" (na-adjectives - legacy format)

3. Verify POS filtering in job manager works correctly

4. Test word resolution with various POS combinations
