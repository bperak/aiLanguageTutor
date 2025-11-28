# CanDo Embeddings Quick Start Guide

## Quick Setup (5 Steps)

### Step 1: Create Vector Index
```powershell
python scripts\apply_cando_vector_index.py
```

### Step 2: Generate Embeddings
```powershell
python resources\generate_cando_embeddings.py --batch-size 50 --provider openai
```

### Step 3: Create Similarity Relationships
```powershell
python resources\create_cando_similarity_relationships.py --threshold 0.65
```

### Step 4: Test API Endpoint
```bash
curl "http://localhost:8000/api/v1/cando/similar?can_do_id=JFまるごと:13&limit=5"
```

### Step 5: Validate Installation
```powershell
python scripts\validate_cando_embeddings.py
```

### Step 6: Query in Neo4j
```cypher
MATCH (a:CanDoDescriptor {uid: "JFまるごと:13"})-[r:SEMANTICALLY_SIMILAR]->(b:CanDoDescriptor)
RETURN b.uid, b.descriptionEn, r.similarity_score
ORDER BY r.similarity_score DESC
LIMIT 10
```

## Configuration

Add to `.env` (optional):
```
CANDO_SIMILARITY_THRESHOLD=0.65
```

## Troubleshooting

**No embeddings found?**
- Check that embeddings were generated: `MATCH (c:CanDoDescriptor) WHERE c.descriptionEmbedding IS NOT NULL RETURN count(c)`

**Vector index not found?**
- Run: `python scripts\apply_cando_vector_index.py`
- Verify: `SHOW INDEXES YIELD name WHERE name = 'cando_descriptor_embeddings'`

**Low similarity scores?**
- Lower threshold: `--threshold 0.5`
- Check descriptions are not empty

## Files Created

- `backend/app/services/cando_embedding_service.py` - Main service
- `backend/migrations/create_cando_vector_index.cypher` - Vector index migration
- `resources/generate_cando_embeddings.py` - Embedding generation script
- `resources/create_cando_similarity_relationships.py` - Relationship creation script
- `scripts/apply_cando_vector_index.py` - Helper script
- `scripts/validate_cando_embeddings.py` - Validation script
- `backend/tests/test_cando_embedding_service.py` - Tests
- `docs/CANDO_EMBEDDINGS.md` - Full documentation

## API Endpoint

**GET** `/api/v1/cando/similar?can_do_id={uid}&limit={n}&similarity_threshold={0.0-1.0}`

See `docs/CANDO_EMBEDDINGS.md` for full details.

