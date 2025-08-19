# Grammar Integration Service - Usage Guide

## 🎯 Overview

The Grammar Integration Service provides access to **392 Japanese grammar patterns** from the Marugoto textbook series with **185,817 relationships** stored in Neo4j. The service offers comprehensive APIs for grammar learning, pattern discovery, and personalized recommendations.

## 🚀 Quick Start

### 1. Start the Backend Service
```powershell
cd backend
uvicorn app.main:app --reload --port 8000
```

### 2. Access API Documentation
Visit: `http://localhost:8000/docs` and look for the **Grammar** section

### 3. Test the Service
```powershell
cd tests
python test_grammar_integration.py
```

## 📚 Available API Endpoints

### Core Pattern Endpoints

#### Get Grammar Patterns
```bash
GET /api/v1/grammar/patterns
```

**Query Parameters:**
- `level` - Filter by textbook level (e.g., "入門(りかい)", "初級1(りかい)")
- `classification` - Filter by grammar function (e.g., "説明", "時間的前後")
- `jfs_category` - Filter by JFS topic (e.g., "自分と家族", "食生活")
- `search` - Search in pattern text or examples
- `limit` - Number of results (1-100, default: 20)
- `offset` - Pagination offset (default: 0)

**Example Request:**
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8000/api/v1/grammar/patterns?level=入門(りかい)&limit=10"
```

#### Get Specific Pattern
```bash
GET /api/v1/grammar/patterns/{pattern_id}
```

#### Find Similar Patterns
```bash
GET /api/v1/grammar/patterns/{pattern_id}/similar
```

#### Get Prerequisites
```bash
GET /api/v1/grammar/patterns/{pattern_id}/prerequisites
```

### Learning Features

#### Generate Learning Path
```bash
GET /api/v1/grammar/learning-path?from_pattern={pattern_id}&to_level={target_level}
```

#### Get Personalized Recommendations
```bash
GET /api/v1/grammar/recommendations?user_level={level}&known_patterns={pattern_ids}
```

#### Find Patterns by Word
```bash
GET /api/v1/grammar/patterns/by-word/{japanese_word}
```

### Metadata Endpoints

#### Get All Levels
```bash
GET /api/v1/grammar/levels
```

#### Get All Classifications
```bash
GET /api/v1/grammar/classifications
```

#### Get JFS Categories
```bash
GET /api/v1/grammar/jfs-categories
```

#### Get Grammar Statistics
```bash
GET /api/v1/grammar/stats
```

## 💻 Frontend Integration

### React Component Usage

#### Basic Pattern Display
```typescript
import { useEffect, useState } from 'react';
import GrammarPatternCard from '@/components/grammar/GrammarPatternCard';

function GrammarList() {
  const [patterns, setPatterns] = useState([]);
  
  useEffect(() => {
    fetch('/api/v1/grammar/patterns?limit=20')
      .then(res => res.json())
      .then(setPatterns);
  }, []);
  
  return (
    <div className="grid gap-4">
      {patterns.map(pattern => (
        <GrammarPatternCard
          key={pattern.id}
          pattern={pattern}
          onStudy={(id) => console.log('Study:', id)}
          onPlayAudio={(text) => console.log('Play:', text)}
        />
      ))}
    </div>
  );
}
```

#### Learning Path Generation
```typescript
import GrammarLearningPath from '@/components/grammar/GrammarLearningPath';

function LearningPathDemo() {
  const [learningPath, setLearningPath] = useState(null);
  
  const generatePath = async (fromPattern: string, toLevel: string) => {
    const response = await fetch(
      `/api/v1/grammar/learning-path?from_pattern=${fromPattern}&to_level=${toLevel}`
    );
    const pathData = await response.json();
    setLearningPath(pathData);
  };
  
  return (
    <div>
      <button onClick={() => generatePath('grammar_001', '初級1(りかい)')}>
        Generate Learning Path
      </button>
      
      {learningPath && (
        <GrammarLearningPath
          learningPath={learningPath}
          onPatternClick={(id) => console.log('Pattern clicked:', id)}
          onStartLearning={(id) => console.log('Start learning:', id)}
        />
      )}
    </div>
  );
}
```

### Full Grammar Page
The complete grammar interface is available at:
- **Route**: `/grammar`
- **Component**: `frontend/src/app/grammar/page.tsx`

## 🧠 Service Layer Usage

### Backend Service Integration

```python
from app.services.grammar_service import GrammarService
from app.db import get_neo4j_session

# Initialize service
async def use_grammar_service():
    async with get_neo4j_session() as session:
        grammar_service = GrammarService(session)
        
        # Get patterns for beginners
        beginner_patterns = await grammar_service.get_patterns(
            level="入門(りかい)",
            limit=10
        )
        
        # Find similar patterns
        similar = await grammar_service.get_similar_patterns("grammar_001")
        
        # Get personalized recommendations
        recommendations = await grammar_service.get_personalized_recommendations(
            user_level="入門(りかい)",
            known_patterns=["grammar_001", "grammar_002"],
            focus_classification="説明"
        )
        
        return {
            "patterns": beginner_patterns,
            "similar": similar,
            "recommendations": recommendations
        }
```

## 🎯 Common Use Cases

### 1. Browse Grammar Patterns by Level
```typescript
// Get all beginner patterns
const beginnerPatterns = await fetch('/api/v1/grammar/patterns?level=入門(りかい)')
  .then(res => res.json());
```

### 2. Search for Specific Grammar
```typescript
// Search for patterns containing "です"
const desuPatterns = await fetch('/api/v1/grammar/patterns?search=です')
  .then(res => res.json());
```

### 3. Get Learning Recommendations
```typescript
// Get personalized recommendations
const recommendations = await fetch(
  '/api/v1/grammar/recommendations?user_level=入門(りかい)&limit=5'
).then(res => res.json());
```

### 4. Generate Study Path
```typescript
// Create learning path from basic to intermediate
const learningPath = await fetch(
  '/api/v1/grammar/learning-path?from_pattern=grammar_001&to_level=初級1(りかい)'
).then(res => res.json());
```

### 5. Find Patterns Using Specific Words
```typescript
// Find patterns that use the word "です"
const wordPatterns = await fetch('/api/v1/grammar/patterns/by-word/です')
  .then(res => res.json());
```

## 🔧 Integration with Other Services

### AI Chat Integration
```python
# In conversation service
async def enhance_response_with_grammar(user_message: str, ai_response: str):
    grammar_service = GrammarService(neo4j_session)
    
    # Find relevant grammar patterns in user's message
    patterns = await grammar_service.search_patterns(user_message)
    
    if patterns:
        # Add grammar explanations to AI response
        grammar_info = f"\n\n📝 Grammar Note: This uses the pattern '{patterns[0]['pattern']}'"
        return ai_response + grammar_info
    
    return ai_response
```

### Spaced Repetition Integration
```python
# In SRS service
async def get_grammar_for_review(user_id: str, user_level: str):
    grammar_service = GrammarService(neo4j_session)
    
    # Get patterns user should review
    recommendations = await grammar_service.get_personalized_recommendations(
        user_level=user_level,
        known_patterns=await get_user_known_patterns(user_id),
        limit=5
    )
    
    return recommendations["recommended_patterns"]
```

## 📊 Data Structure

### Grammar Pattern Object
```typescript
interface GrammarPattern {
  id: string;                    // Unique identifier
  sequence_number: number;       // Order in textbook
  pattern: string;              // Japanese grammar pattern
  pattern_romaji: string;       // Romanized version
  textbook_form: string;        // Form as shown in textbook
  textbook_form_romaji: string; // Romanized textbook form
  example_sentence: string;     // Example usage
  example_romaji: string;       // Romanized example
  classification: string;       // Grammar function type
  textbook: string;            // Source textbook level
  topic: string;               // Lesson topic
  lesson: string;              // Specific lesson
  jfs_category: string;        // JFS topic category
}
```

## 🧪 Testing the Service

### Run Integration Tests
```powershell
# Test the grammar service
python tests/test_grammar_integration.py

# Run all grammar-related tests
pytest tests/ -k grammar -v
```

### Manual API Testing
```powershell
# Start backend
cd backend
uvicorn app.main:app --reload --port 8000

# In another terminal, test endpoints
curl -X GET "http://localhost:8000/api/v1/grammar/patterns?limit=5" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## 🎨 Frontend Usage

### Navigate to Grammar Page
1. Start the frontend: `cd frontend && npm run dev`
2. Visit: `http://localhost:3000/grammar`
3. Use the interface to:
   - Browse patterns by level/classification
   - Search for specific patterns
   - Generate learning paths
   - Get personalized recommendations

### Component Integration
The grammar components are available for reuse:
- `GrammarPatternCard` - Display individual patterns
- `GrammarLearningPath` - Show learning progression

## 🔐 Authentication Required

All grammar endpoints require authentication. Make sure to:
1. Register a user account
2. Login to get an access token
3. Include the token in requests: `Authorization: Bearer YOUR_TOKEN`

## 📈 Available Data

The service provides access to:
- **392 Grammar Patterns** from Marugoto textbooks
- **6 Textbook Levels** (入門 to 中級2)
- **Multiple Classifications** (説明, 時間的前後, etc.)
- **JFS Categories** (topic-based organization)
- **185,817 Relationships** between patterns

## 🚨 Troubleshooting

### Common Issues

1. **401 Unauthorized**: Make sure you're including the Bearer token
2. **404 Not Found**: Check that the grammar router is included in the main API
3. **500 Internal Error**: Verify Neo4j connection is working

### Debug Steps
```powershell
# Check if backend is running
curl http://localhost:8000/api/v1/health

# Test authentication
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"your_user","password":"your_pass"}'

# Test grammar endpoint
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8000/api/v1/grammar/stats"
```

## 🎓 Next Steps

1. **Test the Service**: Run the integration test to verify everything works
2. **Explore the Data**: Use the `/grammar/stats` endpoint to see what's available
3. **Build Learning Features**: Integrate grammar patterns into your AI conversations
4. **Enhance UI**: Customize the frontend components for your needs

The grammar integration service is now ready to power intelligent Japanese language learning in your AI tutor! 🚀
