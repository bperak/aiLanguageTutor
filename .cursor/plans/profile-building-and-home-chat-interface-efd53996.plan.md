<!-- efd53996-2ae8-48fd-8ae3-6565d1d5eb0f 668ee3b9-1117-40e2-914e-1fe119376201 -->
# Enrich AI Chat Sessions with PostgreSQL and pgvector

## Research Summary

Based on Context7 documentation for pgvector, Supabase Vecs, and pg_vectorize, here are the key patterns for enriching AI chat sessions:

### Core Capabilities

1. **Vector Storage for Chat History**

   - Store embeddings of chat messages in PostgreSQL
   - Use `vector(1536)` type for OpenAI embeddings or `vector(384)` for smaller models
   - Associate embeddings with metadata (user_id, session_id, timestamp, message_type)

2. **Semantic Search on Past Conversations**

   - Find similar past conversations using cosine distance (`<=>`) or L2 distance (`<->`)
   - Filter by user_id, session_id, or other metadata
   - Retrieve relevant context from past interactions

3. **Hybrid Search (Vector + Full-Text)**

   - Combine pgvector similarity search with PostgreSQL full-text search (tsvector)
   - Use reciprocal rank fusion to merge results
   - Better than either approach alone

4. **RAG (Retrieval-Augmented Generation)**

   - Retrieve relevant past conversations/knowledge before generating response
   - Inject retrieved context into AI system prompt
   - Provide personalized, context-aware responses

### Implementation Patterns

**Pattern 1: Store Chat Message Embeddings**

```sql
-- Add vector column to conversation_messages table
ALTER TABLE conversation_messages 
ADD COLUMN embedding vector(1536);

-- Create index for similarity search
CREATE INDEX ON conversation_messages 
USING hnsw (embedding vector_cosine_ops);
```

**Pattern 2: Semantic Search on Past Conversations**

```sql
-- Find similar past messages for context
SELECT content, role, created_at, 
       embedding <=> $query_embedding AS similarity
FROM conversation_messages
WHERE user_id = $user_id 
  AND session_id != $current_session_id
  AND role = 'user'
ORDER BY embedding <=> $query_embedding
LIMIT 5;
```

**Pattern 3: Hybrid Search**

```sql
-- Combine vector search with full-text search
WITH vector_search AS (
    SELECT id, content, embedding <=> $query_embedding AS distance
    FROM conversation_messages
    WHERE user_id = $user_id
    ORDER BY distance LIMIT 10
),
text_search AS (
    SELECT id, content, ts_rank_cd(textsearch, query) AS rank
    FROM conversation_messages, plainto_tsquery($query_text) query
    WHERE textsearch @@ query AND user_id = $user_id
    LIMIT 10
)
-- Merge with reciprocal rank fusion
SELECT COALESCE(v.id, t.id) AS id,
       1.0 / (60 + COALESCE(v.rank, 1000)) + 1.0 / (60 + COALESCE(t.rank, 1000)) AS score
FROM vector_search v
FULL OUTER JOIN text_search t ON v.id = t.id
ORDER BY score DESC
LIMIT 5;
```

**Pattern 4: Filtered Vector Search**

```sql
-- Search with metadata filters
SELECT content, embedding <=> $query_embedding AS distance
FROM conversation_messages
WHERE user_id = $user_id
  AND created_at > NOW() - INTERVAL '30 days'
  AND session_type = 'home'
ORDER BY distance
LIMIT 5;
```

## Implementation Plan

### Phase 1: Database Schema Updates

- Add `embedding vector(1536)` column to `conversation_messages` table
- Create HNSW index on embedding column
- Add `textsearch tsvector` column for hybrid search
- Create GIN index on textsearch column

### Phase 2: Embedding Generation Service

- Create service to generate embeddings for messages (using existing OpenAI/Google GenAI)
- Store embeddings when messages are created
- Batch processing for existing messages

### Phase 3: Semantic Search Service

- Create service to search past conversations using pgvector
- Support filtering by user_id, session_type, time range
- Implement hybrid search (vector + full-text)

### Phase 4: RAG Integration

- Modify `stream_assistant_reply` to:
  - Generate embedding for user's current message
  - Search for similar past conversations
  - Inject retrieved context into system prompt
  - Enhance AI responses with relevant history

### Phase 5: User-Specific Context Enhancement

- Build user conversation profiles from embeddings (average vectors)
- Track learning patterns and preferences
- Personalize responses based on conversation history

## Files to Modify

1. **Database Migrations**: Add vector columns and indexes
2. **`backend/app/services/embedding_service.py`**: Extend to handle chat message embeddings
3. **`backend/app/services/conversation_service.py`**: Add semantic search methods
4. **`backend/app/api/v1/endpoints/conversations.py`**: Integrate RAG into streaming endpoint
5. **`backend/app/models/database_models.py`**: Add embedding field to ConversationMessage model

## Benefits

- **Context Awareness**: AI can reference past conversations
- **Personalization**: Responses tailored to user's learning history
- **Knowledge Retention**: System remembers what user has discussed
- **Better Recommendations**: Suggest next steps based on past interactions
- **Learning Progress Tracking**: Identify patterns in user's learning journey

### To-dos

- [x] Update HomeChatInterface.tsx to handle SSE event: error lines and display user-friendly error messages
- [x] Fix database session transaction handling in conversations.py event_generator to properly rollback before commit
- [x] Add detailed exception logging in conversations.py event_generator exception handler
- [x] Review and fix get_postgresql_session dependency in db.py to handle pending rollbacks