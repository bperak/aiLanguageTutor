# AI Language Tutor Backend

FastAPI backend application for the AI Language Tutor platform.

## Features

- Multi-provider AI integration (OpenAI + Google GenAI)
- Neo4j graph database integration
- PostgreSQL with pgvector for vector embeddings
- JWT authentication
- Comprehensive API documentation

## Development

```bash
# Install dependencies
poetry install

# Run development server
poetry run uvicorn app.main:app --reload

# Run tests
poetry run pytest
```
