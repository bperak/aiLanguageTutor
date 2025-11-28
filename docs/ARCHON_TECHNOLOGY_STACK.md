# AI Language Tutor - Technology Stack and Dependencies

**Document ID**: `4ddb8916-1a71-4f14-9060-44201e867db6`  
**Type**: Specification Document  
**Author**: Development Team  
**Last Updated**: 2025-08-21  

## 🎯 Overview

This document provides a comprehensive overview of the technology stack, dependencies, versions, and configuration details for the AI Language Tutor project. It serves as the definitive reference for development, deployment, and maintenance activities.

## 🏗️ Architecture Stack Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    DEPLOYMENT LAYER                         │
├─────────────────────────────────────────────────────────────┤
│ Docker Compose (Dev) │ Google Cloud Run (Prod) │ GitHub Actions │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                   APPLICATION LAYER                         │
├─────────────────┬─────────────────┬─────────────────────────┤
│   Next.js 14+   │   FastAPI      │   Streamlit           │
│   Frontend      │   Backend      │   Validation          │
│   (TypeScript)  │   (Python)     │   (Python)            │
└─────────────────┴─────────────────┴─────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                     DATA LAYER                              │
├─────────────────────────────┬───────────────────────────────┤
│      PostgreSQL 15+         │         Neo4j AuraDB         │
│   (User Data, Conversations) │    (Knowledge Graph)        │
│      + pgvector             │    + Vector Indexes         │
└─────────────────────────────┴───────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                   AI SERVICES LAYER                         │
├─────────────────────────────┬───────────────────────────────┤
│        OpenAI APIs          │      Google Gemini APIs      │
│  GPT-4o, GPT-4o-mini       │   Gemini 2.5 Pro/Flash      │
│  o1-preview, o1-mini       │   + Google Cloud Speech      │
└─────────────────────────────┴───────────────────────────────┘
```

## 🖥️ Backend Technology Stack

### Core Framework
**FastAPI** - Modern, high-performance web framework
- **Version**: Latest (0.104.1+)
- **Python Version**: 3.11+
- **ASGI Server**: Uvicorn
- **Key Features**: Automatic API documentation, async support, type hints
- **Configuration**: Production-ready with proper error handling

### Database Technologies

#### PostgreSQL - Primary Database
- **Version**: PostgreSQL 15+
- **Extensions**: pgvector for vector embeddings
- **ORM**: SQLAlchemy 2.0+ with async support
- **Migrations**: Alembic for database schema management
- **Connection**: AsyncPG driver for optimal performance
- **Features**: Connection pooling, async operations, vector similarity search

**Key Dependencies**:
```toml
[tool.poetry.dependencies]
sqlalchemy = "^2.0.0"
alembic = "^1.12.0"
asyncpg = "^0.28.0"
pgvector = "^0.2.0"
```

#### Neo4j - Knowledge Graph Database
- **Version**: Neo4j 5.x (AuraDB cloud)
- **Driver**: Neo4j Python Driver 5.x
- **Query Language**: Cypher
- **Features**: Vector indexes, graph algorithms, relationship traversal
- **Performance**: Optimized for complex relationship queries

**Key Dependencies**:
```toml
[tool.poetry.dependencies]
neo4j = "^5.14.0"
```

### AI Service Integration

#### OpenAI Integration
- **Models**: GPT-4o, GPT-4o-mini, o1-preview, o1-mini
- **APIs**: Chat Completions, Embeddings
- **Library**: OpenAI Python SDK
- **Features**: Streaming responses, token usage tracking, error handling

**Dependencies**:
```toml
[tool.poetry.dependencies]
openai = "^1.3.0"
```

#### Google Gemini Integration
- **Models**: Gemini 2.5 Pro, Gemini 2.5 Flash
- **Library**: Google Generative AI SDK
- **Features**: Multimodal support, fast inference, cost optimization

**Dependencies**:
```toml
[tool.poetry.dependencies]
google-generativeai = "^0.3.0"
```

#### Google Cloud Services
- **Speech-to-Text**: Real-time speech recognition
- **Text-to-Speech**: High-quality voice synthesis
- **Authentication**: Service account credentials

**Dependencies**:
```toml
[tool.poetry.dependencies]
google-cloud-speech = "^2.21.0"
google-cloud-texttospeech = "^2.16.0"
```

### Natural Language Processing

#### Multi-Language NLP Support
- **Japanese**: GiNZA (spaCy-based Japanese NLP)
- **Korean**: KoNLPy (planned)
- **Chinese**: Jieba (planned)
- **South Slavic**: CLASSLA for Croatian/Serbian (planned)
- **European Languages**: spaCy models (planned)

**Current Dependencies**:
```toml
[tool.poetry.dependencies]
ginza = "^5.1.0"
spacy = "^3.7.0"
```

### Authentication & Security
- **JWT Tokens**: Python-JOSE for token handling
- **Password Hashing**: Passlib with bcrypt
- **CORS**: FastAPI CORS middleware
- **Environment**: Python-dotenv for configuration

**Dependencies**:
```toml
[tool.poetry.dependencies]
python-jose = {extras = ["cryptography"], version = "^3.3.0"}
passlib = {extras = ["bcrypt"], version = "^1.7.4"}
python-dotenv = "^1.0.0"
```

### Data Validation & Serialization
- **Pydantic**: Data validation and serialization
- **Type Hints**: Full type safety throughout the application
- **Schema Validation**: Request/response validation

**Dependencies**:
```toml
[tool.poetry.dependencies]
pydantic = "^2.5.0"
pydantic-settings = "^2.1.0"
```

### Development & Testing

#### Code Quality
- **Ruff**: Fast Python linter and formatter (replaces black, isort, flake8)
- **MyPy**: Static type checking
- **Pre-commit**: Git hooks for code quality

**Dependencies**:
```toml
[tool.poetry.group.dev.dependencies]
ruff = "^0.1.6"
mypy = "^1.7.0"
pre-commit = "^3.6.0"
```

#### Testing Framework
- **Pytest**: Testing framework with async support
- **Coverage**: Test coverage reporting
- **Fixtures**: Comprehensive test fixtures for database and API testing

**Dependencies**:
```toml
[tool.poetry.group.test.dependencies]
pytest = "^7.4.0"
pytest-asyncio = "^0.21.0"
pytest-cov = "^4.1.0"
httpx = "^0.25.0"  # For API testing
```

### Performance & Monitoring
- **Uvicorn**: High-performance ASGI server
- **Structured Logging**: JSON-based logging for production
- **Health Checks**: Comprehensive health monitoring endpoints

**Dependencies**:
```toml
[tool.poetry.dependencies]
uvicorn = {extras = ["standard"], version = "^0.24.0"}
structlog = "^23.2.0"
```

## 🌐 Frontend Technology Stack

### Core Framework
**Next.js 14+** - React-based full-stack framework
- **Version**: Next.js 14.0+
- **React Version**: React 18+
- **Router**: App Router (latest Next.js routing)
- **Rendering**: Server-side rendering (SSR) and static generation
- **Performance**: Automatic code splitting, image optimization

### Language & Type Safety
**TypeScript** - Typed JavaScript
- **Version**: TypeScript 5.0+
- **Configuration**: Strict mode enabled
- **Integration**: Full type safety across components and APIs
- **IDE Support**: Excellent development experience

### Styling & UI Components

#### Tailwind CSS
- **Version**: Tailwind CSS 3.3+
- **Configuration**: Custom design system
- **Features**: Responsive design, dark mode support, custom utilities
- **Performance**: Purged CSS for production builds

#### Shadcn/UI Components
- **Library**: Radix UI primitives with Tailwind styling
- **Components**: Comprehensive UI component library
- **Accessibility**: WCAG 2.1 AA compliant components
- **Customization**: Fully customizable design system

**Dependencies**:
```json
{
  "dependencies": {
    "next": "^14.0.0",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "typescript": "^5.0.0",
    "tailwindcss": "^3.3.0",
    "@radix-ui/react-accordion": "^1.1.2",
    "@radix-ui/react-alert-dialog": "^1.0.5",
    "@radix-ui/react-button": "^0.1.0",
    "class-variance-authority": "^0.7.0",
    "clsx": "^2.0.0",
    "tailwind-merge": "^2.0.0"
  }
}
```

### State Management

#### TanStack Query (React Query)
- **Version**: TanStack Query 5.0+
- **Purpose**: Server state management
- **Features**: Caching, background updates, optimistic updates
- **Performance**: Intelligent request deduplication

#### Zustand
- **Version**: Zustand 4.4+
- **Purpose**: Client state management
- **Features**: Simple API, TypeScript support, minimal boilerplate
- **Performance**: Lightweight and efficient

**Dependencies**:
```json
{
  "dependencies": {
    "@tanstack/react-query": "^5.0.0",
    "@tanstack/react-query-devtools": "^5.0.0",
    "zustand": "^4.4.0"
  }
}
```

### HTTP Client & API Integration
- **Axios**: HTTP client for API requests
- **Features**: Request/response interceptors, error handling
- **Configuration**: Base URL configuration, token management

**Dependencies**:
```json
{
  "dependencies": {
    "axios": "^1.6.0"
  }
}
```

### Form Handling & Validation
- **React Hook Form**: Performant forms with minimal re-renders
- **Zod**: TypeScript-first schema validation
- **Integration**: Seamless form validation with type safety

**Dependencies**:
```json
{
  "dependencies": {
    "react-hook-form": "^7.47.0",
    "@hookform/resolvers": "^3.3.0",
    "zod": "^3.22.0"
  }
}
```

### Icons & Assets
- **Lucide React**: Beautiful, customizable icons
- **Next.js Image**: Optimized image loading and rendering
- **Features**: Lazy loading, responsive images, format optimization

**Dependencies**:
```json
{
  "dependencies": {
    "lucide-react": "^0.292.0"
  }
}
```

### Development & Code Quality

#### ESLint & Prettier
- **ESLint**: JavaScript/TypeScript linting
- **Prettier**: Code formatting
- **Configuration**: Next.js recommended rules + custom rules
- **Integration**: VS Code integration, pre-commit hooks

**Dependencies**:
```json
{
  "devDependencies": {
    "eslint": "^8.54.0",
    "eslint-config-next": "^14.0.0",
    "eslint-config-prettier": "^9.0.0",
    "prettier": "^3.1.0",
    "prettier-plugin-tailwindcss": "^0.5.0"
  }
}
```

#### TypeScript Configuration
```json
{
  "compilerOptions": {
    "target": "es5",
    "lib": ["dom", "dom.iterable", "es6"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [{"name": "next"}],
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    }
  }
}
```

## 🛠️ Validation Interface Technology Stack

### Core Framework
**Streamlit** - Rapid web app development for data science
- **Version**: Streamlit 1.28+
- **Purpose**: Professional linguistic workbench
- **Features**: Interactive components, real-time updates, easy deployment
- **Integration**: Direct database connections, custom components

### Database Integration
- **Neo4j Integration**: Direct connection to knowledge graph
- **Query Interface**: Advanced Cypher query capabilities
- **Batch Operations**: Efficient bulk data processing
- **Performance**: Optimized for large dataset operations

**Dependencies**:
```txt
streamlit>=1.28.0
neo4j>=5.14.0
pandas>=2.0.0
plotly>=5.17.0
streamlit-aggrid>=0.3.4
```

### Data Processing & Visualization
- **Pandas**: Data manipulation and analysis
- **Plotly**: Interactive data visualization
- **Streamlit AgGrid**: Advanced data grid component
- **NumPy**: Numerical computing support

### Authentication & Security
- **Role-Based Access**: Native Speakers, Linguists, Teachers, QA
- **Session Management**: Streamlit session state
- **Security**: Environment-based configuration

## 🐳 Containerization & Deployment

### Docker Configuration

#### Multi-Stage Builds
- **Backend Dockerfile**: Optimized Python container
- **Frontend Dockerfile**: Node.js build with Nginx serving
- **Validation Dockerfile**: Streamlit application container

#### Docker Compose Development
```yaml
version: '3.8'
services:
  postgres:
    image: pgvector/pgvector:pg15
    environment:
      POSTGRES_DB: ailanguagetutor
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  neo4j:
    image: neo4j:5.14
    environment:
      NEO4J_AUTH: neo4j/password
      NEO4J_PLUGINS: '["apoc"]'
    ports:
      - "7474:7474"
      - "7687:7687"
    volumes:
      - neo4j_data:/data

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql+asyncpg://postgres:password@postgres/ailanguagetutor
      NEO4J_URI: bolt://neo4j:7687
    depends_on:
      - postgres
      - neo4j

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      NEXT_PUBLIC_API_BASE_URL: http://localhost:8000
    depends_on:
      - backend

  validation-ui:
    build: ./validation-ui
    ports:
      - "8501:8501"
    environment:
      NEO4J_URI: bolt://neo4j:7687
    depends_on:
      - neo4j
```

### Production Deployment (Planned)

#### Google Cloud Run
- **Backend**: Containerized FastAPI application
- **Frontend**: Static site deployment with CDN
- **Database**: Cloud SQL for PostgreSQL with pgvector
- **Knowledge Graph**: Neo4j AuraDB (managed service)

#### CI/CD Pipeline (GitHub Actions)
```yaml
name: CI/CD Pipeline
on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          cd backend
          pip install poetry
          poetry install
      - name: Run tests
        run: |
          cd backend
          poetry run pytest
      - name: Run linting
        run: |
          cd backend
          poetry run ruff check .
          poetry run mypy .

  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - name: Deploy to Google Cloud Run
        # Deployment steps
```

## 🔧 Development Tools & Configuration

### Code Quality Tools

#### Ruff Configuration (Python)
```toml
[tool.ruff]
target-version = "py311"
line-length = 88
select = [
    "E",  # pycodestyle errors
    "W",  # pycodestyle warnings
    "F",  # pyflakes
    "I",  # isort
    "B",  # flake8-bugbear
    "C4", # flake8-comprehensions
    "UP", # pyupgrade
]
ignore = [
    "E501",  # line too long, handled by formatter
    "B008",  # do not perform function calls in argument defaults
    "C901",  # too complex
]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
skip-magic-trailing-comma = false
line-ending = "auto"
```

#### ESLint Configuration (TypeScript)
```json
{
  "extends": [
    "next/core-web-vitals",
    "eslint:recommended",
    "@typescript-eslint/recommended",
    "prettier"
  ],
  "rules": {
    "@typescript-eslint/no-unused-vars": "error",
    "@typescript-eslint/no-explicit-any": "warn",
    "prefer-const": "error",
    "no-var": "error"
  }
}
```

### VS Code Configuration
```json
{
  "python.defaultInterpreterPath": "./backend/.venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.ruffEnabled": true,
  "python.formatting.provider": "ruff",
  "typescript.preferences.importModuleSpecifier": "relative",
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.fixAll.eslint": true,
    "source.organizeImports": true
  }
}
```

## 🔐 Environment Configuration

### Backend Environment Variables
```bash
# Database Configuration
DATABASE_URL=postgresql+asyncpg://user:password@localhost/ailanguagetutor
POSTGRES_USER=postgres
POSTGRES_PASSWORD=password
POSTGRES_DB=ailanguagetutor

# Neo4j Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=password

# AI Service APIs
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=AI...
GOOGLE_CLOUD_PROJECT_ID=your-project-id

# Authentication
JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# AI Routing Configuration
AI_ROUTING_CONFIG_DEFAULT_PROVIDER=openai
AI_ROUTING_CONFIG_FALLBACK_ENABLED=true
AI_ROUTING_CONFIG_COST_OPTIMIZATION=true

# Application Configuration
ENVIRONMENT=development
LOG_LEVEL=INFO
CORS_ORIGINS=["http://localhost:3000"]
```

### Frontend Environment Variables
```bash
# API Configuration
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000

# Build Configuration
NODE_ENV=development
```

## 📊 Performance & Monitoring

### Backend Performance
- **ASGI Server**: Uvicorn with optimal worker configuration
- **Database**: Connection pooling, query optimization
- **Caching**: Redis for session and API response caching (planned)
- **Monitoring**: Structured logging, health check endpoints

### Frontend Performance
- **Next.js Optimization**: Automatic code splitting, image optimization
- **Bundle Analysis**: Bundle size monitoring and optimization
- **Caching**: Browser caching, CDN integration
- **Performance Metrics**: Web Vitals monitoring

### Database Performance
- **PostgreSQL**: Proper indexing, query optimization, connection pooling
- **Neo4j**: Graph algorithm optimization, vector index tuning
- **Monitoring**: Query performance tracking, slow query analysis

## 🧪 Testing Strategy

### Backend Testing
- **Unit Tests**: Individual function and class testing
- **Integration Tests**: API endpoint testing with database
- **Performance Tests**: Load testing for critical endpoints
- **Security Tests**: Authentication and authorization testing

### Frontend Testing
- **Component Tests**: React component unit testing (planned)
- **E2E Tests**: End-to-end user flow testing (planned)
- **Visual Tests**: UI regression testing (planned)

### Test Data Management
- **Fixtures**: Comprehensive test data fixtures
- **Database**: Isolated test database instances
- **Mocking**: AI service mocking for consistent testing

## 🔄 Dependency Management

### Python Dependencies (Poetry)
```toml
[tool.poetry.dependencies]
python = "^3.11"
fastapi = "^0.104.1"
uvicorn = {extras = ["standard"], version = "^0.24.0"}
sqlalchemy = "^2.0.23"
alembic = "^1.13.0"
asyncpg = "^0.29.0"
pgvector = "^0.2.4"
neo4j = "^5.14.1"
openai = "^1.3.8"
google-generativeai = "^0.3.2"
pydantic = "^2.5.1"
python-jose = {extras = ["cryptography"], version = "^3.3.0"}
passlib = {extras = ["bcrypt"], version = "^1.7.4"}
python-dotenv = "^1.0.0"
ginza = "^5.1.3"

[tool.poetry.group.dev.dependencies]
ruff = "^0.1.6"
mypy = "^1.7.1"
pytest = "^7.4.3"
pytest-asyncio = "^0.21.1"
pytest-cov = "^4.1.0"
httpx = "^0.25.2"
```

### Node.js Dependencies (npm/yarn)
```json
{
  "dependencies": {
    "next": "^14.0.3",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "typescript": "^5.3.2",
    "@tanstack/react-query": "^5.8.4",
    "zustand": "^4.4.7",
    "axios": "^1.6.2",
    "tailwindcss": "^3.3.6",
    "lucide-react": "^0.294.0"
  },
  "devDependencies": {
    "eslint": "^8.54.0",
    "eslint-config-next": "^14.0.3",
    "prettier": "^3.1.0",
    "@types/node": "^20.10.0",
    "@types/react": "^18.2.39",
    "@types/react-dom": "^18.2.17"
  }
}
```

## 🚀 Deployment Readiness

### Production Checklist
- ✅ Environment variable configuration
- ✅ Docker containerization
- ✅ Database migration scripts
- ✅ Health check endpoints
- ✅ Logging and monitoring setup
- ✅ Security configuration
- 🔄 CI/CD pipeline setup (in progress)
- 🔄 Performance optimization (in progress)
- 🔄 Backup and disaster recovery (planned)

### Scalability Considerations
- **Horizontal Scaling**: Stateless application design
- **Database Scaling**: Read replicas, connection pooling
- **Caching**: Redis integration for performance
- **CDN**: Static asset optimization
- **Load Balancing**: Multiple application instances

---

**This technology stack provides a robust, scalable, and maintainable foundation for the AI Language Tutor platform, supporting current functionality and future expansion to multiple languages and advanced features.**
