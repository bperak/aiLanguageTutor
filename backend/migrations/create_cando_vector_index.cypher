// Create vector index for CanDoDescriptor embeddings
// This enables efficient similarity search using Neo4j's vector index capabilities

// Drop existing index if it exists (for re-running migration)
DROP INDEX cando_descriptor_embeddings IF EXISTS;

// Create vector index for CanDoDescriptor.descriptionEmbedding
// Dimensions: 1536 (OpenAI text-embedding-3-small)
// Similarity function: cosine
CREATE VECTOR INDEX cando_descriptor_embeddings
FOR (c:CanDoDescriptor)
ON c.descriptionEmbedding
OPTIONS {
  indexConfig: {
    `vector.dimensions`: 1536,
    `vector.similarity_function`: 'cosine'
  }
};

// Verify index creation
SHOW INDEXES YIELD name, type, state
WHERE name = 'cando_descriptor_embeddings';

