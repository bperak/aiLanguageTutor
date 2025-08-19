# 🎓 AI Language Tutor

An intelligent, personalized multi-language learning platform that combines graph-based knowledge representation with AI-powered tutoring and voice interaction. Starting with Japanese, expanding to Korean, Mandarin, Spanish, and beyond.

## 🌟 Vision

Create a "living brain" for language learning that understands connections between concepts, cultural contexts, and adapts to each learner's unique journey across multiple languages and cultures.

## 🏗️ Architecture

### System Components

- **PostgreSQL Database** - The "Memory Center" (user data, conversations, embeddings)
- **Universal Knowledge Graph (Neo4j)** - The "Multi-Lingual Brain"
- **Backend API (FastAPI)** - The "Nervous System"
- **Frontend (Next.js)** - The "Body"
- **Human Tutor Interface (Streamlit)** - The "Linguistic Workbench"
- **Voice Services (Google Cloud)** - The "Voice"

### Technology Stack

**Backend:**
- FastAPI (Python 3.11+)
- PostgreSQL with pgvector (Conversations, embeddings)
- Neo4j AuraDB (Knowledge graph)
- Multi-Provider AI (OpenAI GPT-4o, Google Gemini 2.5)
- JWT Authentication

**Frontend:**
- Next.js 14+ with App Router
- TypeScript + Tailwind CSS
- Shadcn/UI Components
- TanStack Query + Zustand

**Validation Interface:**
- Streamlit (Professional linguistic workbench)
- Advanced content validation tools
- Multi-reviewer collaborative workflow

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- Node.js 18+ (for local frontend development)
- Python 3.11+ (for local backend development)
- Neo4j AuraDB account (free tier)
- OpenAI API key
- Google Gemini API key

### 1. Environment Setup

```bash
# Clone the repository
git clone <repository-url>
cd aiLanguageTutor

# Create .env with required variables
# On Windows PowerShell, edit manually:
#   - Create a file named `.env` in project root
#   - Copy the keys from `.env.template` (see repo) and fill them
# Important: Do not commit your real keys
```

### 2. Generate JWT Secret Key

```bash
# Generate a secure JWT secret key
openssl rand -hex 32

# Add the generated key to your .env file as JWT_SECRET_KEY
```

### 3. Start Development Environment

```bash
# Start all services with Docker Compose
docker-compose up -d

# Wait for services to be healthy (check with: docker-compose ps)
# This will start:
# - Backend API: http://localhost:8000
# - Frontend: http://localhost:3000  
# - Validation UI: http://localhost:8501
# - PostgreSQL: localhost:5432
# - Neo4j: localhost:7474 (browser) & 7687 (bolt)
```

### 4. Verify Installation

- **Backend API**: Visit http://localhost:8000/docs for API documentation
- **Frontend**: Visit http://localhost:3000 for the main application
- **Validation Interface**: Visit http://localhost:8501 for content validation
- **Health Check**: Visit http://localhost:8000/health
- **Neo4j Browser**: Visit http://localhost:7474 for knowledge graph exploration

### 5. Run Tests

```bash
# Run all tests (requires backend to be healthy)
.\scripts\run_tests.ps1
```

## 🌐 Current API Endpoints (Phase 2)

### Health & Status
- `GET /health` - Basic health check
- `GET /api/v1/health` - API health check
- `GET /api/v1/health/detailed` - Detailed health with database connectivity

### Authentication
- `POST /api/v1/auth/register` - User registration
- `POST /api/v1/auth/login` - User login
- `GET /api/v1/auth/me` - Get current user profile
- `PUT /api/v1/auth/profile` - Update user profile
- `POST /api/v1/auth/change-password` - Change password
- `POST /api/v1/auth/deactivate` - Deactivate account
- `GET /api/v1/auth/verify-token` - Verify JWT token

### Conversations
- `POST /api/v1/conversations/sessions` - Create conversation session
- `GET /api/v1/conversations/sessions` - List user sessions
- `GET /api/v1/conversations/sessions/{session_id}` - Get session details
- `POST /api/v1/conversations/sessions/{session_id}/messages` - Add message to session
- `GET /api/v1/conversations/sessions/{session_id}/messages` - List session messages

### Knowledge Graph
- `GET /api/v1/knowledge/health` - Knowledge graph health check
- `GET /api/v1/knowledge/search` - Search knowledge graph
- `GET /api/v1/knowledge/embeddings/status` - Check embeddings status

### Content Analysis
- `POST /api/v1/content/analyze` - Analyze text content
- `POST /api/v1/content/analyze-url` - Analyze content from URL
- `POST /api/v1/content/analyze-upload` - Analyze uploaded file
- `POST /api/v1/content/analyze-persist` - Analyze and persist to Neo4j
- `GET /api/v1/content/term` - Verify persisted term in Neo4j

### Learning & Personalization
- `GET /api/v1/learning/dashboard` - Get personalized learning dashboard
- `GET /api/v1/learning/diagnostic/quiz` - Get diagnostic quiz
- `POST /api/v1/learning/diagnostic/grade` - Grade quiz responses

### Spaced Repetition System (SRS)
- `POST /api/v1/srs/schedule` - Schedule SRS review

### Analytics
- `GET /api/v1/analytics/summary` - Get conversation analytics summary

### Admin & RBAC
- `GET /api/v1/admin/health` - Admin health check (requires admin role)

## 📁 Project Structure

```
aiLanguageTutor/
├── backend/                  # FastAPI application
│   ├── app/
│   │   ├── main.py          # FastAPI app instance
│   │   ├── api/v1/          # API endpoints
│   │   ├── core/            # Configuration & security
│   │   └── db.py            # Database connections
│   ├── Dockerfile
│   └── pyproject.toml       # Poetry dependencies
├── frontend/                # Next.js application
│   ├── src/
│   │   ├── app/             # App Router pages
│   │   ├── components/      # React components
│   │   └── lib/             # Utilities
│   ├── Dockerfile
│   └── package.json
├── validation-ui/           # Streamlit validation interface
│   ├── main.py              # Streamlit app
│   ├── Dockerfile
│   └── requirements.txt
├── tests/                   # Test suite
│   ├── test_*.py           # Individual test files
│   └── _helpers.py         # Test utilities
├── scripts/                 # Utility scripts
│   └── run_tests.ps1       # Test execution script
├── docker-compose.yml       # Development environment
├── .env.template           # Environment variables template
└── README.md               # This file
```

## 🔧 Development

### Backend Development

```bash
cd backend

# Install dependencies with Poetry
poetry install

# Run backend locally (with hot reloading)
poetry run uvicorn app.main:app --reload --port 8000

# Run tests
poetry run pytest

# Code formatting
poetry run ruff format .
poetry run ruff check . --fix
```

### Frontend Development

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev

# Build for production
npm run build

# Lint code
npm run lint

#### Environment

Set the API base URL for the frontend via environment variable in `.env`:

```
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

Note: Update your local `.env` manually as needed; the file is not committed.

#### Conversation AI Replies

Assistant replies in conversations are generated using real provider APIs configured in backend `.env`:

```
OPENAI_API_KEY=...
GEMINI_API_KEY=...
AI_ROUTING_CONFIG_DEFAULT_PROVIDER=openai
```

The backend uses these keys via `app.core.config.settings`. Conversation sessions store `ai_provider` and `ai_model`; replies use those values. If AI generation fails, the user message is still stored, and the endpoint returns without an assistant reply.

See `.env.template` in the repo for a complete list of variables required. Remember to create and maintain your `.env` locally.
```

### Validation Interface Development

```bash
cd validation-ui

# Install dependencies
pip install -r requirements.txt

# Run Streamlit app
streamlit run main.py --server.port=8501
```

## 🌐 API Documentation

Once the backend is running, visit:
- **Interactive API Docs**: http://localhost:8000/docs
- **ReDoc Documentation**: http://localhost:8000/redoc

## 🧪 Testing

### Backend Tests
```bash
# Run all tests
.\scripts\run_tests.ps1

# Or run specific test files
cd backend
poetry run pytest tests/test_health_endpoints.py
poetry run pytest tests/test_auth_smoke.py
poetry run pytest tests/test_content_persist_neo4j.py
```

### Test Coverage
The test suite includes:
- ✅ Health endpoint tests
- ✅ Authentication flow tests
- ✅ Conversation management tests
- ✅ Content analysis tests
- ✅ Knowledge graph integration tests
- ✅ Learning dashboard tests
- ✅ SRS scheduling tests
- ✅ Analytics tests
- ✅ Admin RBAC tests

## 🔒 Security

- JWT authentication for API access
- Environment variables for sensitive data
- CORS configuration for cross-origin requests
- Rate limiting and request validation
- Secure database connections

## 📊 Monitoring & Logging

- Structured logging with structlog
- Health check endpoints
- Database connection monitoring
- AI provider performance tracking

## 🌍 Multi-Language Support

Currently supporting:
- 🇯🇵 Japanese (Primary)

Planned expansions:
- 🇰🇷 Korean
- 🇨🇳 Mandarin Chinese
- 🇭🇷 Croatian
- 🇷🇸 Serbian
- 🇪🇸 Spanish
- 🇫🇷 French
- 🇩🇪 German

## 🤝 Contributing

1. Follow the development workflow in `PLANNING.md`
2. Check `TASK.md` for current tasks and priorities
3. Use conventional commit messages
4. Ensure all tests pass before submitting PRs
5. Follow code quality standards (Ruff for Python, ESLint for TypeScript)

## 📚 Documentation

- `PLANNING.md` - Complete project architecture and development phases
- `TASK.md` - Current tasks and progress tracking
- `AI_ARCHITECTURE.md` - AI provider integration details
- `CONTENT_ANALYSIS_SYSTEM.md` - Content analysis system design
- `HUMAN_TUTOR_ENHANCEMENTS.md` - Validation interface features

## 🆘 Troubleshooting

### Common Issues

**Docker Services Won't Start:**
```bash
# Check if ports are available
lsof -i :3000,8000,8501,8080

# Clean up Docker resources
docker-compose down -v
docker system prune -f
```

**Backend Connection Issues:**
```bash
# Check backend status
docker-compose ps

# View backend logs
docker-compose logs backend

# Restart backend
docker-compose restart backend
```

**Test Failures:**
```bash
# Ensure backend is healthy before running tests
docker-compose ps

# Wait for backend to be healthy, then run tests
.\scripts\run_tests.ps1
```

**Database Connection Issues:**
- Verify Neo4j AuraDB credentials in `.env`
- Check network connectivity to Neo4j instance
- Ensure PostgreSQL container is running

**Missing Environment Variables:**
- Copy `.env.template` to `.env`
- Fill in all required API keys and database credentials
- Restart Docker containers after updating `.env`

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🎯 Development Status

**Current Phase**: Phase 3 - Frontend (The Body)  
**Progress**: 🚧 In Progress - Minimal auth and dashboard UI added

### Phase 2 Achievements:
- ✅ Complete authentication system with JWT
- ✅ Conversation management with sessions and messages
- ✅ Knowledge graph integration and search
- ✅ Content analysis with multi-item extraction
- ✅ Neo4j persistence for analyzed content
- ✅ Learning dashboard and diagnostic quiz
- ✅ Spaced Repetition System (SRS)
- ✅ Analytics and conversation insights
- ✅ Role-Based Access Control (RBAC)
- ✅ Comprehensive test suite (22 tests passing)

**Next Phase**: Phase 3 - Frontend (The Body)

See `TASK.md` for detailed progress tracking and next steps.

---

**Built with ❤️ for language learners worldwide**