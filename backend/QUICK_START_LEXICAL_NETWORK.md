# Quick Start - Lexical Network Builder

## 🚀 Get Started in 5 Minutes

### 1. Install Dependencies
```bash
cd backend
poetry install  # Installs pandas if needed
```

### 2. Run Migrations
```bash
python3 scripts/run_lexical_network_migrations.py
```

### 3. Test the API
```bash
# Start server
uvicorn app.main:app --reload

# In another terminal, test endpoints
curl http://localhost:8000/api/v1/lexical-network/models
```

### 4. Build Your First Relations

**Option A: Quick Build (Single Word)**
```bash
curl -X POST "http://localhost:8000/api/v1/lexical-network/build-relations?word=美しい&relation_types=SYNONYM&model=gpt-4o-mini" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Option B: Background Job (Multiple Words)**
```bash
# Create job
JOB_ID=$(curl -X POST "http://localhost:8000/api/v1/lexical-network/jobs" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "job_type": "relation_building",
    "source": "pos_filter",
    "pos_filter": "形容詞",
    "relation_types": ["SYNONYM"],
    "model": "gpt-4o-mini",
    "max_words": 5
  }' | jq -r '.job_id')

# Start job
curl -X POST "http://localhost:8000/api/v1/lexical-network/jobs/$JOB_ID/start" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Check status
curl "http://localhost:8000/api/v1/lexical-network/jobs/$JOB_ID"
```

### 5. Verify in Neo4j
```cypher
// Check created relations
MATCH ()-[r:LEXICAL_RELATION]->()
WHERE r.ai_provider IS NOT NULL
RETURN r.ai_provider, r.ai_model, r.ai_temperature, count(*) AS count
ORDER BY count DESC
```

---

## ✅ What's Working

- ✅ **Temperature = 0.0** - All AI calls use deterministic temperature
- ✅ **Multi-Provider** - OpenAI, Gemini, DeepSeek supported
- ✅ **Metadata Tracking** - Full AI generation metadata stored
- ✅ **POS-Specific** - Different relation types for nouns/adjectives/verbs/adverbs
- ✅ **Background Jobs** - Process multiple words asynchronously
- ✅ **Admin API** - 12+ endpoints for control and monitoring

---

## 📖 Full Documentation

- **Next Steps**: `LEXICAL_NETWORK_NEXT_STEPS.md`
- **Build Status**: `LEXICAL_NETWORK_BUILD_STATUS.md`
- **Implementation Summary**: `LEXICAL_NETWORK_IMPLEMENTATION_SUMMARY.md`

---

## 🎯 Example: Build Relations for Adjectives

```python
from app.services.lexical_network.relation_builder_service import RelationBuilderService
from app.schemas.lexical_network import JobConfig
from app.db import get_neo4j_session

config = JobConfig(
    job_type="relation_building",
    source="pos_filter",
    pos_filter="形容詞",
    relation_types=["SYNONYM", "NEAR_SYNONYM", "GRADABLE_ANTONYM"],
    model="gpt-4o-mini",
    max_words=10,
)

builder = RelationBuilderService()
async for session in get_neo4j_session():
    # Process words...
    break
```

---

**Status: Ready to use!** 🎉
