# AI Language Tutor - Project Planning & Architecture

## 🎯 Project Overview

**Vision**: An intelligent, personalized multi-language learning platform that combines graph-based knowledge representation with AI-powered tutoring and voice interaction. Starting with Japanese, expanding to Korean, Mandarin, Spanish, and beyond.

**Core Philosophy**: Create a "living brain" for language learning that understands connections between concepts, cultural contexts, and adapts to each learner's unique journey across multiple languages and cultures.

---

## 📊 Current Project Status

**🎯 Overall Progress**: ~60% Complete | **Current Phase**: Transitioning to Phase 4 (Voice Integration)

### ✅ Completed Phases
- **Phase 0 - Foundation** ✅ Complete (Git, Docker, Cloud setup)  
- **Phase 1 - Knowledge Graph** ✅ Complete (60,958 nodes, 128,487 edges imported)  
- **Phase 2 - Backend API** ✅ Complete (22+ endpoints, comprehensive testing)  
- **Phase 3 - Frontend** ✅ Complete (Full React app, responsive design, real-time features)

### 🚧 In Progress
- **Streamlit Validation Interface** - 30% complete (Human validation workbench)
- **Knowledge Graph Data Import** - 80% complete (Scripts ready, execution needed)

### 📋 Next Priorities
1. **Phase 4 - Voice Integration** (4-6 weeks) - Speech-to-Text, Text-to-Speech
2. **Phase 5 - Deployment** (3-4 weeks) - Production optimization, CI/CD
3. **Phase 6 - Multi-Language** (Future) - Korean, Mandarin, Slavic languages

### 🏆 Key Achievements
- **22 comprehensive tests** passing with full functionality coverage
- **Real-time conversation interface** with streaming AI responses  
- **Multi-provider AI integration** (OpenAI + Gemini) with intelligent routing
- **Comprehensive knowledge graph** ready for semantic search and learning
- **Mobile-responsive design** across all components
- **Advanced personalization** with SRS algorithms and learning analytics

---

## 🏗️ Architecture Overview

### System Components
1. **PostgreSQL Database** - The "Memory Center"
   - User accounts, profiles, and authentication data
   - Conversation history and chat sessions
   - Learning progress and statistics tracking
   - User preferences and settings
   - Session management and activity logs

2. **Universal Knowledge Graph (Neo4j)** - The "Multi-Lingual Brain"
   - Cross-language lexical knowledge and concept mapping
   - Language-specific grammatical structures and relationships
   - Universal learning patterns and cultural contexts
   - Complex relationship modeling between concepts

3. **Semantic Search & Embeddings** - Distributed Intelligence
   - PostgreSQL with pgvector for conversation embeddings
   - Neo4j vector indexes for knowledge graph semantic search
   - Direct AI provider embedding APIs for real-time similarity

4. **Backend API (FastAPI)** - The "Nervous System"
   - RESTful API with JWT authentication
   - Advanced personalization algorithms
   - Spaced Repetition System (SRS)
   - Voice processing integration
   - Conversation management and storage

5. **Frontend (Next.js)** - The "Body"
   - Modern React-based UI with TypeScript
   - Real-time data fetching with TanStack Query
   - Responsive design with Tailwind CSS + Shadcn/UI
   - Voice interaction capabilities
   - Real-time conversation interface

6. **Enhanced Human Tutor Interface (Streamlit)** - The "Linguistic Workbench"
   - Professional-grade validation and content creation tools
   - Advanced linguistic analysis workbench with morphological tools
   - Collaborative multi-reviewer workflow with peer consultation
   - AI-human learning loop with feedback analytics
   - Cultural appropriateness and pedagogical effectiveness validators
   - Batch operations and smart content prioritization
   - Quality metrics and performance tracking for reviewers

7. **Voice Services (Google Cloud)** - The "Voice"
   - Speech-to-Text for practice exercises
   - Text-to-Speech for pronunciation guidance

---

## 🛠️ Technology Stack

### Backend
- **Framework**: FastAPI (Python 3.11+)
- **Databases**: 
  - **PostgreSQL**: User data, conversations, sessions, transactional data, and conversation embeddings (pgvector)
  - **Neo4j AuraDB**: Knowledge graph for language concepts, relationships, and knowledge embeddings (vector indexes)
- **ORM**: SQLAlchemy with Alembic for PostgreSQL migrations
- **AI Services**: 
  - **OpenAI**: GPT-4o, GPT-4o-mini, o1-preview, o1-mini
  - **Google Gemini**: Gemini 2.5 Pro, Gemini 2.5 Flash
  - **Voice**: Google Cloud Speech/TTS
- **AI Architecture**: Multi-provider unified interface with automatic model routing
- **Multi-Language NLP**: GiNZA (Japanese), KoNLPy (Korean), Jieba (Chinese), CLASSLA (Croatian/Serbian), spaCy (European languages)
- **Authentication**: JWT tokens with passlib
- **Deployment**: Docker containers on Google Cloud Run
- **Testing**: Pytest with comprehensive coverage

### Frontend
- **Framework**: Next.js 14+ with App Router
- **Language**: TypeScript
- **Styling**: Tailwind CSS + Shadcn/UI components
- **State Management**: Zustand (client) + TanStack Query (server)
- **Audio**: Web APIs (MediaRecorder, Audio)

### Human Tutor Interface
- **Framework**: Streamlit (Professional linguistic workbench)
- **Purpose**: Advanced content validation, creation, and collaborative review
- **Features**: Linguistic analysis tools, cultural validators, pedagogical assessment
- **Collaboration**: Multi-reviewer workflow with peer consultation and discussion
- **AI Integration**: Human-AI learning loop with feedback analytics
- **Database**: Direct Neo4j integration with advanced querying and batch operations
- **Authentication**: Role-based access (Native Speakers, Linguists, Teachers, QA)

### Development Tools
- **Code Quality**: Ruff (Python), ESLint + Prettier (TypeScript)
- **Dependency Management**: Poetry (Python), npm/yarn (Node.js)
- **Containerization**: Docker + Docker Compose
- **CI/CD**: GitHub Actions
- **Monitoring**: Structured logging, Sentry/LogRocket

### Data Management & Governance
- **Data Governance**: Automated classification, quality monitoring, compliance framework
- **Backup & Recovery**: Multi-tier backup strategy with automated disaster recovery
- **Security & Privacy**: End-to-end encryption, GDPR compliance, role-based access control
- **Monitoring & Observability**: Real-time data quality monitoring, predictive analytics
- **Lifecycle Management**: Intelligent data archival, retention policies, automated optimization
- **Data Catalog**: Comprehensive metadata management, lineage tracking, discovery engine

---

## 📁 Project Structure

```
aiLanguageTutor/
├── .env.template              # Environment variables template
├── .gitignore                # Git ignore patterns
├── docker-compose.yml        # Local development environment
├── PLANNING.md               # This file
├── TASK.md                   # Task tracking
├── README.md                 # Setup and usage instructions
├── description.md            # Original detailed project specification
├── backend/                  # FastAPI application
│   ├── Dockerfile
│   ├── pyproject.toml        # Poetry dependencies
│   ├── alembic.ini          # Database migration configuration
│   ├── app/
│   │   ├── main.py          # FastAPI app instance
│   │   ├── models/          # SQLAlchemy models
│   │   │   ├── __init__.py
│   │   │   ├── user.py      # User model
│   │   │   ├── conversation.py  # Conversation models
│   │   │   └── analytics.py # Analytics models
│   │   ├── schemas/         # Pydantic schemas
│   │   │   ├── __init__.py
│   │   │   ├── user.py      # User schemas
│   │   │   ├── conversation.py  # Conversation schemas
│   │   │   └── analytics.py # Analytics schemas
│   │   ├── crud/            # Database operations
│   │   │   ├── __init__.py
│   │   │   ├── user.py      # User CRUD operations
│   │   │   ├── conversation.py  # Conversation CRUD operations
│   │   │   └── analytics.py # Analytics CRUD operations
│   │   ├── services/        # Business logic services
│   │   │   ├── __init__.py
│   │   │   ├── conversation.py  # Conversation management service
│   │   │   ├── ai_provider.py   # AI provider service
│   │   │   └── analytics.py # Learning analytics service
│   │   ├── db/              # Database connections and utilities
│   │   │   ├── __init__.py
│   │   │   ├── postgresql.py    # PostgreSQL connection
│   │   │   └── neo4j.py        # Neo4j connection
│   │   ├── core/
│   │   │   ├── config.py    # Settings management
│   │   │   └── security.py  # Authentication logic
│   │   └── api/v1/
│   │       ├── api.py       # Route aggregation
│   │       └── endpoints/   # API endpoints
│   │           ├── auth.py  # Authentication endpoints
│   │           ├── conversations.py # Conversation endpoints
│   │           ├── users.py # User management endpoints
│   │           └── health.py # Health check endpoints
│   └── migrations/          # Alembic database migrations
│       └── versions/        # Migration files
├── frontend/                 # Next.js application
│   ├── Dockerfile
│   ├── package.json
│   ├── app/                 # App Router pages
│   ├── components/          # React components
│   ├── lib/                 # Utilities and API client
│   └── stores/              # Zustand state stores
├── validation-ui/           # Human validation interface (Streamlit)
│   ├── main.py              # Streamlit app entry point
│   ├── pages/               # Validation interface pages
│   ├── components/          # Reusable UI components
│   ├── requirements.txt     # Python dependencies
│   └── config.py            # Configuration and database connections
├── scripts/                  # Data migration and utilities
├── tests/                   # Test files
└── .github/workflows/       # CI/CD pipelines
```

---

## 💬 Conversation Storage & Management Architecture

### PostgreSQL Schema for Conversations

Our conversation storage system uses PostgreSQL to maintain detailed records of all user interactions, enabling personalized learning experiences and comprehensive progress tracking.

#### Core Tables Structure

```sql
-- Users table (extends basic auth with conversation preferences)
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Conversation preferences
    preferred_ai_provider VARCHAR(20) DEFAULT 'openai',
    conversation_style VARCHAR(20) DEFAULT 'balanced', -- casual, formal, balanced
    max_conversation_length INTEGER DEFAULT 50,
    auto_save_conversations BOOLEAN DEFAULT TRUE
);

-- Conversation sessions
CREATE TABLE conversation_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255),
    language_code VARCHAR(10) NOT NULL DEFAULT 'ja', -- ISO language code
    session_type VARCHAR(20) NOT NULL DEFAULT 'chat', -- chat, lesson, practice, quiz
    status VARCHAR(20) DEFAULT 'active', -- active, completed, archived
    
    -- AI Configuration
    ai_provider VARCHAR(20) NOT NULL,
    ai_model VARCHAR(50) NOT NULL,
    system_prompt TEXT,
    conversation_context JSONB, -- Stores context like current lesson, difficulty level
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    
    -- Statistics
    total_messages INTEGER DEFAULT 0,
    user_messages INTEGER DEFAULT 0,
    ai_messages INTEGER DEFAULT 0,
    session_duration_seconds INTEGER DEFAULT 0
);

-- Individual conversation messages
CREATE TABLE conversation_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES conversation_sessions(id) ON DELETE CASCADE,
    
    -- Message content
    role VARCHAR(20) NOT NULL, -- user, assistant, system
    content TEXT NOT NULL,
    content_type VARCHAR(20) DEFAULT 'text', -- text, audio, image
    
    -- AI Generation metadata (for assistant messages)
    ai_provider VARCHAR(20),
    ai_model VARCHAR(50),
    tokens_used INTEGER,
    generation_time_ms INTEGER,
    confidence_score DECIMAL(3,2),
    
    -- Learning analytics
    contains_correction BOOLEAN DEFAULT FALSE,
    grammar_points_mentioned TEXT[], -- Array of grammar point IDs
    vocabulary_introduced TEXT[], -- Array of new vocabulary
    difficulty_level INTEGER, -- 1-5 scale
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    message_order INTEGER NOT NULL, -- Order within session
    
    -- Constraints
    UNIQUE(session_id, message_order)
);

-- User learning interactions within conversations
CREATE TABLE conversation_interactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id UUID NOT NULL REFERENCES conversation_messages(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Interaction type
    interaction_type VARCHAR(30) NOT NULL, -- question_asked, correction_received, concept_explained, practice_completed
    
    -- Learning data
    concept_id VARCHAR(100), -- Reference to Neo4j node ID
    concept_type VARCHAR(20), -- grammar_point, vocabulary, cultural_note
    user_response TEXT,
    is_correct BOOLEAN,
    attempts_count INTEGER DEFAULT 1,
    
    -- Spaced repetition integration
    ease_factor DECIMAL(3,2) DEFAULT 2.5,
    interval_days INTEGER DEFAULT 1,
    next_review_date DATE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Conversation analytics and insights
CREATE TABLE conversation_analytics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES conversation_sessions(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Performance metrics
    words_per_minute DECIMAL(5,2),
    grammar_accuracy_percentage DECIMAL(5,2),
    vocabulary_usage_diversity INTEGER,
    conversation_flow_score DECIMAL(3,2),
    
    -- Learning progress
    new_concepts_learned INTEGER DEFAULT 0,
    concepts_reviewed INTEGER DEFAULT 0,
    mistakes_corrected INTEGER DEFAULT 0,
    cultural_insights_gained INTEGER DEFAULT 0,
    
    -- Engagement metrics
    session_engagement_score DECIMAL(3,2),
    user_initiative_count INTEGER, -- How often user started topics
    question_asking_frequency DECIMAL(3,2),
    
    analyzed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

#### Database Indexes for Performance

```sql
-- Indexes for optimal query performance
CREATE INDEX idx_conversation_sessions_user_id ON conversation_sessions(user_id);
CREATE INDEX idx_conversation_sessions_language ON conversation_sessions(language_code);
CREATE INDEX idx_conversation_sessions_created_at ON conversation_sessions(created_at DESC);

CREATE INDEX idx_conversation_messages_session_id ON conversation_messages(session_id);
CREATE INDEX idx_conversation_messages_order ON conversation_messages(session_id, message_order);
CREATE INDEX idx_conversation_messages_role ON conversation_messages(role);
CREATE INDEX idx_conversation_messages_created_at ON conversation_messages(created_at DESC);

CREATE INDEX idx_conversation_interactions_user_id ON conversation_interactions(user_id);
CREATE INDEX idx_conversation_interactions_concept ON conversation_interactions(concept_id, concept_type);
CREATE INDEX idx_conversation_interactions_review_date ON conversation_interactions(next_review_date);

CREATE INDEX idx_conversation_analytics_user_id ON conversation_analytics(user_id);
CREATE INDEX idx_conversation_analytics_analyzed_at ON conversation_analytics(analyzed_at DESC);
```

### Conversation Management Service Architecture

```python
class ConversationService:
    """Service for managing user conversations and learning interactions."""
    
    def __init__(self, db: AsyncSession, ai_service: AIProviderService):
        self.db = db
        self.ai_service = ai_service
    
    async def create_conversation_session(
        self,
        user_id: UUID,
        language_code: str,
        session_type: str,
        title: Optional[str] = None
    ) -> ConversationSession:
        """Create a new conversation session."""
        
    async def add_message_to_conversation(
        self,
        session_id: UUID,
        role: str,
        content: str,
        ai_metadata: Optional[dict] = None
    ) -> ConversationMessage:
        """Add a message to an existing conversation."""
        
    async def get_conversation_history(
        self,
        user_id: UUID,
        session_id: Optional[UUID] = None,
        limit: int = 50
    ) -> List[ConversationMessage]:
        """Retrieve conversation history for a user."""
        
    async def analyze_conversation_for_learning(
        self,
        session_id: UUID
    ) -> ConversationAnalytics:
        """Analyze conversation for learning insights and progress tracking."""
        
    async def get_user_conversation_stats(
        self,
        user_id: UUID,
        date_range: Optional[Tuple[datetime, datetime]] = None
    ) -> UserConversationStats:
        """Get comprehensive conversation statistics for a user."""
```

### Integration with Existing Systems

#### Neo4j Integration
- **Concept Linking**: Conversation interactions reference Neo4j node IDs for grammar points and vocabulary
- **Progress Tracking**: Learning progress from conversations updates mastery scores in Neo4j
- **Relationship Discovery**: Conversations help identify which concepts are frequently discussed together

#### Semantic Search Integration
- **PostgreSQL pgvector**: Store conversation embeddings for similarity search and context retrieval
- **Neo4j Vector Indexes**: Store knowledge embeddings for semantic concept discovery
- **AI Provider Embeddings**: Generate embeddings on-demand using OpenAI/Gemini embedding APIs

#### AI Provider Integration
- **Context Management**: Maintain conversation context across AI provider calls
- **Provider Performance Tracking**: Track which AI providers perform best for different conversation types
- **Dynamic Provider Selection**: Choose optimal AI provider based on conversation history and user preferences

---

## 🤖 Multi-Provider AI Architecture

### AI Provider Strategy
Our application leverages multiple AI providers to optimize for performance, cost, and capabilities:

**OpenAI Models:**
- **GPT-4o**: Complex reasoning, detailed explanations, high-quality content generation
- **GPT-4o-mini**: Fast responses, simple tasks, cost-effective interactions
- **o1-preview**: Advanced reasoning for complex grammar analysis
- **o1-mini**: Structured reasoning for specific linguistic tasks

**Google Gemini Models:**
- **Gemini 2.5 Pro**: Multimodal understanding, complex analysis, high-context tasks
- **Gemini 2.5 Flash**: Fast inference, real-time interactions, cost-effective processing

### Unified AI Interface
```python
# Core AI service abstraction
class AIProviderService:
    def __init__(self):
        self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)
    
    async def generate_content(
        self, 
        prompt: str, 
        task_type: TaskType,
        complexity: ComplexityLevel = ComplexityLevel.MEDIUM
    ) -> AIResponse:
        # Intelligent model routing based on task requirements
        provider, model = self._route_request(task_type, complexity)
        return await self._execute_request(provider, model, prompt)
    
    def _route_request(self, task_type: TaskType, complexity: ComplexityLevel):
        # Route based on task type, complexity, cost, and performance requirements
        if task_type == TaskType.GRAMMAR_GENERATION and complexity == ComplexityLevel.HIGH:
            return ("openai", "gpt-4o")  # High-quality grammar explanations
        elif task_type == TaskType.QUICK_RESPONSE:
            return ("gemini", "gemini-2.5-flash")  # Fast interactions
        elif task_type == TaskType.REASONING:
            return ("openai", "o1-preview")  # Complex reasoning tasks
        # ... more routing logic
```

### Model Selection Criteria

| Task Type | Primary Model | Fallback Model | Reasoning |
|-----------|---------------|----------------|-----------|
| Grammar Generation | GPT-4o | Gemini 2.5 Pro | High-quality linguistic explanations |
| Quick Responses | Gemini 2.5 Flash | GPT-4o-mini | Speed and cost optimization |
| Complex Reasoning | o1-preview | GPT-4o | Advanced logical analysis |
| Content Embedding | text-embedding-3-large | Gemini embedding | Vector quality and consistency |
| Real-time Chat | Gemini 2.5 Flash | GPT-4o-mini | Low latency requirements |

### Configuration Management
```python
# Environment variables for multi-provider setup
OPENAI_API_KEY=your_openai_key
GEMINI_API_KEY=your_gemini_key
GOOGLE_CLOUD_PROJECT_ID=your_gcp_project

# AI routing configuration
AI_ROUTING_CONFIG = {
    "default_provider": "openai",
    "fallback_enabled": True,
    "cost_optimization": True,
    "performance_monitoring": True
}
```

---

## 🔍 Content Validation Workflow

### Human-in-the-Loop Quality Assurance
Our AI-generated content requires human validation to ensure linguistic accuracy and cultural appropriateness. This workflow ensures only high-quality, validated content reaches learners.

### Validation Process Flow
```
1. AI generates grammar content → status: 'pending_review'
2. Human reviewer validates content → Approve/Edit/Reject
3. Approved content → status: 'approved' + relationships created
4. Only approved content → embedded in PostgreSQL with pgvector for search
```

### Validation Interface Architecture
```python
# Streamlit-based internal validation tool
class ValidationInterface:
    def display_pending_reviews(self):
        # Show list of all pending GrammarPoint nodes
        pending_items = neo4j_query(
            "MATCH (g:GrammarPoint {status: 'pending_review'}) RETURN g"
        )
        return pending_items
    
    def review_item(self, grammar_point_id: str):
        # Detailed review screen with validation actions
        # - Display AI-generated content
        # - Show proposed relationships
        # - Provide Approve/Edit/Reject buttons
        
    def approve_content(self, item_id: str, modifications: dict = None):
        # Update status to 'approved'
        # Create actual Neo4j relationships
        # Trigger embedding generation
        
    def reject_content(self, item_id: str, reason: str):
        # Delete the pending node
        # Log rejection reason for AI improvement
```

### Quality Gates
- **Linguistic Accuracy**: Native speaker validation of grammar explanations
- **Cultural Appropriateness**: Context and example sentence validation
- **Relationship Accuracy**: Prerequisite and contrast relationship verification
- **Consistency**: Alignment with existing approved content

---

## 📚 AI-Powered Content Analysis System

### Overview
An intelligent endpoint that can analyze Japanese grammar textbooks, articles, and educational content to automatically extract new grammar points, vocabulary, and their relationships, then integrate them into the knowledge graph with proper source attribution.

### Content Analysis Workflow
```
1. Upload/Submit Content (PDF, text, URL)
2. AI Content Extraction & Preprocessing 
3. Multi-Provider AI Analysis (OpenAI + Gemini)
4. Knowledge Item Identification & Classification
5. Relationship Mapping & Connection Analysis
6. Source Attribution & Reference Linking
7. Quality Scoring & Confidence Assessment
8. Human Validation Queue Integration
9. Automatic Knowledge Graph Integration
```

### Core Components

#### 1. Content Ingestion Service
```python
class ContentIngestionService:
    async def process_content(
        self,
        content: Union[UploadFile, str, HttpUrl],
        source_metadata: SourceMetadata
    ) -> ContentAnalysisResult:
        # Extract text from various formats (PDF, HTML, plain text)
        # Preprocess and chunk content for AI analysis
        # Route to appropriate AI analysis pipeline
```

#### 2. Multi-Provider AI Analysis
```python
class ContentAnalysisService:
    async def analyze_grammar_content(
        self,
        text_chunks: List[str],
        source_info: SourceInfo
    ) -> AnalysisResult:
        # Use GPT-4o for detailed linguistic analysis
        # Use Gemini 2.5 Pro for relationship mapping
        # Cross-validate findings between providers
        # Generate confidence scores for each extraction
```

#### 3. Knowledge Graph Integration
```python
class KnowledgeIntegrationService:
    async def integrate_findings(
        self,
        analysis_result: AnalysisResult,
        source_reference: SourceReference
    ) -> IntegrationResult:
        # Create new nodes with source attribution
        # Map relationships to existing knowledge
        # Generate embedding vectors for new content
        # Queue for human validation if confidence < threshold
```

### API Endpoint Design

```python
@router.post("/api/v1/content/analyze")
async def analyze_content(
    content: Union[UploadFile, ContentSubmission],
    source_metadata: SourceMetadata = Body(...),
    analysis_options: AnalysisOptions = Body(default_factory=AnalysisOptions),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Analyze educational content and extract grammar knowledge
    
    - **content**: File upload (PDF, TXT) or text submission
    - **source_metadata**: Title, author, publication info, URL
    - **analysis_options**: AI provider preferences, confidence thresholds
    - **Returns**: Analysis results with extracted knowledge items
    """
```

### Source Attribution System

#### Source Metadata Schema
```python
class SourceMetadata(BaseModel):
    title: str
    author: Optional[str] = None
    publisher: Optional[str] = None
    publication_date: Optional[date] = None
    isbn: Optional[str] = None
    url: Optional[HttpUrl] = None
    page_range: Optional[str] = None
    chapter_section: Optional[str] = None
    language: str = "ja"
    content_type: ContentType  # textbook, article, blog, video_transcript
    
class SourceReference(BaseModel):
    source_id: str
    page_number: Optional[int] = None
    paragraph_number: Optional[int] = None
    exact_quote: Optional[str] = None
    context_snippet: str
```

#### Neo4j Source Integration
```cypher
// Create source nodes
CREATE (s:Source {
    id: $source_id,
    title: $title,
    author: $author,
    publisher: $publisher,
    publication_date: $publication_date,
    url: $url,
    content_type: $content_type
})

// Link grammar points to sources
MATCH (g:GrammarPoint {id: $grammar_id})
MATCH (s:Source {id: $source_id})
CREATE (g)-[:SOURCED_FROM {
    page: $page_number,
    confidence: $confidence_score,
    extracted_date: datetime()
}]->(s)
```

---

## 🎯 Development Phases

### Phase 0: Foundation & Environment Setup ⚙️ ✅ COMPLETE
**Goal**: Stable, reproducible development environment
- ✅ Git repository and branching strategy
- ✅ Docker containerization
- ✅ Cloud services provisioning
- ✅ Development tooling setup

### Phase 1: The Knowledge Graph (Building the Brain) 🧠 ✅ COMPLETE
**Goal**: Populate core knowledge graphs (Lexical, Grammatical, Pragmatic) with legacy system integration
- ✅ Data schema definition (Neo4j + PostgreSQL vector indexes)
- ✅ **Legacy system migration** from NetworkX graph (60,958 nodes, 128,487 edges)
- ✅ **Feature integration** from existing Japanese lexical graph system
- ✅ **Enhanced FastAPI backend** with optimized performance
- ✅ **Wikidata integration** enhancement for comprehensive linguistic data
- ✅ Multi-provider AI content generation (OpenAI + Google Gemini)
- ✅ Intelligent model routing based on task complexity and cost
- ✅ Vector embeddings creation with multiple providers (stored in PostgreSQL + Neo4j)

### Phase 2: The Core API (The Nervous System) 🔗 ✅ COMPLETE
**Goal**: Backend API with personalization and content analysis
- ✅ FastAPI application structure with 22+ endpoints
- ✅ User authentication & onboarding (JWT-based)
- ✅ Advanced SRS algorithms (SuperMemo-2 adaptation)
- ✅ Personalized content delivery and learning analytics
- ✅ **AI-powered content analysis endpoint** for automatic knowledge extraction
- ✅ Conversation management system with session-based storage
- ✅ Knowledge graph integration with Neo4j
- ✅ Multi-provider AI integration (OpenAI + Gemini)
- ✅ Role-based access control (RBAC) for admin features
- ✅ Comprehensive test coverage (22 tests)

### Phase 3: The Frontend Experience (The Body) 💻 ✅ COMPLETE
**Goal**: Engaging, personalized, and culturally immersive UI
- ✅ **Complete Next.js 14+ Application** with TypeScript
- ✅ **Authentication Interface** - Login and Register with validation
- ✅ **Real-time Conversation Interface** with streaming AI responses
- ✅ **Personalized Learning Dashboard** with analytics and progress tracking
- ✅ **Content Analysis Interface** for text processing and file uploads
- ✅ **SRS Review Interface** for spaced repetition practice
- ✅ **Responsive Design** - Mobile-first with Tailwind CSS + Shadcn/UI
- ✅ **Navigation System** - Comprehensive app navigation
- ✅ **Error Handling & UX** - Toast notifications, loading states, error boundaries
- ✅ **TanStack Query + Zustand** for state management
- ✅ **API Integration** with comprehensive backend connectivity

### Phase 4: Voice Integration (The Voice) 🎤 🚧 NEXT PRIORITY
**Goal**: Conversational learning experience
- 📋 Speech-to-Text integration for practice exercises
- 📋 Text-to-Speech synthesis for pronunciation guidance
- 📋 Voice-based practice exercises
- 📋 Audio playback components
- 📋 Google Cloud Speech API integration
- 📋 Web Audio APIs implementation
- 📋 Voice activity detection
- 📋 Cross-browser voice compatibility

**Estimated Duration**: 4-6 weeks
**Technical Requirements**: Google Cloud Speech/TTS APIs, MediaRecorder, Web Audio APIs

### Phase 5: Deployment & Operations (Going Live) 🚀 📋 PLANNED
**Goal**: Production deployment and maintenance
- 📋 Production optimization and performance tuning
- 📋 Google Cloud Run infrastructure setup
- 📋 CI/CD automation with GitHub Actions
- 📋 Monitoring and maintenance systems
- 📋 Security hardening and compliance
- 📋 Backup and disaster recovery procedures
- 📋 Comprehensive data management implementation

**Estimated Duration**: 3-4 weeks
**Prerequisites**: Phase 4 completion, performance optimization

### Phase 6: Multi-Language Expansion 🌍 📋 FUTURE
**Goal**: Expand beyond Japanese to multiple languages
- 📋 **Korean Integration** (First expansion)
  - KoNLPy NLP pipeline integration
  - Korean cultural validation framework
  - Korean-specific learning scenarios
  - Native speaker reviewer recruitment

- 📋 **Mandarin Chinese** (Second expansion)
  - Jieba NLP pipeline integration
  - Traditional/Simplified Chinese support
  - Chinese cultural context engine

- 📋 **South Slavic Languages** (Third expansion)
  - CLASSLA integration (Croatian/Serbian)
  - Dual-script support (Latin/Cyrillic)

**Estimated Duration**: 8-12 weeks per language

---

## 🎨 Design Principles

### Code Quality
- **Modularity**: No file over 500 lines of code
- **Testing**: Comprehensive Pytest coverage for all features
- **Type Safety**: Full TypeScript + Python type hints
- **Documentation**: Google-style docstrings for all functions
- **Consistency**: Automated formatting with Ruff + Prettier

### User Experience
- **Hyper-Personalization**: AI-driven adaptation to learning style, emotional state, and cultural interests
- **Immersive Learning**: Contextual scenarios and cultural integration
- **Gamified Engagement**: Achievement systems, streaks, and social learning features
- **Multi-Modal Experience**: Visual, auditory, and kinesthetic learning support
- **Community-Driven**: Collaborative learning with native speakers and peers
- **Accessible & Inclusive**: Universal design supporting diverse learning needs
- **Cross-Platform**: Seamless experience across web, mobile, and emerging technologies

### Architecture
- **Microservices**: Clear separation of concerns
- **Scalability**: Designed for growth and performance
- **Security**: JWT authentication, encrypted secrets
- **Observability**: Structured logging and error tracking

---

## 🔧 Development Workflow

### Git Strategy
- **Main Branch**: Always deployable production code
- **Feature Branches**: Descriptive names (e.g., `feat/setup-backend-docker`)
- **Pull Requests**: Mandatory code reviews
- **Conventional Commits**: Standardized commit messages

### Environment Management
- **Local Development**: Docker Compose with hot reloading
- **Environment Variables**: Secure `.env` file management
- **Secrets**: Cloud-native secret management
- **Configuration**: Pydantic-based settings validation

### Quality Assurance
- **Automated Testing**: Run on every PR
- **Code Linting**: Enforced in CI/CD
- **Type Checking**: MyPy + TypeScript strict mode
- **Security Scanning**: Automated vulnerability checks

---

## 🎯 Success Metrics

### Technical
- **Performance**: <200ms API response times
- **Reliability**: 99.9% uptime
- **Security**: Zero critical vulnerabilities
- **Code Quality**: 90%+ test coverage

### User Experience
- **Engagement**: Daily active usage
- **Learning Effectiveness**: Measurable progress tracking
- **Accessibility**: WCAG 2.1 AA compliance
- **Mobile Experience**: Responsive across all devices

---

## 🚀 Getting Started

1. **Clone and Setup**: Follow README.md instructions
2. **Environment**: Copy `.env.template` to `.env` and configure
3. **Development**: Run `docker-compose up --build`
4. **Verify**: Access backend docs at `localhost:8000/docs`
5. **Frontend**: Access app at `localhost:3000`

---

*This document serves as the single source of truth for project architecture, conventions, and development practices. Update it as the project evolves.*