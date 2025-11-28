# AI Language Tutor - Project Architecture Overview

**Document ID**: `20526421-0647-4edb-920d-3ac10bb5bb0e`  
**Type**: Specification Document  
**Author**: Development Team  
**Last Updated**: 2025-08-21  

## 🎯 1. Project Overview

### Vision
An intelligent, personalized multi-language learning platform that combines graph-based knowledge representation with AI-powered tutoring and voice interaction.

### Core Philosophy
Create a "living brain" for language learning that understands connections between concepts, cultural contexts, and adapts to each learner's unique journey across multiple languages and cultures.

### Target Languages
- **Primary**: Japanese (Current focus)
- **Phase 1 Expansion**: Korean, Mandarin Chinese
- **Phase 2 Expansion**: Croatian, Serbian  
- **Phase 3 Expansion**: Spanish, French, German

### Core Principles
1. **Graph-based Knowledge Representation**: Complex relationships between concepts
2. **Multi-provider AI Integration**: Intelligent routing between OpenAI and Google Gemini
3. **Human-in-the-loop Validation**: Professional linguistic review workflow
4. **Personalized Learning Paths**: Adaptive algorithms based on user progress
5. **Cultural Context Integration**: Beyond language - cultural understanding

## 🏗️ 2. System Architecture

### Microservices Architecture Overview
The system follows a microservices approach with clear separation of concerns:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Next.js       │    │    FastAPI      │    │   Streamlit     │
│   Frontend      │◄──►│    Backend      │◄──►│   Validation    │
│   (The Body)    │    │(Nervous System) │    │  (Workbench)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       ▼                       │
         │              ┌─────────────────┐               │
         │              │   PostgreSQL    │               │
         │              │ (Memory Center) │               │
         │              └─────────────────┘               │
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 ▼
                        ┌─────────────────┐
                        │     Neo4j       │
                        │(Multi-Lingual   │
                        │     Brain)      │
                        └─────────────────┘
                                 ▲
                        ┌─────────────────┐
                        │ Google Cloud    │
                        │ Voice Services  │
                        │  (The Voice)    │
                        └─────────────────┘
```

### Component Details

#### 2.1 PostgreSQL Database - "Memory Center"
**Role**: Central repository for user data and conversation management

**Responsibilities**:
- User accounts, profiles, and authentication data
- Conversation history and chat sessions (60+ endpoint coverage)
- Learning progress and statistics tracking
- User preferences and settings
- Session management and activity logs

**Technologies**:
- PostgreSQL 15+ with pgvector extension
- SQLAlchemy ORM with async support
- Alembic for database migrations
- Connection pooling for performance

**Key Tables**:
- `users` - Authentication and preferences
- `conversation_sessions` - Session metadata and AI configuration
- `conversation_messages` - Individual messages with AI metadata
- `conversation_interactions` - Learning interactions and SRS data
- `conversation_analytics` - Performance metrics and insights

#### 2.2 Neo4j Knowledge Graph - "Multi-Lingual Brain"
**Role**: Semantic knowledge representation and relationship modeling

**Responsibilities**:
- Cross-language lexical knowledge and concept mapping
- Language-specific grammatical structures and relationships
- Universal learning patterns and cultural contexts
- Complex relationship modeling between concepts

**Technologies**:
- Neo4j AuraDB (cloud-hosted)
- Vector indexes for semantic search
- Cypher queries for complex relationship traversal
- Graph algorithms for learning path optimization

**Data Volume**:
- NetworkX Import: 60,958 nodes, 128,487 edges (synonym relationships)
- Lee's Vocabulary: 17,921 entries (Japanese learning vocabulary)
- Grammar Points: Comprehensive Japanese grammar structure

**Key Node Types**:
- `GrammarPoint` - Language grammar concepts
- `Vocabulary` - Lexical knowledge with semantic relationships
- `CulturalContext` - Cultural learning scenarios
- `LearningPath` - Structured learning progressions
- `Source` - Content attribution and references

#### 2.3 FastAPI Backend - "Nervous System"
**Role**: Central API orchestration and business logic

**Responsibilities**:
- RESTful API with 22+ endpoints
- JWT authentication and authorization
- Advanced personalization algorithms
- Spaced Repetition System (SRS) implementation
- Voice processing integration coordination
- Conversation management and storage

**Technologies**:
- FastAPI with Python 3.11+
- Uvicorn ASGI server
- Pydantic for data validation
- JWT tokens with passlib for authentication
- Multi-provider AI routing system

**API Endpoint Categories**:
- Authentication (7 endpoints): Registration, login, profile management
- Conversations (5 endpoints): Session and message management
- Knowledge Graph (3 endpoints): Search and embeddings
- Content Analysis (4 endpoints): Text/URL/file analysis with Neo4j persistence
- Learning (3 endpoints): Dashboard, diagnostic quiz, grading
- Analytics (1 endpoint): Conversation insights
- Admin (1 endpoint): RBAC functionality

**Testing Coverage**: 22 comprehensive tests covering all major functionality

#### 2.4 Next.js Frontend - "Body"
**Role**: User interface and experience layer

**Responsibilities**:
- Modern React-based UI with TypeScript
- Real-time data fetching with TanStack Query
- Responsive design with Tailwind CSS + Shadcn/UI
- Voice interaction capabilities
- Real-time conversation interface with streaming

**Technologies**:
- Next.js 14+ with App Router
- TypeScript for type safety
- Tailwind CSS + Shadcn/UI components
- TanStack Query for server state management
- Zustand for client state management
- Web Audio APIs for voice integration

**Key Features Implemented**:
- Authentication UI (login/register)
- Real-time conversation interface with streaming responses
- Learning dashboard with analytics visualization
- Content analysis interface
- SRS review interface
- Responsive design for all screen sizes

#### 2.5 Streamlit Validation Interface - "Linguistic Workbench"
**Role**: Professional content validation and quality assurance

**Responsibilities**:
- Professional-grade validation and content creation tools
- Advanced linguistic analysis workbench with morphological tools
- Collaborative multi-reviewer workflow with peer consultation
- AI-human learning loop with feedback analytics
- Cultural appropriateness and pedagogical effectiveness validators

**Technologies**:
- Streamlit for rapid UI development
- Direct Neo4j integration with advanced querying
- Batch operations and smart content prioritization
- Role-based access control

**Status**: Currently in development (partial implementation)

**Planned Features**:
- Pending reviews dashboard with smart prioritization
- Detailed review screen with AI-generated content display
- Validation actions (Approve/Edit & Approve/Reject)
- Multi-reviewer workflow with peer consultation
- Quality metrics and performance tracking

#### 2.6 Google Cloud Voice Services - "Voice"
**Role**: Speech processing and pronunciation guidance

**Responsibilities**:
- Speech-to-Text for practice exercises
- Text-to-Speech for pronunciation guidance
- Voice-based practice exercises
- Audio playback and recording

**Technologies**:
- Google Cloud Speech-to-Text API
- Google Cloud Text-to-Speech API
- Web Audio APIs (MediaRecorder, Audio)
- Cross-browser compatibility

**Status**: Planned for Phase 4 implementation

## 🛠️ 3. Technology Stack

### 3.1 Backend Technologies
- **Framework**: FastAPI (Python 3.11+)
- **Databases**: 
  - PostgreSQL with pgvector (conversations, embeddings)
  - Neo4j AuraDB (knowledge graph, vector indexes)
- **ORM**: SQLAlchemy with Alembic for migrations
- **AI Services**: 
  - OpenAI: GPT-4o, GPT-4o-mini, o1-preview, o1-mini
  - Google Gemini: 2.5 Pro, 2.5 Flash
  - Voice: Google Cloud Speech/TTS
- **AI Architecture**: Multi-provider unified interface with automatic model routing
- **NLP Libraries**: 
  - Japanese: GiNZA
  - Korean: KoNLPy (planned)
  - Chinese: Jieba (planned)
  - South Slavic: CLASSLA (Croatian/Serbian, planned)
  - European: spaCy (planned)
- **Authentication**: JWT tokens with passlib
- **Testing**: Pytest with 22 comprehensive tests
- **Code Quality**: Ruff for linting and formatting

### 3.2 Frontend Technologies
- **Framework**: Next.js 14+ with App Router
- **Language**: TypeScript with strict mode
- **Styling**: Tailwind CSS + Shadcn/UI components
- **State Management**: 
  - Client State: Zustand
  - Server State: TanStack Query
- **Audio**: Web APIs (MediaRecorder, Audio)
- **Code Quality**: ESLint + Prettier

### 3.3 Validation Interface
- **Framework**: Streamlit (Professional linguistic workbench)
- **Purpose**: Advanced content validation, creation, and collaborative review
- **Database**: Direct Neo4j integration with advanced querying
- **Authentication**: Role-based access (Native Speakers, Linguists, Teachers, QA)

### 3.4 Development & Deployment
- **Code Quality**: Ruff (Python), ESLint + Prettier (TypeScript)
- **Dependency Management**: Poetry (Python), npm/yarn (Node.js)
- **Containerization**: Docker + Docker Compose
- **CI/CD**: GitHub Actions
- **Monitoring**: Structured logging, health check endpoints
- **Deployment**: Google Cloud Run (planned)

## 📊 4. Current Status

### 4.1 Completed Phases

#### Phase 2 - Core API (The Nervous System) ✅ COMPLETE
**Completion Date**: 2024-12-28  
**Status**: All endpoints implemented and tested

**Achievements**:
- ✅ Authentication System: Registration, login, JWT tokens, profile management
- ✅ Conversation Management: Sessions, messages, metadata, threading
- ✅ Knowledge Graph Integration: Neo4j connectivity, search, embeddings
- ✅ Content Analysis System: Text/URL/file analysis with Neo4j persistence
- ✅ Learning & Personalization: Dashboard, diagnostic quiz, progress tracking
- ✅ Spaced Repetition System: Scheduling, intervals, ease factors
- ✅ Analytics & Insights: Conversation analytics, user activity tracking
- ✅ Admin & RBAC: Role-based access control, security validation
- ✅ Testing & QA: 22 comprehensive tests, Docker containerization

#### Phase 3 - Frontend (The Body) ✅ COMPLETE
**Completion Date**: 2025-01-15  
**Status**: Minimal but functional UI implemented

**Achievements**:
- ✅ Next.js 14+ Setup: App Router, TypeScript, Tailwind CSS
- ✅ Authentication UI: Login/register screens with form validation
- ✅ Conversation Interface: Real-time chat with streaming responses
- ✅ Learning Dashboard: Analytics visualization, progress tracking
- ✅ Content Analysis Interface: Text input and analysis results
- ✅ SRS Review Interface: Spaced repetition practice
- ✅ Responsive Design: Mobile-friendly layouts
- ✅ Error Handling: Global toasts, loading states, skeletons

### 4.2 In Progress

#### Streamlit Validation Interface 🚧
**Status**: Partial implementation  
**Priority**: High  
**Remaining Work**:
- Advanced linguistic analysis tools
- Multi-reviewer workflow with peer consultation
- AI-human learning loop with feedback analytics
- Quality metrics and performance tracking

#### Knowledge Graph Data Import 🚧
**Status**: Scripts ready, execution needed  
**Priority**: High  
**Data Ready**:
- NetworkX synonym graph (60,958 nodes, 128,487 edges)
- Lee's vocabulary database (17,921 entries)
- Import orchestration scripts completed

### 4.3 Next Phases

#### Phase 4 - Voice Integration (The Voice) 📋
**Priority**: Next  
**Scope**:
- Speech-to-Text integration for practice exercises
- Text-to-Speech for pronunciation guidance
- Voice-based practice exercises
- Audio playback components
- Cross-browser compatibility testing

#### Phase 5 - Deployment & Operations (Going Live) 📋
**Priority**: Medium  
**Scope**:
- Production optimization and performance tuning
- Google Cloud Run infrastructure setup
- CI/CD automation with GitHub Actions
- Monitoring and maintenance systems
- Comprehensive data management implementation

#### Phase 6 - Multi-Language Expansion 📋
**Priority**: Future  
**Scope**:
- Korean language integration (KoNLPy, cultural framework)
- Mandarin Chinese support (Jieba, Traditional/Simplified)
- South Slavic languages (CLASSLA, Croatian/Serbian)
- European languages (Spanish, French, German)

## 🔄 5. Data Architecture

### 5.1 PostgreSQL Schema Design
```sql
-- Core conversation storage with vector embeddings
users (id, username, email, preferences, ai_provider_preference)
conversation_sessions (id, user_id, title, language_code, ai_provider, ai_model, context)
conversation_messages (id, session_id, role, content, ai_metadata, learning_analytics)
conversation_interactions (id, message_id, user_id, concept_id, srs_data)
conversation_analytics (id, session_id, performance_metrics, engagement_scores)
```

### 5.2 Neo4j Graph Schema
```cypher
// Multi-language knowledge representation
(g:GrammarPoint)-[:PREREQUISITE]->(g2:GrammarPoint)
(g:GrammarPoint)-[:CONTRASTS_WITH]->(g2:GrammarPoint)
(v:Vocabulary)-[:SYNONYM]->(v2:Vocabulary)
(v:Vocabulary)-[:PART_OF]->(c:CulturalContext)
(g:GrammarPoint)-[:SOURCED_FROM]->(s:Source)
```

### 5.3 Semantic Search Strategy
- **PostgreSQL pgvector**: Conversation embeddings for similarity search
- **Neo4j Vector Indexes**: Knowledge embeddings for concept discovery
- **Real-time Embeddings**: AI provider APIs for on-demand similarity

## 🤖 6. AI Integration Architecture

### 6.1 Multi-Provider Strategy
**Intelligent Model Routing**: Task-based selection for optimal performance and cost

#### OpenAI Models
- **GPT-4o**: Complex reasoning, detailed explanations, high-quality content
- **GPT-4o-mini**: Fast responses, simple tasks, cost-effective interactions
- **o1-preview**: Advanced reasoning for complex grammar analysis
- **o1-mini**: Structured reasoning for specific linguistic tasks

#### Google Gemini Models
- **Gemini 2.5 Pro**: Multimodal understanding, complex analysis, high-context
- **Gemini 2.5 Flash**: Fast inference, real-time interactions, cost-effective

### 6.2 Task Routing Examples
- **Grammar Generation**: GPT-4o (high-quality linguistic explanations)
- **Quick Responses**: Gemini 2.5 Flash (speed and cost optimization)
- **Complex Reasoning**: o1-preview (advanced logical analysis)
- **Content Embedding**: text-embedding-3-large (vector quality)
- **Real-time Chat**: Gemini 2.5 Flash (low latency)

### 6.3 Performance Monitoring
- AI provider response times and success rates
- Cost tracking and optimization
- Model performance comparison
- Automatic fallback mechanisms

## 🛡️ 7. Quality Assurance

### 7.1 Human Validation Workflow
```
AI generates content → status: 'pending_review'
Human reviewer validates → Approve/Edit/Reject
Approved content → status: 'approved' + relationships created
Only approved content → embedded with pgvector for search
```

### 7.2 Quality Gates
- **Linguistic Accuracy**: Native speaker validation of grammar explanations
- **Cultural Appropriateness**: Context and example sentence validation
- **Relationship Accuracy**: Prerequisite and contrast relationship verification
- **Consistency**: Alignment with existing approved content

### 7.3 Automated Testing
- **Backend**: 22 comprehensive tests with pytest
- **Categories**: Health, auth, conversations, content analysis, knowledge graph, learning, SRS, analytics, admin RBAC
- **Coverage**: All major functionality covered
- **CI/CD**: Automated testing on every commit

### 7.4 Security
- JWT authentication for API access
- Environment variables for sensitive data
- CORS configuration for cross-origin requests
- Rate limiting and request validation
- Secure database connections

## 🚀 8. Deployment Architecture

### 8.1 Development Environment
- **Docker Compose**: PostgreSQL, Neo4j, backend, frontend, validation UI
- **Hot Reloading**: All services support development mode
- **Health Checks**: Automated service health monitoring

### 8.2 Production Deployment (Planned)
- **Platform**: Google Cloud Run for scalable containerized deployment
- **Database**: Managed PostgreSQL with pgvector support
- **Knowledge Graph**: Neo4j AuraDB (cloud-hosted)
- **CI/CD**: GitHub Actions for automated testing and deployment
- **Monitoring**: Structured logging, health endpoints, performance tracking

### 8.3 Scalability Considerations
- Microservices architecture for horizontal scaling
- Database connection pooling
- AI provider load balancing
- CDN for static assets
- Caching strategies for frequently accessed data

---

**This architecture supports a scalable, maintainable, and extensible multi-language learning platform that can grow from Japanese to global language support while maintaining high quality through human validation and comprehensive testing.**
