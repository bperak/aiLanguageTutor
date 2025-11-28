# CanDo Vector Embeddings Documentation

## Overview

The CanDo Vector Embeddings system enables semantic similarity relationships between CanDoDescriptor nodes in Neo4j. This allows the system to connect Can-Dos beyond explicit prerequisites, supporting adaptive learning paths that reflect semantic relatedness.

## Architecture

### Components

1. **CanDoEmbeddingService** (`backend/app/services/cando_embedding_service.py`)
   - Service for generating and managing CanDoDescriptor embeddings
   - Handles embedding generation, similarity computation, and relationship creation

2. **Neo4j Vector Index** (`backend/migrations/create_cando_vector_index.cypher`)
   - Vector index for efficient similarity search
   - 1536 dimensions (OpenAI text-embedding-3-small)
   - Cosine similarity function

3. **Migration Scripts**
   - `resources/generate_cando_embeddings.py` - Generate embeddings for existing CanDoDescriptors
   - `resources/create_cando_similarity_relationships.py` - Create similarity relationships

## Data Model

### Neo4j Schema Changes

**New Property:**
- `CanDoDescriptor.descriptionEmbedding` - List[float] (1536 dimensions)
  - Stores vector embedding of combined descriptionEn + descriptionJa

**New Relationship:**
- `(:CanDoDescriptor)-[:SEMANTICALLY_SIMILAR]->(:CanDoDescriptor)`
  - Properties:
    - `similarity_score`: float - Cosine similarity value (0.0 to 1.0)
    - `source_level`: string - CEFR level of source CanDoDescriptor
    - `target_level`: string - CEFR level of target CanDoDescriptor
    - `source_topic`: string - Primary topic of source CanDoDescriptor
    - `target_topic`: string - Primary topic of target CanDoDescriptor
    - `source_skillDomain`: string - Skill domain of source CanDoDescriptor
    - `target_skillDomain`: string - Skill domain of target CanDoDescriptor
    - `cross_domain`: boolean - True if level/topic/skillDomain differ between nodes
    - `created_at`: datetime - Timestamp when relationship was created
    - `updated_at`: datetime - Timestamp when relationship was last updated

**New Index:**
- Vector index `cando_descriptor_embeddings` on `CanDoDescriptor.descriptionEmbedding`

## Configuration

### Environment Variables

- `OPENAI_API_KEY` or `GEMINI_API_KEY` - Required for generating embeddings
- `CANDO_SIMILARITY_THRESHOLD` - Minimum similarity score for creating relationships (default: 0.65)
- `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD` - Neo4j connection settings

### Settings

The similarity threshold can be configured in `backend/app/core/config.py`:

```python
CANDO_SIMILARITY_THRESHOLD: float = Field(
    default=0.65,
    description="Minimum similarity score for creating SEMANTICALLY_SIMILAR relationships"
)
```

## Usage

### 1. Create Vector Index

First, create the Neo4j vector index:

**Option A: Using the helper script (recommended)**
```powershell
# PowerShell (Windows)
python scripts\apply_cando_vector_index.py
```

**Option B: Using Neo4j Browser or cypher-shell**
```bash
# Using cypher-shell
cat backend/migrations/create_cando_vector_index.cypher | cypher-shell -u neo4j -p <password>
```

Or execute the Cypher file directly in Neo4j Browser.

### 2. Generate Embeddings for Existing CanDoDescriptors

Run the migration script to generate embeddings for all existing CanDoDescriptors:

```powershell
# PowerShell (Windows)
python resources\generate_cando_embeddings.py --batch-size 50 --provider openai
```

Options:
- `--batch-size`: Number of nodes to process at once (default: 50)
- `--provider`: AI provider for embeddings - `openai` or `gemini` (default: openai)
- `--skip-existing`: Skip nodes that already have embeddings (default: True)
- `--no-skip-existing`: Regenerate embeddings for all nodes
- `--dry-run`: Only report counts without generating embeddings

### 3. Create Similarity Relationships

After embeddings are generated, create similarity relationships:

```powershell
# PowerShell (Windows)
python resources\create_cando_similarity_relationships.py --threshold 0.65 --batch-size 100
```

Options:
- `--threshold`: Minimum similarity score to create relationships (default: 0.65)
- `--batch-size`: Number of relationships to create per batch (default: 100)
- `--dry-run`: Only report statistics without creating relationships

### 4. Using the Service in Code

```python
from app.services.cando_embedding_service import CanDoEmbeddingService
from app.db import get_neo4j_session

# Initialize service
service = CanDoEmbeddingService()

# Get Neo4j session
async with get_neo4j_session() as session:
    # Update embedding for a single CanDoDescriptor
    await service.update_cando_embedding(session, "JFまるごと:13")
    
    # Find similar CanDoDescriptors
    similar = await service.find_similar_candos(
        session,
        "JFまるごと:13",
        limit=10,
        similarity_threshold=0.65
    )
    
    # Update similarity relationships for a CanDoDescriptor
    count = await service.update_similarity_for_cando(
        session,
        "JFまるごと:13"
    )
```

## Embedding Generation

### Content Preparation

Embeddings are generated from combined description text:
- Format: `"English: {descriptionEn} | Japanese: {descriptionJa}"`
- If only one description exists, only that part is included
- At least one description (en or ja) must be present

### Embedding Model

- **Provider**: OpenAI (default) or Google Gemini
- **Model**: `text-embedding-3-small` (OpenAI) or `embedding-001` (Gemini)
- **Dimensions**: 1536 (OpenAI) or 768 (Gemini)
- **Note**: The system is configured for 1536 dimensions (OpenAI)

## Similarity Computation

### Algorithm

1. **Vector Index Search** (Primary Method)
   - Uses Neo4j vector index for efficient similarity search
   - Returns top-k similar nodes based on cosine similarity

2. **Manual Cosine Similarity** (Fallback)
   - Used when vector index is unavailable
   - Computes cosine similarity manually for all pairs
   - Less efficient but functional

### Similarity Threshold

- **Default**: 0.65 (configurable)
- **Range**: 0.0 to 1.0
- **Meaning**: 
  - 1.0 = Identical descriptions
  - 0.65 = Moderate semantic similarity
  - 0.0 = No similarity

### Domain Constraints

**No domain filtering** - Relationships are created based purely on semantic similarity, allowing cross-domain connections:
- Different CEFR levels (A1 ↔ A2)
- Different topics
- Different skill domains

This enables adaptive learning paths that connect semantically related concepts across traditional boundaries.

## Relationship Metadata

Each `SEMANTICALLY_SIMILAR` relationship includes rich metadata:

```cypher
MATCH (a:CanDoDescriptor)-[r:SEMANTICALLY_SIMILAR]->(b:CanDoDescriptor)
RETURN 
  a.uid AS source_uid,
  b.uid AS target_uid,
  r.similarity_score,
  r.source_level,
  r.target_level,
  r.source_topic,
  r.target_topic,
  r.cross_domain,
  r.created_at
```

This metadata enables:
- Filtering by domain boundaries in queries
- Understanding relationship context
- Tracking relationship creation/updates

## Querying Similar CanDoDescriptors

### Using Vector Index

```cypher
// Find similar CanDoDescriptors using vector index
MATCH (source:CanDoDescriptor {uid: "JFまるごと:13"})
WHERE source.descriptionEmbedding IS NOT NULL
CALL db.index.vector.queryNodes(
    'cando_descriptor_embeddings',
    10,
    source.descriptionEmbedding
)
YIELD node AS target, score
WHERE target.uid <> source.uid
  AND score >= 0.65
RETURN target.uid, target.descriptionEn, score
ORDER BY score DESC
```

### Using Relationships

```cypher
// Find similar CanDoDescriptors via relationships
MATCH (source:CanDoDescriptor {uid: "JFまるごと:13"})-[r:SEMANTICALLY_SIMILAR]->(target:CanDoDescriptor)
WHERE r.similarity_score >= 0.65
RETURN target.uid, target.descriptionEn, r.similarity_score, r.cross_domain
ORDER BY r.similarity_score DESC
LIMIT 10
```

### Filtering by Domain

```cypher
// Find similar CanDoDescriptors within same level
MATCH (source:CanDoDescriptor {uid: "JFまるごと:13"})-[r:SEMANTICALLY_SIMILAR]->(target:CanDoDescriptor)
WHERE r.source_level = r.target_level
  AND r.similarity_score >= 0.65
RETURN target.uid, target.descriptionEn, r.similarity_score
ORDER BY r.similarity_score DESC
```

## API Endpoint

### Find Similar CanDoDescriptors

**GET** `/api/v1/cando/similar`

Find semantically similar CanDoDescriptors using vector embeddings.

**Query Parameters:**
- `can_do_id` (required): CanDoDescriptor UID (e.g., "JFまるごと:13")
- `limit` (optional): Maximum number of results (1-50, default: 10)
- `similarity_threshold` (optional): Minimum similarity score (0.0-1.0, default: 0.65)

**Example Request:**
```bash
curl "http://localhost:8000/api/v1/cando/similar?can_do_id=JFまるごと:13&limit=5&similarity_threshold=0.7"
```

**Example Response:**
```json
{
  "can_do_id": "JFまるごと:13",
  "count": 5,
  "similar": [
    {
      "uid": "JFまるごと:14",
      "level": "A2",
      "topic": "旅行と交通",
      "skillDomain": "やりとり",
      "descriptionEn": "Can ask for directions",
      "descriptionJa": "道を尋ねることができる",
      "similarity": 0.85
    },
    ...
  ]
}
```

## Integration with Learning Paths

The semantic similarity relationships enable:

1. **Adaptive Learning Paths**
   - Suggest semantically related CanDoDescriptors beyond explicit prerequisites
   - Connect concepts across different topics/domains

2. **Content Discovery**
   - Find related learning materials based on semantic similarity
   - Suggest alternative approaches to the same learning goal

3. **Personalization**
   - Recommend CanDoDescriptors based on user's current learning context
   - Adapt to user's learning style and preferences

### Example: Enhancing Learning Path Service

Here's how to integrate semantic similarity into the learning path generation:

```python
from app.services.cando_embedding_service import CanDoEmbeddingService
from app.services.learning_path_service import LearningPathService

class EnhancedLearningPathService(LearningPathService):
    """Learning path service enhanced with semantic similarity."""
    
    def __init__(self):
        super().__init__()
        self.embedding_service = CanDoEmbeddingService()
    
    async def get_semantically_related_candos(
        self,
        neo4j_session,
        current_cando_uid: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get semantically related CanDoDescriptors for adaptive learning paths.
        
        This can be used to suggest alternative or complementary learning content
        beyond explicit prerequisites.
        """
        similar = await self.embedding_service.find_similar_candos(
            neo4j_session,
            current_cando_uid,
            limit=limit,
            similarity_threshold=0.65
        )
        
        return similar
    
    async def enhance_learning_path_with_similarity(
        self,
        db: AsyncSession,
        neo4j_session,
        user_id: uuid.UUID,
        base_cando_uid: str
    ) -> Dict[str, Any]:
        """
        Generate learning path that includes semantically related CanDoDescriptors.
        """
        # Get base CanDoDescriptor
        result = await neo4j_session.run(
            "MATCH (c:CanDoDescriptor {uid: $uid}) RETURN c",
            {"uid": base_cando_uid}
        )
        base_cando = await result.single()
        
        # Find semantically similar CanDoDescriptors
        similar = await self.get_semantically_related_candos(
            neo4j_session,
            base_cando_uid,
            limit=10
        )
        
        # Filter by user's level if needed
        # ... (add filtering logic)
        
        # Generate learning path including similar content
        # ... (integrate into path generation)
        
        return {
            "base_cando": base_cando_uid,
            "similar_candos": similar,
            "path": "..."  # Generated path
        }
```

### Using Relationships in Cypher Queries

You can also query relationships directly in learning path generation:

```cypher
// Find CanDoDescriptors similar to a completed one
MATCH (user:User {id: $user_id})-[:MASTERED]->(completed:CanDoDescriptor)
MATCH (completed)-[r:SEMANTICALLY_SIMILAR]->(similar:CanDoDescriptor)
WHERE r.similarity_score >= 0.65
  AND NOT (user)-[:MASTERED]->(similar)
  AND similar.level = $target_level
RETURN similar.uid, similar.descriptionEn, r.similarity_score
ORDER BY r.similarity_score DESC
LIMIT 10
```

## Performance Considerations

### Batch Processing

- Embeddings are generated in batches (default: 50 nodes)
- Relationships are created in batches (default: 100 relationships)
- Progress is logged every 50 items

### Rate Limiting

- Small delays (0.1s) between API calls to avoid rate limits
- Exponential backoff on errors (handled by EmbeddingService)

### Vector Index

- Vector index significantly improves similarity search performance
- Falls back to manual computation if index unavailable
- Index should be created before running similarity relationship script

## Maintenance

### Updating Embeddings

When a CanDoDescriptor is added or modified:

```python
# Automatically update embedding and relationships
service = CanDoEmbeddingService()
await service.update_cando_embedding(neo4j_session, can_do_uid)
await service.update_similarity_for_cando(neo4j_session, can_do_uid)
```

### Regenerating All Embeddings

To regenerate embeddings for all CanDoDescriptors:

```powershell
python resources\generate_cando_embeddings.py --no-skip-existing --batch-size 50
```

### Updating Relationships

To update similarity relationships with a new threshold:

```powershell
# First, delete existing relationships (optional)
# MATCH ()-[r:SEMANTICALLY_SIMILAR]->() DELETE r

# Then recreate with new threshold
python resources\create_cando_similarity_relationships.py --threshold 0.7 --batch-size 100
```

## Testing

Run tests for the embedding service:

```powershell
cd backend
poetry run pytest tests/test_cando_embedding_service.py -v
```

## Troubleshooting

### Vector Index Not Found

If you get errors about vector index not existing:
1. **Check Neo4j Version**: Ensure Neo4j version supports vector indexes (5.11+)
   - Vector indexes are available in Neo4j 5.11 and later
   - Check version: `CALL dbms.components() YIELD name, versions RETURN name, versions`
2. Run the migration script: `python scripts\apply_cando_vector_index.py`
3. Verify index exists: `SHOW INDEXES YIELD name WHERE name = 'cando_descriptor_embeddings'`
4. Check index state: `SHOW INDEXES YIELD name, state WHERE name = 'cando_descriptor_embeddings'`
   - State should be `ONLINE` for the index to be usable

### Low Similarity Scores

If relationships are not being created:
- Lower the threshold: `--threshold 0.5`
- Check that embeddings are generated correctly
- Verify descriptions are not empty

### API Rate Limits

If you encounter rate limit errors:
- Reduce batch size: `--batch-size 25`
- Add longer delays in the service code
- Use exponential backoff (already implemented)

## Important Notes

- **Neo4j Version Requirement**: Vector indexes require Neo4j 5.11 or later
- Embeddings are stored directly in Neo4j (not PostgreSQL)
- Relationships are unidirectional but can be queried in both directions
- Similarity threshold of 0.65 is a good starting point
- Can be lowered to 0.5 for more connections or raised to 0.7 for stricter matching
- Cross-domain connections enable adaptive learning paths
- The system includes a fallback mechanism if vector index is unavailable (uses manual cosine similarity)

## Future Enhancements

Potential improvements:
1. **Bidirectional Relationships**: Currently unidirectional, could be bidirectional
2. **Weighted Similarity**: Consider domain overlap in similarity computation
3. **Incremental Updates**: Only update relationships for changed CanDoDescriptors
4. **Similarity Clustering**: Group CanDoDescriptors into semantic clusters
5. **Multi-language Embeddings**: Separate embeddings for different languages

## References

- [Neo4j Vector Index Documentation](https://neo4j.com/docs/cypher-manual/current/indexes-for-vector-search/)
- [OpenAI Embeddings API](https://platform.openai.com/docs/guides/embeddings)
- [Google Gemini Embeddings](https://ai.google.dev/docs/embeddings)

