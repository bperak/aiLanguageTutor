# Lexical Relations Data Cleanup

## Overview

This document describes the cleanup process for `LEXICAL_RELATION` edges in Neo4j to address data quality issues.

## Issues Addressed

### 1. Duplicate Edges
**Problem**: Multiple `LEXICAL_RELATION` edges exist for the same `(source, target, relation_type)` combination.

**Solution**: Deduplication keeps the best edge based on:
1. Highest `confidence` value
2. If tied, highest `weight` value  
3. If tied, newest `created_utc` timestamp

**Cleanup Script**: See `backend/scripts/cleanup_lexical_relations.cypher` Step 2.

### 2. Self-Loops
**Problem**: Edges where `source.standard_orthography = target.standard_orthography` (same word pointing to itself).

**Solution**: All self-loops are deleted as they are invalid.

**Cleanup Script**: See `backend/scripts/cleanup_lexical_relations.cypher` Step 1.

### 3. Missing POS Data
**Problem**: Some `Word` nodes have `NULL` or empty `pos_primary`, causing the Relations UI to show missing POS information.

**Solution**: 
- The UI now displays "(unknown)" in yellow/italic when POS is missing
- Word nodes with missing `pos_primary` should be backfilled using the gap-fill service or dictionary import

**Note**: POS is not stored on relations; it's computed from `Word.pos_primary` in the API response.

### 4. Register Inconsistency
**Problem**: The same source word (e.g., `utsukushii`) may have different `register_source` values across different relations.

**Policy Decision**: **Edge-specific registers are kept** (Option A).

**Rationale**:
- Register can be contextual - the same word may have different register characteristics depending on the target word and usage context
- Example: `utsukushii` might be "formal" when paired with `tanrei` (端麗) but "neutral" when paired with `kirei` (きれい)
- This flexibility allows capturing nuanced semantic relationships

**No normalization is performed** - each edge maintains its own register values.

## Cleanup Process

### Running the Cleanup

Execute the Cypher script in Neo4j Browser or via cypher-shell:

```bash
docker-compose -f docker-compose.server.yml exec neo4j cypher-shell -u neo4j -p testpassword123 < backend/scripts/cleanup_lexical_relations.cypher
```

Or run individual steps:

1. **Remove self-loops**:
```cypher
MATCH (s:Word)-[r:LEXICAL_RELATION]->(t:Word)
WHERE s.standard_orthography = t.standard_orthography
DELETE r
RETURN count(*) AS deleted;
```

2. **Deduplicate**:
```cypher
MATCH (s:Word)-[r:LEXICAL_RELATION]->(t:Word)
WITH s.standard_orthography AS source, 
     t.standard_orthography AS target, 
     r.relation_type AS rel_type,
     collect(r) AS edges
WHERE size(edges) > 1
WITH source, target, rel_type, edges
UNWIND edges AS edge
WITH source, target, rel_type, edge,
     coalesce(edge.confidence, 0.0) AS conf,
     coalesce(edge.weight, 0.0) AS wgt,
     coalesce(edge.created_utc, datetime({year: 1970})) AS created
ORDER BY conf DESC, wgt DESC, created DESC
WITH source, target, rel_type, collect(edge) AS sorted_edges
WITH source, target, rel_type, sorted_edges[0] AS keep_edge, sorted_edges[1..] AS delete_edges
UNWIND delete_edges AS rel_to_delete
DELETE rel_to_delete
RETURN count(*) AS duplicates_deleted;
```

### Verification

After cleanup, verify:

1. **No self-loops remain**:
```cypher
MATCH (s:Word)-[r:LEXICAL_RELATION]->(t:Word)
WHERE s.standard_orthography = t.standard_orthography
RETURN count(*) AS remaining_self_loops;
```

2. **No duplicates remain**:
```cypher
MATCH (s:Word)-[r:LEXICAL_RELATION]->(t:Word)
WITH s.standard_orthography AS source, 
     t.standard_orthography AS target, 
     r.relation_type AS rel_type,
     count(*) AS cnt
WHERE cnt > 1
RETURN source, target, rel_type, cnt;
```

3. **Check for missing POS**:
```cypher
MATCH (s:Word)-[r:LEXICAL_RELATION]->(t:Word)
WHERE (s.pos_primary IS NULL OR s.pos_primary = '') 
   OR (t.pos_primary IS NULL OR t.pos_primary = '')
RETURN s.standard_orthography AS source, 
       t.standard_orthography AS target,
       s.pos_primary AS source_pos,
       t.pos_primary AS target_pos;
```

## Prevention

To prevent these issues in the future:

1. **Before creating relations**: Check if a relation already exists for `(source, target, relation_type)` and update instead of creating duplicate
2. **Self-loop check**: Validate `source != target` before creating edge
3. **POS validation**: Ensure Word nodes have `pos_primary` before creating relations (or backfill after)

## Related Files

- Cleanup script: `backend/scripts/cleanup_lexical_relations.cypher`
- API endpoint: `backend/app/api/v1/endpoints/lexical_network_admin.py` (relations_sample)
- UI component: `frontend/src/app/lexical/admin/page.tsx` (RelationsContent)
