# CanDo Embeddings - Usage Examples

## Python Code Examples

### Basic Usage

```python
from app.services.cando_embedding_service import CanDoEmbeddingService
from app.db import get_neo4j_session

# Initialize service
service = CanDoEmbeddingService()

# Get Neo4j session
async with get_neo4j_session() as session:
    # Find similar CanDoDescriptors
    similar = await service.find_similar_candos(
        session,
        "JFまるごと:13",
        limit=10,
        similarity_threshold=0.65
    )
    
    for item in similar:
        print(f"{item['uid']}: {item['descriptionEn']} (similarity: {item['similarity']:.2f})")
```

### Update Embedding for New CanDoDescriptor

```python
# When a new CanDoDescriptor is created or modified
async with get_neo4j_session() as session:
    # Update embedding
    success = await service.update_cando_embedding(
        session,
        "JFまるごと:13",
        provider="openai"
    )
    
    if success:
        # Update similarity relationships
        count = await service.update_similarity_for_cando(
            session,
            "JFまるごと:13"
        )
        print(f"Created {count} similarity relationships")
```

### Batch Processing

```python
# Generate embeddings for all CanDoDescriptors
async with get_neo4j_session() as session:
    stats = await service.batch_generate_cando_embeddings(
        session,
        batch_size=50,
        provider="openai",
        skip_existing=True
    )
    
    print(f"Processed: {stats['processed']}")
    print(f"Generated: {stats['generated']}")
    print(f"Errors: {stats['errors']}")
```

## Cypher Query Examples

### Find Similar CanDoDescriptors

```cypher
// Using vector index (fast)
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
// Find via SEMANTICALLY_SIMILAR relationships
MATCH (source:CanDoDescriptor {uid: "JFまるごと:13"})-[r:SEMANTICALLY_SIMILAR]->(target:CanDoDescriptor)
WHERE r.similarity_score >= 0.65
RETURN target.uid, target.descriptionEn, r.similarity_score, r.cross_domain
ORDER BY r.similarity_score DESC
LIMIT 10
```

### Filter by Domain

```cypher
// Find similar within same level
MATCH (source:CanDoDescriptor {uid: "JFまるごと:13"})-[r:SEMANTICALLY_SIMILAR]->(target:CanDoDescriptor)
WHERE r.source_level = r.target_level
  AND r.similarity_score >= 0.65
RETURN target.uid, target.descriptionEn, r.similarity_score
ORDER BY r.similarity_score DESC
```

### Find Cross-Domain Connections

```cypher
// Find similar CanDoDescriptors across different domains
MATCH (source:CanDoDescriptor {uid: "JFまるごと:13"})-[r:SEMANTICALLY_SIMILAR]->(target:CanDoDescriptor)
WHERE r.cross_domain = true
  AND r.similarity_score >= 0.70
RETURN 
  target.uid,
  target.descriptionEn,
  r.source_level + " → " + r.target_level AS level_change,
  r.source_topic + " → " + r.target_topic AS topic_change,
  r.similarity_score
ORDER BY r.similarity_score DESC
```

### Learning Path with Similarity

```cypher
// Find next CanDoDescriptors based on completed ones and similarity
MATCH (user:User {id: $user_id})-[:MASTERED]->(completed:CanDoDescriptor)
MATCH (completed)-[r:SEMANTICALLY_SIMILAR]->(next:CanDoDescriptor)
WHERE r.similarity_score >= 0.65
  AND NOT (user)-[:MASTERED]->(next)
  AND next.level IN ["A1", "A2"]  // User's target level
RETURN DISTINCT next.uid, next.descriptionEn, r.similarity_score
ORDER BY r.similarity_score DESC
LIMIT 20
```

## API Usage Examples

### Find Similar CanDoDescriptors

```bash
# Basic request
curl "http://localhost:8000/api/v1/cando/similar?can_do_id=JFまるごと:13"

# With custom limit and threshold
curl "http://localhost:8000/api/v1/cando/similar?can_do_id=JFまるごと:13&limit=5&similarity_threshold=0.7"
```

### JavaScript/TypeScript Example

```typescript
// Frontend usage
async function findSimilarCanDos(canDoId: string, limit: number = 10) {
  const response = await fetch(
    `/api/v1/cando/similar?can_do_id=${encodeURIComponent(canDoId)}&limit=${limit}`
  );
  const data = await response.json();
  return data.similar;
}

// Usage
const similar = await findSimilarCanDos("JFまるごと:13", 5);
similar.forEach(item => {
  console.log(`${item.uid}: ${item.descriptionEn} (${item.similarity.toFixed(2)})`);
});
```

## Integration Patterns

### Pattern 1: Suggest Next Steps

```python
async def suggest_next_candos(
    neo4j_session,
    user_id: str,
    completed_cando_uid: str
):
    """Suggest next CanDoDescriptors based on completed one."""
    service = CanDoEmbeddingService()
    
    # Find similar CanDoDescriptors
    similar = await service.find_similar_candos(
        neo4j_session,
        completed_cando_uid,
        limit=10
    )
    
    # Filter by user's level and exclude completed
    # ... (add filtering logic)
    
    return similar
```

### Pattern 2: Content Discovery

```python
async def discover_related_content(
    neo4j_session,
    current_cando_uid: str,
    user_interests: List[str]
):
    """Discover related content based on semantic similarity."""
    service = CanDoEmbeddingService()
    
    # Find similar CanDoDescriptors
    similar = await service.find_similar_candos(
        neo4j_session,
        current_cando_uid,
        limit=20
    )
    
    # Filter by user interests (topics, domains)
    # ... (add filtering logic)
    
    return similar
```

### Pattern 3: Adaptive Learning Path

```python
async def generate_adaptive_path(
    neo4j_session,
    starting_cando_uid: str,
    target_level: str
):
    """Generate learning path using semantic similarity."""
    service = CanDoEmbeddingService()
    path = [starting_cando_uid]
    visited = {starting_cando_uid}
    
    current = starting_cando_uid
    while len(path) < 10:  # Limit path length
        # Find similar CanDoDescriptors
        similar = await service.find_similar_candos(
            neo4j_session,
            current,
            limit=5
        )
        
        # Filter by target level and not visited
        candidates = [
            s for s in similar
            if s['level'] == target_level and s['uid'] not in visited
        ]
        
        if not candidates:
            break
        
        # Select best candidate
        next_cando = candidates[0]
        path.append(next_cando['uid'])
        visited.add(next_cando['uid'])
        current = next_cando['uid']
    
    return path
```

