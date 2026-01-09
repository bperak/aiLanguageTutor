# Lexical Network Builder - Next Steps Guide

## ✅ Implementation Complete

All core components have been implemented. Follow these steps to get the system running.

---

## Step 1: Install Dependencies

```bash
cd backend
poetry install
# OR if using pip:
pip install pandas
```

The new dependency `pandas` is required for dictionary import from Google Sheets.

---

## Step 2: Configure Environment Variables

Add to your `.env` file (if not already present):

```bash
# Required
OPENAI_API_KEY=your_openai_key
GEMINI_API_KEY=your_gemini_key

# Optional (for DeepSeek support)
DEEPSEEK_API_KEY=your_deepseek_key
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1

# Neo4j (should already be configured)
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password
```

---

## Step 3: Run Neo4j Migrations

### Option A: Using the Python Script (Recommended)

```bash
cd backend
python3 scripts/run_lexical_network_migrations.py
```

This script will:
- Connect to Neo4j
- Create all required indexes
- Verify the schema
- Show existing data statistics

### Option B: Manual Cypher Execution

In Neo4j Browser, execute:

```cypher
// Run the indexes migration
:source migrations/lexical_indexes.cypher
```

The schema file (`lexical_relations_schema.cypher`) is documentation only - the actual schema is created when you create the first LEXICAL_RELATION edge.

---

## Step 4: Verify API Endpoints

Start your backend server:

```bash
cd backend
uvicorn app.main:app --reload
```

Then test the endpoints:

```bash
# List available models
curl http://localhost:8000/api/v1/lexical-network/models

# Get network statistics
curl http://localhost:8000/api/v1/lexical-network/stats

# List jobs
curl http://localhost:8000/api/v1/lexical-network/jobs
```

Or use the test script:

```bash
python3 scripts/test_lexical_network_api.py
```

---

## Step 5: Test Relation Building

### Quick Test (Single Word)

```bash
# Build relations for a word (requires authentication)
curl -X POST "http://localhost:8000/api/v1/lexical-network/build-relations?word=美しい&relation_types=SYNONYM&model=gpt-4o-mini" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Create a Background Job

```bash
curl -X POST "http://localhost:8000/api/v1/lexical-network/jobs" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "job_type": "relation_building",
    "source": "pos_filter",
    "pos_filter": "形容詞",
    "relation_types": ["SYNONYM", "NEAR_SYNONYM"],
    "model": "gpt-4o-mini",
    "max_words": 10,
    "batch_size": 5
  }'
```

Then start the job:

```bash
curl -X POST "http://localhost:8000/api/v1/lexical-network/jobs/{job_id}/start" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

Check job status:

```bash
curl "http://localhost:8000/api/v1/lexical-network/jobs/{job_id}"
```

---

## Step 6: Import Dictionaries (Optional)

### Import Lee Dictionary

```bash
curl -X POST "http://localhost:8000/api/v1/lexical-network/import/lee-dict" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Import Matsushita Dictionary

```bash
curl -X POST "http://localhost:8000/api/v1/lexical-network/import/matsushita-dict" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Note:** These endpoints require the Google Sheets to be publicly accessible or you'll need to implement authentication.

---

## Step 7: Verify Data in Neo4j

Query the created relations:

```cypher
// Find relations created by a specific model
MATCH ()-[r:LEXICAL_RELATION]->()
WHERE r.ai_model = 'gpt-4o-mini'
RETURN count(r) AS count

// Find relations for adjectives
MATCH (w1:Word)-[r:LEXICAL_RELATION]->(w2:Word)
WHERE w1.pos_primary = '形容詞'
RETURN w1.standard_orthography, w2.standard_orthography, r.relation_type, r.weight, r.ai_model
ORDER BY r.weight DESC
LIMIT 10

// Check AI metadata
MATCH ()-[r:LEXICAL_RELATION]->()
WHERE r.ai_provider IS NOT NULL
RETURN r.ai_provider, r.ai_model, r.ai_temperature, 
       count(*) AS count, 
       avg(r.ai_cost_usd) AS avg_cost
ORDER BY count DESC
```

---

## Step 8: Programmatic Usage

See `scripts/example_lexical_network_usage.py` for examples:

```python
from app.services.lexical_network.relation_builder_service import RelationBuilderService
from app.schemas.lexical_network import JobConfig

# Create config
config = JobConfig(
    job_type="relation_building",
    source="word_list",
    word_list=["美しい"],
    relation_types=["SYNONYM", "NEAR_SYNONYM"],
    model="gpt-4o-mini",
)

# Build relations
builder = RelationBuilderService()
result = await builder.build_relations_for_word(neo4j_session, "美しい", config)
```

---

## Troubleshooting

### Issue: "No module named 'structlog'"
**Solution:** Activate your virtual environment:
```bash
cd backend
source venv/bin/activate  # or poetry shell
```

### Issue: "Neo4j connection failed"
**Solution:** 
1. Ensure Neo4j is running: `docker-compose up neo4j` (if using Docker)
2. Check `.env` has correct `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`

### Issue: "API endpoint returns 404"
**Solution:** 
1. Verify the router is registered in `app/api/v1/api.py`
2. Restart the FastAPI server
3. Check the route prefix: `/api/v1/lexical-network/*`

### Issue: "AI generation fails"
**Solution:**
1. Verify API keys are set in `.env`
2. Check API key validity
3. Ensure you have credits/quota
4. Check logs for specific error messages

### Issue: "Temperature not 0.0"
**Solution:** This should never happen - temperature is hardcoded to 0.0 in all providers. If you see this, it's a bug - check the provider implementation.

---

## Key Features to Test

1. **Temperature=0.0 Enforcement**
   - All AI calls should use temperature=0.0
   - Check `ai_temperature` field in Neo4j relations

2. **Multi-Provider Support**
   - Test with different models: `gpt-4o-mini`, `gemini-2.5-flash`, `deepseek-chat`
   - Verify metadata is stored correctly

3. **POS-Specific Relations**
   - Test with nouns (should get HYPERNYM, HYPONYM)
   - Test with adjectives (should get GRADABLE_ANTONYM, SCALAR_INTENSITY)
   - Test with verbs (should get CAUSATIVE_PAIR, CONVERSE)

4. **Metadata Tracking**
   - Verify all AI metadata fields are populated
   - Check cost calculations are reasonable
   - Verify request_id is unique

---

## Performance Tips

1. **Batch Processing**: Use background jobs for processing many words
2. **Model Selection**: Use `gpt-4o-mini` or `gemini-2.5-flash` for cost efficiency
3. **Confidence Filtering**: Set `min_confidence` to filter low-quality relations
4. **POS Filtering**: Process one POS at a time for better organization

---

## Next Development Steps

1. **Frontend Admin Dashboard**: Create React/Next.js admin UI
2. **Clustering Analysis**: Implement HDBSCAN for edge clustering
3. **Centrality Measures**: Add PageRank, betweenness centrality
4. **Quality Metrics**: Track relation quality over time
5. **Export/Import**: Add JSON export for relations

---

## Support

For issues or questions:
1. Check the test files: `tests/test_lexical_network_builder.py`
2. Review the build status: `LEXICAL_NETWORK_BUILD_STATUS.md`
3. Check Neo4j logs for database issues
4. Check FastAPI logs for API issues
