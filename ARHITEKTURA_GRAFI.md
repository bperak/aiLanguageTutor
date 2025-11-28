# Grafovi Arhitekture Sustava - AI Language Tutor

## Graf 1: High-Level Arhitektura (Preporučeno za prezentaciju)

```mermaid
graph TB
    subgraph "Korisnici"
        STUDENT[👤 Student<br/>Web Browser]
        NASTAVNIK[👨‍🏫 Nastavnik<br/>Streamlit UI]
    end
    
    subgraph "Frontend Layer"
        FE[Next.js 14+ Frontend<br/>TypeScript + React<br/>Tailwind CSS + Shadcn/UI]
    end
    
    subgraph "Backend Layer"
        BE[FastAPI Backend<br/>Python 3.11+<br/>JWT Authentication]
        AI_ROUTER[AI Router<br/>Multi-Provider<br/>Model Selection]
    end
    
    subgraph "Baze Podataka"
        PG[(PostgreSQL<br/>+ pgvector<br/>Memory Center)]
        NEO[(Neo4j AuraDB<br/>Knowledge Graph<br/>138,691 čvorova<br/>185,817 relacija)]
    end
    
    subgraph "AI Providers"
        OPENAI[OpenAI<br/>GPT-4o, GPT-4o-mini<br/>o1-preview, o1-mini]
        GEMINI[Google Gemini<br/>Gemini 2.5 Pro<br/>Gemini 2.5 Flash]
    end
    
    subgraph "Validation Layer"
        STREAMLIT[Streamlit<br/>Validation UI<br/>Human-in-the-Loop]
    end
    
    STUDENT -->|HTTPS| FE
    NASTAVNIK -->|HTTPS| STREAMLIT
    
    FE -->|JWT + REST API| BE
    FE <-->|Web Audio APIs| VOICE[Google Cloud<br/>Speech/TTS]
    
    BE -->|SQL + Embeddings| PG
    BE -->|Cypher + Vector Search| NEO
    BE -->|Route Request| AI_ROUTER
    
    AI_ROUTER --> OPENAI
    AI_ROUTER --> GEMINI
    
    STREAMLIT -->|Cypher Queries| NEO
    STREAMLIT -->|Admin APIs| BE
    
    BE -->|JSON/Stream| FE
    
    style FE fill:#3b82f6,stroke:#1e40af,color:#fff
    style BE fill:#10b981,stroke:#059669,color:#fff
    style PG fill:#8b5cf6,stroke:#6d28d9,color:#fff
    style NEO fill:#f59e0b,stroke:#d97706,color:#fff
    style OPENAI fill:#6366f1,stroke:#4f46e5,color:#fff
    style GEMINI fill:#ec4899,stroke:#db2777,color:#fff
    style STREAMLIT fill:#14b8a6,stroke:#0d9488,color:#fff
```

---

## Graf 2: Detaljna Tehnička Arhitektura

```mermaid
graph TB
    subgraph "Client Layer"
        WEB[Web Browser<br/>Chrome/Firefox/Safari]
        MOBILE[Mobile Browser<br/>iOS/Android]
    end
    
    subgraph "Frontend - Next.js 14+"
        NEXT_APP[App Router<br/>Server Components]
        REACT[React 18+<br/>TypeScript]
        UI[Shadcn/UI<br/>Tailwind CSS]
        STATE[Zustand<br/>TanStack Query]
        AUDIO[Web Audio APIs<br/>MediaRecorder]
    end
    
    subgraph "API Gateway"
        API[FastAPI Backend<br/>Port 8000]
        AUTH[JWT Authentication<br/>passlib]
        MIDDLEWARE[CORS<br/>Rate Limiting<br/>Error Handling]
    end
    
    subgraph "Business Logic Layer"
        CONV_SVC[Conversation Service<br/>Session Management]
        AI_SVC[AI Provider Service<br/>Multi-Provider Router]
        GRAMMAR_SVC[Grammar Service<br/>Graph Queries]
        LEARNING_SVC[Learning Path Service<br/>SRS Algorithm]
        ANALYTICS_SVC[Analytics Service<br/>Progress Tracking]
    end
    
    subgraph "Data Layer - PostgreSQL"
        PG_MAIN[(PostgreSQL 15+<br/>Main Database)]
        PG_VECTOR[pgvector Extension<br/>Vector Embeddings<br/>1536 dimensions]
        PG_TABLES[Tables:<br/>users, sessions,<br/>messages, analytics]
    end
    
    subgraph "Data Layer - Neo4j"
        NEO_MAIN[(Neo4j AuraDB<br/>Graph Database)]
        NEO_VECTOR[Vector Indexes<br/>Semantic Search]
        NEO_NODES[Nodes:<br/>138,691 total<br/>Words, GrammarPatterns,<br/>Classifications, Topics]
        NEO_RELS[Relationships:<br/>185,817 total<br/>PREREQUISITE_FOR,<br/>USES_WORD, SIMILAR_TO]
    end
    
    subgraph "AI Services"
        OPENAI_API[OpenAI API<br/>GPT-4o, GPT-4o-mini<br/>o1-preview, o1-mini<br/>text-embedding-3-large]
        GEMINI_API[Google Gemini API<br/>Gemini 2.5 Pro<br/>Gemini 2.5 Flash<br/>embedding-001]
        EMBEDDING[Embedding Service<br/>Multi-Provider<br/>Vector Generation]
    end
    
    subgraph "Validation & Admin"
        STREAMLIT_APP[Streamlit App<br/>Port 8501]
        VALIDATION[Content Validation<br/>Human Review]
        ADMIN[Admin Dashboard<br/>Quality Metrics]
    end
    
    subgraph "External Services"
        GCP_SPEECH[Google Cloud<br/>Speech-to-Text]
        GCP_TTS[Google Cloud<br/>Text-to-Speech]
    end
    
    WEB --> NEXT_APP
    MOBILE --> NEXT_APP
    
    NEXT_APP --> REACT
    REACT --> UI
    REACT --> STATE
    REACT --> AUDIO
    
    NEXT_APP -->|HTTPS| API
    AUDIO <--> GCP_SPEECH
    AUDIO <--> GCP_TTS
    
    API --> AUTH
    API --> MIDDLEWARE
    API --> CONV_SVC
    API --> AI_SVC
    API --> GRAMMAR_SVC
    API --> LEARNING_SVC
    API --> ANALYTICS_SVC
    
    CONV_SVC --> PG_MAIN
    CONV_SVC --> NEO_MAIN
    GRAMMAR_SVC --> NEO_MAIN
    LEARNING_SVC --> PG_MAIN
    LEARNING_SVC --> NEO_MAIN
    ANALYTICS_SVC --> PG_MAIN
    
    AI_SVC --> EMBEDDING
    AI_SVC --> OPENAI_API
    AI_SVC --> GEMINI_API
    
    PG_MAIN --> PG_VECTOR
    PG_MAIN --> PG_TABLES
    
    NEO_MAIN --> NEO_VECTOR
    NEO_MAIN --> NEO_NODES
    NEO_MAIN --> NEO_RELS
    
    STREAMLIT_APP --> VALIDATION
    STREAMLIT_APP --> ADMIN
    VALIDATION --> NEO_MAIN
    ADMIN --> API
    
    style NEXT_APP fill:#3b82f6,stroke:#1e40af,color:#fff
    style API fill:#10b981,stroke:#059669,color:#fff
    style PG_MAIN fill:#8b5cf6,stroke:#6d28d9,color:#fff
    style NEO_MAIN fill:#f59e0b,stroke:#d97706,color:#fff
    style OPENAI_API fill:#6366f1,stroke:#4f46e5,color:#fff
    style GEMINI_API fill:#ec4899,stroke:#db2777,color:#fff
    style STREAMLIT_APP fill:#14b8a6,stroke:#0d9488,color:#fff
```

---

<## Graf 3: Data Flow - Chat Tutoring

```mermaid
sequenceDiagram
    participant U as Student
    participant FE as Next.js Frontend
    participant BE as FastAPI Backend
    participant PG as PostgreSQL
    participant NEO as Neo4j
    participant AI as AI Router
    participant LLM as OpenAI/Gemini
    
    U->>FE: Unos poruke u chat
    FE->>FE: Validacija i priprema
    FE->>BE: POST /api/v1/conversations/sessions/{id}/messages<br/>(JWT Token)
    
    BE->>BE: Verifikacija JWT
    BE->>PG: Spremi korisničku poruku<br/>(conversation_messages)
    
    BE->>NEO: Semantičko pretraživanje<br/>(Pronađi relevantne koncepte)
    NEO-->>BE: Vraća povezane gramatičke obrasce<br/>i vokabular
    
    BE->>BE: Generiraj embedding za poruku<br/>(pgvector ili AI provider)
    
    BE->>AI: Route request<br/>(task_type, complexity)
    AI->>AI: Odaberi optimalni model<br/>(cost, performance, task)
    
    AI->>LLM: Generate reply<br/>(prompt + context + knowledge)
    LLM-->>AI: Streaming response<br/>(tokens + metadata)
    
    AI-->>BE: Reply payload<br/>(content, tokens_used, model)
    
    BE->>PG: Spremi AI odgovor<br/>(conversation_messages + metadata)
    BE->>PG: Ažuriraj analytics<br/>(conversation_analytics)
    
    BE-->>FE: Stream SSE<br/>(event: message, data: tokens)
    FE->>FE: Render streaming text
    FE-->>U: Prikaži AI odgovor u real-time
    
    Note over BE,PG: Embedding se generira i sprema<br/>za buduće semantičko pretraživanje
    Note over BE,NEO: Graf znanja se koristi za<br/>personalizaciju konteksta
```

---

## Graf 4: Graf Znanja - Struktura

```mermaid
graph LR
    subgraph "Neo4j Knowledge Graph"
        subgraph "Node Types"
            W[Word Nodes<br/>138,153]
            GP[GrammarPattern Nodes<br/>392]
            GC[GrammarClassification<br/>63]
            MT[MarugotoTopic<br/>55]
            JFS[JFSCategory<br/>25]
            TL[TextbookLevel<br/>6]
        end
        
        subgraph "Relationship Types"
            R1[SYNONYM_OF<br/>173,425]
            R2[SIMILAR_TO<br/>4,448]
            R3[PREREQUISITE_FOR<br/>3,654]
            R4[USES_WORD<br/>2,046]
            R5[DOMAIN_OF<br/>803]
            R6[BELONGS_TO_LEVEL<br/>392]
            R7[HAS_CLASSIFICATION<br/>392]
            R8[CATEGORIZED_AS<br/>392]
            R9[ANTONYM_OF<br/>265]
        end
        
        subgraph "Vector Search"
            VS[Vector Indexes<br/>Semantic Search<br/>Embeddings]
        end
    end
    
    GP -->|PREREQUISITE_FOR| GP
    GP -->|USES_WORD| W
    GP -->|BELONGS_TO_LEVEL| TL
    GP -->|HAS_CLASSIFICATION| GC
    GP -->|CATEGORIZED_AS| JFS
    W -->|SYNONYM_OF| W
    W -->|SIMILAR_TO| W
    W -->|ANTONYM_OF| W
    MT -->|DOMAIN_OF| TL
    
    GP -.->|Vector Search| VS
    W -.->|Vector Search| VS
    
    style W fill:#f59e0b,stroke:#d97706,color:#fff
    style GP fill:#3b82f6,stroke:#1e40af,color:#fff
    style VS fill:#10b981,stroke:#059669,color:#fff
```

---

## Graf 5: Layered Architecture (Pojednostavljen)

```mermaid
graph TB
    subgraph "Presentation Layer"
        WEB_UI[Web UI<br/>Next.js + React]
        ADMIN_UI[Admin UI<br/>Streamlit]
    end
    
    subgraph "Application Layer"
        API[FastAPI REST API<br/>22+ endpoints]
        AUTH_SVC[Authentication<br/>JWT]
        BUSINESS[Business Logic<br/>Services]
    end
    
    subgraph "Data Access Layer"
        ORM[SQLAlchemy ORM<br/>Alembic Migrations]
        NEO_DRIVER[Neo4j Driver<br/>Cypher Queries]
        VECTOR[Vector Search<br/>pgvector + Neo4j Vectors]
    end
    
    subgraph "Data Storage Layer"
        PG[(PostgreSQL<br/>User Data<br/>Conversations<br/>Embeddings)]
        NEO[(Neo4j<br/>Knowledge Graph<br/>138K nodes<br/>185K relationships)]
    end
    
    subgraph "External Services Layer"
        AI[AI Providers<br/>OpenAI + Gemini]
        CLOUD[Google Cloud<br/>Speech/TTS]
    end
    
    WEB_UI --> API
    ADMIN_UI --> API
    
    API --> AUTH_SVC
    API --> BUSINESS
    
    BUSINESS --> ORM
    BUSINESS --> NEO_DRIVER
    BUSINESS --> VECTOR
    
    ORM --> PG
    NEO_DRIVER --> NEO
    VECTOR --> PG
    VECTOR --> NEO
    
    BUSINESS --> AI
    WEB_UI --> CLOUD
    
    style WEB_UI fill:#3b82f6,stroke:#1e40af,color:#fff
    style API fill:#10b981,stroke:#059669,color:#fff
    style PG fill:#8b5cf6,stroke:#6d28d9,color:#fff
    style NEO fill:#f59e0b,stroke:#d97706,color:#fff
    style AI fill:#6366f1,stroke:#4f46e5,color:#fff
```

---

## Graf 6: Komponente i Tehnologije (Mindmap)

```mermaid
mindmap
  root((AI Language<br/>Tutor))
    Frontend
      Next.js 14+
      TypeScript
      React 18+
      Tailwind CSS
      Shadcn/UI
      TanStack Query
      Zustand
      Web Audio APIs
    Backend
      FastAPI
      Python 3.11+
      JWT Auth
      SQLAlchemy
      Alembic
      Pytest
    Databases
      PostgreSQL
        pgvector
        User Data
        Conversations
        Analytics
      Neo4j AuraDB
        138,691 Nodes
        185,817 Relationships
        Vector Indexes
        Cypher Queries
    AI Services
      OpenAI
        GPT-4o
        GPT-4o-mini
        o1-preview
        o1-mini
        Embeddings
      Google Gemini
        Gemini 2.5 Pro
        Gemini 2.5 Flash
        Embeddings
      AI Router
        Model Selection
        Cost Optimization
    Validation
      Streamlit
      Human Review
      Quality Metrics
      Multi-Reviewer
    External
      Google Cloud
        Speech-to-Text
        Text-to-Speech
      Docker
      GitHub Actions
```

---

## Kako Generirati Grafove

### Opcija 1: Mermaid Live Editor (Preporučeno)
1. Idite na: https://mermaid.live/
2. Kopirajte bilo koji graf iznad
3. Graf će se automatski generirati
4. Kliknite "Actions" → "Download PNG/SVG" za eksport

### Opcija 2: VS Code
1. Instalirajte ekstenziju "Markdown Preview Mermaid Support"
2. Otvorite ovaj fajl u VS Code
3. Grafovi će se automatski renderirati u preview modu

### Opcija 3: GitHub
1. Uploadajte ovaj fajl na GitHub
2. GitHub automatski renderira Mermaid grafove u markdown fajlovima

### Opcija 4: Online Tools
- https://mermaid-js.github.io/mermaid-live-editor/
- https://kroki.io/ (podržava Mermaid)
- https://www.diagrams.net/ (može importati Mermaid)

### Opcija 5: PowerPoint/Google Slides
1. Generirajte PNG/SVG iz Mermaid Live Editor
2. Importajte u PowerPoint ili Google Slides
3. Ili koristite Mermaid add-on za Google Slides

---

## Preporuke za Prezentaciju

### Za Slide:
- **Graf 1 (High-Level)** - Najbolji za uvod u arhitekturu
- **Graf 3 (Data Flow)** - Prikazuje kako sustav radi u praksi
- **Graf 4 (Graf Znanja)** - Vizualizacija strukture znanja

### Za Dokumentaciju:
- **Graf 2 (Detaljna)** - Kompletan tehnički pregled
- **Graf 5 (Layered)** - Pojednostavljena arhitektura
- **Graf 6 (Mindmap)** - Pregled tehnologija

---

## Prilagođavanje Grafova

Svi grafovi su u Mermaid formatu i mogu se lako mijenjati:
- Promjena boja: `style NODE fill:#color`
- Dodavanje čvorova: `NODE[Label]`
- Dodavanje relacija: `NODE1 --> NODE2`
- Promjena tipa grafa: `graph TB` → `graph LR` → `sequenceDiagram`

---

**Kreirano:** 6. studenog 2025.  
**Za:** TheCUC Konferencija, Rovinj, 7. studenog 2025.




