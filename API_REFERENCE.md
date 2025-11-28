# 🌐 AI Language Tutor API Reference

**Base URL**: `http://localhost:8000`  
**API Version**: v1  
**Interactive Docs**: http://localhost:8000/docs

## 🔐 Authentication

All protected endpoints require a JWT token in the Authorization header:
```
Authorization: Bearer <your_jwt_token>
```

## 📋 Endpoints Overview

### Health & Status
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Basic health check |
| GET | `/api/v1/health` | API health check |
| GET | `/api/v1/health/detailed` | Detailed health with database connectivity |

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/register` | User registration |
| POST | `/api/v1/auth/login` | User login |
| GET | `/api/v1/auth/me` | Get current user profile |
| PUT | `/api/v1/auth/profile` | Update user profile |
| POST | `/api/v1/auth/change-password` | Change password |
| POST | `/api/v1/auth/deactivate` | Deactivate account |
| GET | `/api/v1/auth/verify-token` | Verify JWT token |

### Conversations
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/conversations/sessions` | Create conversation session |
| GET | `/api/v1/conversations/sessions` | List user sessions |
| GET | `/api/v1/conversations/sessions/{session_id}` | Get session details |
| PUT | `/api/v1/conversations/sessions/{session_id}` | Update session (title) |
| POST | `/api/v1/conversations/sessions/{session_id}/messages` | Add message to session |
| GET | `/api/v1/conversations/sessions/{session_id}/messages` | List session messages |

### Dialogue Generation (CanDo)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/cando/dialogue/new` | Generate a fresh dialogue with contextual setting |
| POST | `/api/v1/cando/dialogue/extend` | Continue an existing dialogue within same domain |
| POST | `/api/v1/cando/dialogue/store` | Store a generated dialogue for later use |

#### Request/Response Examples

Generate new dialogue:
```http
POST /api/v1/cando/dialogue/new
Content-Type: application/json

{
  "can_do_id": "JF_105",
  "seed_setting": "At a city hall counter, a newcomer asks about residence registration.",
  "vocabulary": ["住所", "申請", "必要書類"],
  "grammar_patterns": ["〜なければならない"],
  "num_turns": 6,
  "characters": ["Clerk", "Newcomer"]
}
```
Response (abridged):
```json
{
  "setting": "市役所の窓口で…",
  "characters": ["Clerk", "Newcomer"],
  "dialogue_turns": [
    { "speaker": "Clerk", "japanese": { "kanji": "いらっしゃいませ…", "romaji": "...", "furigana": [], "translation": "..." } }
  ]
}
```

Extend dialogue:
```http
POST /api/v1/cando/dialogue/extend
Content-Type: application/json

{
  "can_do_id": "JF_105",
  "setting": "市役所の窓口で…",
  "dialogue_turns": [ { "speaker": "Clerk", "japanese": { "kanji": "…" } } ],
  "num_turns": 3
}
```

Store dialogue:
```http
POST /api/v1/cando/dialogue/store
Content-Type: application/json

{
  "can_do_id": "JF_105",
  "dialogue_card": { "setting": "…", "characters": ["A","B"], "dialogue_turns": [] }
}
```

### Knowledge & Lexical Graph
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/knowledge/health` | Knowledge graph health check |
| GET | `/api/v1/knowledge/search` | Search knowledge graph |
| GET | `/api/v1/knowledge/embeddings/status` | Check embeddings status |
| GET | `/api/v1/lexical/graph?center=<word>&searchField=<kanji|hiragana|translation>&depth=<n>` | Get lexical ego-graph |
| GET | `/api/v1/lexical/node/{word}` | Get lexical node details |
#### Lexical Graph Schema Guarantees

```json
{
  "nodes": [
    { "id": "日本", "name": "日本", "hiragana": "にほん", "translation": "Japan", "level": 1, "pos": "noun", "domain": "geography" }
  ],
  "links": [
    { "source": "日本", "target": "東京", "weight": 1.0 }
  ],
  "center": { "id": "日本" }
}
```

- `nodes[*].id` is always a non-empty string and unique within the response.
- `links[*].source` and `links[*].target` are always non-empty strings that reference existing node ids in `nodes`.
- `weight` is numeric; if missing or invalid, defaults to 1.0.
- Self-loop links are omitted.

### Content Analysis
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/content/analyze` | Analyze text content |
| POST | `/api/v1/content/analyze-url` | Analyze content from URL |
| POST | `/api/v1/content/analyze-upload` | Analyze uploaded file |
| POST | `/api/v1/content/analyze-persist` | Analyze and persist to Neo4j |
| GET | `/api/v1/content/term` | Verify persisted term in Neo4j |

### Learning & Personalization
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/learning/dashboard` | Get personalized learning dashboard |
| GET | `/api/v1/learning/diagnostic/quiz` | Get diagnostic quiz |
| POST | `/api/v1/learning/diagnostic/grade` | Grade quiz responses |

### Spaced Repetition System (SRS)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/srs/schedule` | Schedule SRS review |

### Analytics
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/analytics/summary` | Get conversation analytics summary |

### Admin & RBAC
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/admin/health` | Admin health check (requires admin role) |

## 📝 Detailed Endpoint Documentation

### Authentication Endpoints

#### Register User
```http
POST /api/v1/auth/register
Content-Type: application/json

{
  "username": "testuser",
  "email": "test@example.com",
  "password": "securepassword123",
  "full_name": "Test User"
}
```

**Response:**
```json
{
  "id": 1,
  "username": "testuser",
  "email": "test@example.com",
  "full_name": "Test User",
  "is_active": true,
  "created_at": "2024-01-01T00:00:00Z"
}
```

#### Login User
```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "username": "testuser",
  "password": "securepassword123"
}
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "username": "testuser",
    "email": "test@example.com",
    "full_name": "Test User"
  }
}
```

### Content Analysis Endpoints

#### Analyze Text Content
```http
POST /api/v1/content/analyze
Content-Type: application/json

{
  "text": "Hello world, this is a test sentence with multiple words.",
  "source": {
    "title": "Test Document",
    "language": "en",
    "author": "Test Author",
    "url": "https://example.com"
  }
}
```

**Response:**
```json
{
  "status": "ok",
  "processed_chars": 58,
  "items": [
    {
      "kind": "vocabulary",
      "value": "Hello",
      "confidence": 0.9
    },
    {
      "kind": "vocabulary", 
      "value": "world",
      "confidence": 0.9
    }
  ],
  "source": {
    "title": "Test Document",
    "language": "en",
    "author": "Test Author",
    "url": "https://example.com"
  },
  "analyzed_at": "2024-01-01T00:00:00Z"
}
```

#### Analyze and Persist to Neo4j
```http
POST /api/v1/content/analyze-persist?min_confidence=0.7
Content-Type: application/json

{
  "text": "Hello world, this is a test sentence with multiple words.",
  "source": {
    "title": "Test Document",
    "language": "en"
  }
}
```

**Response:**
```json
{
  "status": "ok",
  "processed_chars": 58,
  "items": [
    {
      "kind": "vocabulary",
      "value": "Hello",
      "confidence": 0.9
    },
    {
      "kind": "vocabulary",
      "value": "world", 
      "confidence": 0.9
    }
  ],
  "source": {
    "title": "Test Document",
    "language": "en"
  },
  "analyzed_at": "2024-01-01T00:00:00Z",
  "persisted": true,
  "persisted_count": 2
}
```

### Conversation Endpoints

#### Create Conversation Session
```http
POST /api/v1/conversations/sessions
Authorization: Bearer <token>
Content-Type: application/json

{
  "title": "My Learning Session",
  "language": "ja",
  "level": "beginner"
}
```

**Response:**
```json
{
  "id": 1,
  "title": "My Learning Session",
  "language": "ja",
  "level": "beginner",
  "user_id": 1,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

#### Add Message to Session
```http
POST /api/v1/conversations/sessions/1/messages
Authorization: Bearer <token>
Content-Type: application/json

{
  "content": "Hello, I want to learn Japanese",
  "role": "user"
}
```

**Response:**
```json
{
  "user_message": { "id": "...", "order": 1, "created_at": "..." },
  "assistant_message": { "id": "...", "order": 2, "created_at": "..." }
}
```

- Stores the user message, then generates an assistant reply using the session’s `ai_provider` and `ai_model` (OpenAI or Gemini) with keys from `.env`.
- If AI generation fails, the endpoint still returns success for the user message with `assistant_message: null`.

### Learning Endpoints

#### Get Learning Dashboard
```http
GET /api/v1/learning/dashboard
Authorization: Bearer <token>
```

**Response:**
```json
{
  "user_id": 1,
  "total_sessions": 5,
  "total_messages": 25,
  "learning_streak": 3,
  "current_level": "beginner",
  "languages": ["ja"],
  "recent_activity": [
    {
      "date": "2024-01-01",
      "sessions": 2,
      "messages": 10
    }
  ]
}
```

#### Get Diagnostic Quiz
```http
GET /api/v1/learning/diagnostic/quiz
Authorization: Bearer <token>
```

**Response:**
```json
{
  "quiz_id": "diagnostic_001",
  "questions": [
    {
      "id": 1,
      "type": "multiple_choice",
      "question": "What does 'こんにちは' mean?",
      "options": ["Good morning", "Good afternoon", "Good evening", "Goodbye"],
      "correct_answer": 1
    }
  ]
}
```

### SRS Endpoints

#### Schedule SRS Review
```http
POST /api/v1/srs/schedule
Authorization: Bearer <token>
Content-Type: application/json

{
  "item_id": "word:日本",
  "last_interval_days": 1,
  "grade": "good"
}
```

**Response:**
```json
{
  "item_id": "word:日本",
  "next_review_days": 3,
  "next_review_date": "2024-01-04T00:00:00Z",
  "interval": 3,
  "ease_factor": 2.5
}
```

## 🔧 Error Responses

### Standard Error Format
```json
{
  "detail": "Error message description"
}
```

### Common HTTP Status Codes
- `200` - Success
- `201` - Created
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `422` - Validation Error
- `500` - Internal Server Error

### Example Error Responses

#### Validation Error (422)
```json
{
  "detail": [
    {
      "loc": ["body", "password"],
      "msg": "Password must be at least 8 characters long",
      "type": "value_error"
    }
  ]
}
```

#### Authentication Error (401)
```json
{
  "detail": "Invalid credentials"
}
```

## 🧪 Testing

### Quick Test with PowerShell
```powershell
# Test health endpoint
Invoke-RestMethod -Uri "http://localhost:8000/health"

# Test content analysis
$body = @{
    text = "Hello world, this is a test sentence."
    source = @{
        title = "Test Document"
        language = "en"
    }
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/api/v1/content/analyze" -Method POST -Body $body -ContentType "application/json"
```

### Run Full Test Suite
```powershell
.\scripts\run_tests.ps1
```

## 📊 Rate Limits

Currently, no rate limits are implemented. Future versions will include:
- Per-user rate limiting
- Per-endpoint rate limiting
- Burst protection

## 🔒 Security Notes

- All sensitive endpoints require JWT authentication
- Passwords are hashed using bcrypt
- JWT tokens expire after 24 hours
- CORS is configured for development
- Input validation is enforced on all endpoints

---

**For interactive API exploration, visit**: http://localhost:8000/docs
