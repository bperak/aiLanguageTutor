# AI Language Tutor - Multi-Provider AI Architecture

## 🎯 Overview

This document outlines the multi-provider AI architecture for the AI Language Tutor application, enabling seamless integration with both OpenAI and Google Gemini models for optimal performance, cost efficiency, and reliability.

## 🏗️ Architecture Principles

### 1. **Provider Agnostic Design**
- Unified interface abstracts provider-specific implementations
- Easy to add new AI providers without changing business logic
- Consistent response formats across all providers

### 2. **Intelligent Routing**
- Task-based model selection for optimal performance
- Cost-aware routing to minimize expenses
- Automatic fallback mechanisms for reliability

### 3. **Performance Optimization**
- Real-time monitoring of response times and quality
- Caching strategies for frequently requested content
- Load balancing across multiple models

## 🤖 AI Provider Configuration

### OpenAI Models

| Model | Use Case | Strengths | Cost |
|-------|----------|-----------|------|
| **GPT-4o** | Complex grammar explanations, detailed content generation | Highest quality, excellent reasoning | High |
| **GPT-4o-mini** | Quick responses, simple interactions, bulk processing | Fast, cost-effective, good quality | Low |
| **o1-preview** | Advanced reasoning, complex linguistic analysis | Superior reasoning capabilities | Very High |
| **o1-mini** | Structured reasoning tasks, specific analysis | Good reasoning, more affordable | Medium |
| **text-embedding-3-large** | Vector embeddings for semantic search | High-quality embeddings, 3072 dimensions | Medium |

### Google Gemini Models

| Model | Use Case | Strengths | Cost |
|-------|----------|-----------|------|
| **Gemini 2.5 Pro** | Complex multimodal tasks, high-context analysis | Excellent context window, multimodal | High |
| **Gemini 2.5 Flash** | Real-time interactions, fast responses | Very fast inference, cost-effective | Low |

## 🔀 Intelligent Routing System

### Task-Based Routing

```python
class TaskType(Enum):
    GRAMMAR_GENERATION = "grammar_generation"
    QUICK_RESPONSE = "quick_response" 
    COMPLEX_REASONING = "complex_reasoning"
    CONTENT_EMBEDDING = "content_embedding"
    REAL_TIME_CHAT = "real_time_chat"
    BULK_PROCESSING = "bulk_processing"
    MULTIMODAL_ANALYSIS = "multimodal_analysis"

class ComplexityLevel(Enum):
    LOW = "low"
    MEDIUM = "medium" 
    HIGH = "high"
    CRITICAL = "critical"

ROUTING_RULES = {
    (TaskType.GRAMMAR_GENERATION, ComplexityLevel.HIGH): ("openai", "gpt-4o"),
    (TaskType.GRAMMAR_GENERATION, ComplexityLevel.MEDIUM): ("gemini", "gemini-2.5-pro"),
    (TaskType.QUICK_RESPONSE, ComplexityLevel.LOW): ("gemini", "gemini-2.5-flash"),
    (TaskType.COMPLEX_REASONING, ComplexityLevel.HIGH): ("openai", "o1-preview"),
    (TaskType.COMPLEX_REASONING, ComplexityLevel.MEDIUM): ("openai", "gpt-4o"),
    (TaskType.REAL_TIME_CHAT, ComplexityLevel.LOW): ("gemini", "gemini-2.5-flash"),
    (TaskType.BULK_PROCESSING, ComplexityLevel.LOW): ("openai", "gpt-4o-mini"),
    (TaskType.CONTENT_EMBEDDING, ComplexityLevel.MEDIUM): ("openai", "text-embedding-3-large"),
}
```

### Cost Optimization Strategy

```python
class CostOptimizer:
    def __init__(self):
        self.cost_per_token = {
            "gpt-4o": {"input": 0.0025, "output": 0.01},
            "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
            "o1-preview": {"input": 0.015, "output": 0.06},
            "gemini-2.5-pro": {"input": 0.00125, "output": 0.005},
            "gemini-2.5-flash": {"input": 0.000075, "output": 0.0003},
        }
    
    def estimate_cost(self, provider: str, model: str, input_tokens: int, output_tokens: int) -> float:
        costs = self.cost_per_token.get(model, {"input": 0, "output": 0})
        return (input_tokens * costs["input"] + output_tokens * costs["output"]) / 1000
    
    def select_cost_effective_model(self, task_type: TaskType, estimated_tokens: int) -> tuple:
        # Select the most cost-effective model that meets quality requirements
        candidates = self._get_suitable_models(task_type)
        return min(candidates, key=lambda x: self.estimate_cost(x[0], x[1], estimated_tokens, estimated_tokens))
```

## 🛠️ Implementation Architecture

### 1. Core AI Service Layer

```python
# app/services/ai_provider_service.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from openai import OpenAI
from google import genai

class AIProvider(ABC):
    @abstractmethod
    async def generate_content(self, prompt: str, **kwargs) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    async def create_embedding(self, text: str, **kwargs) -> List[float]:
        pass

class OpenAIProvider(AIProvider):
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
    
    async def generate_content(self, prompt: str, model: str = "gpt-4o-mini", **kwargs) -> Dict[str, Any]:
        response = await self.client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            **kwargs
        )
        return {
            "content": response.choices[0].message.content,
            "usage": response.usage.dict(),
            "model": model,
            "provider": "openai"
        }

class GeminiProvider(AIProvider):
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)
    
    async def generate_content(self, prompt: str, model: str = "gemini-2.5-flash", **kwargs) -> Dict[str, Any]:
        response = await self.client.models.generate_content(
            model=model,
            contents=prompt,
            **kwargs
        )
        return {
            "content": response.text,
            "usage": {"total_tokens": len(response.text.split())},  # Approximate
            "model": model,
            "provider": "gemini"
        }

class AIProviderService:
    def __init__(self, openai_key: str, gemini_key: str):
        self.providers = {
            "openai": OpenAIProvider(openai_key),
            "gemini": GeminiProvider(gemini_key)
        }
        self.router = ModelRouter()
        self.monitor = PerformanceMonitor()
    
    async def generate_content(
        self, 
        prompt: str, 
        task_type: TaskType,
        complexity: ComplexityLevel = ComplexityLevel.MEDIUM,
        **kwargs
    ) -> Dict[str, Any]:
        # Route request to optimal provider/model
        provider_name, model = self.router.route_request(task_type, complexity)
        provider = self.providers[provider_name]
        
        try:
            # Execute request with monitoring
            start_time = time.time()
            result = await provider.generate_content(prompt, model=model, **kwargs)
            end_time = time.time()
            
            # Record performance metrics
            self.monitor.record_request(
                provider=provider_name,
                model=model,
                task_type=task_type,
                response_time=end_time - start_time,
                success=True
            )
            
            return result
            
        except Exception as e:
            # Implement fallback logic
            return await self._handle_fallback(prompt, task_type, complexity, e, **kwargs)
    
    async def _handle_fallback(self, prompt: str, task_type: TaskType, complexity: ComplexityLevel, error: Exception, **kwargs):
        # Get fallback provider/model
        fallback_provider, fallback_model = self.router.get_fallback(task_type, complexity)
        
        if fallback_provider and fallback_provider in self.providers:
            try:
                provider = self.providers[fallback_provider]
                result = await provider.generate_content(prompt, model=fallback_model, **kwargs)
                
                # Mark as fallback in response
                result["fallback"] = True
                result["original_error"] = str(error)
                
                return result
            except Exception as fallback_error:
                # Log both errors and raise
                logger.error(f"Primary error: {error}, Fallback error: {fallback_error}")
                raise fallback_error
        
        raise error
```

### 2. Configuration Management

```python
# app/core/config.py
from pydantic import BaseSettings
from typing import Dict, Any

class AIConfig(BaseSettings):
    # Provider API Keys
    openai_api_key: str
    openai_organization_id: Optional[str] = None
    gemini_api_key: str
    google_cloud_project_id: str
    
    # Routing Configuration
    default_provider: str = "openai"
    fallback_enabled: bool = True
    cost_optimization: bool = True
    performance_monitoring: bool = True
    
    # Model Defaults
    openai_default_model: str = "gpt-4o-mini"
    gemini_default_model: str = "gemini-2.5-flash"
    
    # Performance Settings
    ai_request_timeout: int = 30
    ai_max_retries: int = 3
    max_concurrent_requests: int = 10
    
    # Cost Limits
    daily_cost_limit: float = 50.0
    cost_alert_threshold: float = 0.8
    
    class Config:
        env_file = ".env"
        case_sensitive = False
```

### 3. Performance Monitoring

```python
# app/services/monitoring.py
from dataclasses import dataclass
from typing import Dict, List
import time
from collections import defaultdict

@dataclass
class RequestMetric:
    provider: str
    model: str
    task_type: TaskType
    response_time: float
    success: bool
    cost: float
    timestamp: float

class PerformanceMonitor:
    def __init__(self):
        self.metrics: List[RequestMetric] = []
        self.provider_stats = defaultdict(lambda: {
            "total_requests": 0,
            "successful_requests": 0,
            "avg_response_time": 0.0,
            "total_cost": 0.0
        })
    
    def record_request(self, provider: str, model: str, task_type: TaskType, 
                      response_time: float, success: bool, cost: float = 0.0):
        metric = RequestMetric(
            provider=provider,
            model=model,
            task_type=task_type,
            response_time=response_time,
            success=success,
            cost=cost,
            timestamp=time.time()
        )
        
        self.metrics.append(metric)
        self._update_stats(metric)
    
    def get_provider_performance(self, provider: str, hours: int = 24) -> Dict[str, Any]:
        cutoff_time = time.time() - (hours * 3600)
        recent_metrics = [m for m in self.metrics 
                         if m.provider == provider and m.timestamp > cutoff_time]
        
        if not recent_metrics:
            return {}
        
        total_requests = len(recent_metrics)
        successful_requests = sum(1 for m in recent_metrics if m.success)
        avg_response_time = sum(m.response_time for m in recent_metrics) / total_requests
        total_cost = sum(m.cost for m in recent_metrics)
        
        return {
            "provider": provider,
            "total_requests": total_requests,
            "success_rate": successful_requests / total_requests,
            "avg_response_time": avg_response_time,
            "total_cost": total_cost,
            "cost_per_request": total_cost / total_requests if total_requests > 0 else 0
        }
    
    def get_model_recommendations(self) -> Dict[TaskType, str]:
        # Analyze performance data to recommend best models for each task type
        recommendations = {}
        
        for task_type in TaskType:
            task_metrics = [m for m in self.metrics if m.task_type == task_type]
            if task_metrics:
                # Score models based on success rate, response time, and cost
                model_scores = defaultdict(list)
                for metric in task_metrics:
                    score = (
                        (1.0 if metric.success else 0.0) * 0.5 +  # Success weight
                        (1.0 / metric.response_time) * 0.3 +      # Speed weight  
                        (1.0 / (metric.cost + 0.001)) * 0.2       # Cost weight
                    )
                    model_scores[f"{metric.provider}:{metric.model}"].append(score)
                
                # Get best performing model
                best_model = max(model_scores.items(), 
                               key=lambda x: sum(x[1]) / len(x[1]))
                recommendations[task_type] = best_model[0]
        
        return recommendations
```

## 📊 Monitoring & Analytics

### Key Metrics to Track

1. **Performance Metrics**
   - Response times per provider/model
   - Success rates and error frequencies
   - Throughput (requests per minute)
   - Queue depths and wait times

2. **Cost Metrics**
   - Cost per request by provider/model
   - Daily/monthly spend by provider
   - Cost efficiency ratios
   - Budget utilization tracking

3. **Quality Metrics**
   - User satisfaction scores
   - Content quality ratings
   - Task completion rates
   - Fallback frequency

### Dashboard Endpoints

```python
# app/api/v1/endpoints/monitoring.py
@router.get("/ai/performance")
async def get_ai_performance(
    hours: int = 24,
    provider: Optional[str] = None,
    current_user: User = Depends(get_current_active_user)
):
    """Get AI provider performance metrics"""
    monitor = get_performance_monitor()
    
    if provider:
        return monitor.get_provider_performance(provider, hours)
    else:
        return {
            "openai": monitor.get_provider_performance("openai", hours),
            "gemini": monitor.get_provider_performance("gemini", hours),
            "recommendations": monitor.get_model_recommendations()
        }

@router.get("/ai/costs")
async def get_ai_costs(
    days: int = 7,
    current_user: User = Depends(get_current_active_user)
):
    """Get AI usage costs breakdown"""
    cost_tracker = get_cost_tracker()
    return cost_tracker.get_cost_breakdown(days)
```

## 🔧 Environment Configuration

Create a comprehensive `.env` file with all necessary AI provider configurations:

```bash
# AI Providers
OPENAI_API_KEY=your_openai_api_key
OPENAI_ORGANIZATION_ID=your_org_id_optional
GEMINI_API_KEY=your_gemini_api_key
GOOGLE_CLOUD_PROJECT_ID=your_gcp_project

# AI Routing
DEFAULT_AI_PROVIDER=openai
AI_FALLBACK_ENABLED=true
AI_COST_OPTIMIZATION=true
AI_PERFORMANCE_MONITORING=true

# Model Defaults
OPENAI_DEFAULT_MODEL=gpt-4o-mini
GEMINI_DEFAULT_MODEL=gemini-2.5-flash

# Performance Settings
AI_REQUEST_TIMEOUT=30
AI_MAX_RETRIES=3
MAX_CONCURRENT_REQUESTS=10

# Cost Management
DAILY_COST_LIMIT=50.0
COST_ALERT_THRESHOLD=0.8
```

## 🚀 Benefits of This Architecture

### 1. **Reliability**
- Automatic failover between providers
- Graceful degradation during outages
- Multiple model options for each task

### 2. **Cost Optimization**
- Intelligent routing based on cost/performance ratio
- Real-time cost tracking and alerting
- Bulk processing optimizations

### 3. **Performance**
- Task-specific model selection
- Caching for repeated requests
- Load balancing across providers

### 4. **Scalability**
- Easy to add new AI providers
- Horizontal scaling support
- Efficient resource utilization

### 5. **Observability**
- Comprehensive performance monitoring
- Cost tracking and analytics
- Quality metrics and user feedback

This multi-provider AI architecture ensures the AI Language Tutor can leverage the best capabilities of both OpenAI and Google Gemini while maintaining optimal performance, cost efficiency, and reliability.

---

## 🔧 Integration with Simplified Architecture

### PostgreSQL + pgvector Integration

Our AI architecture leverages PostgreSQL's pgvector extension for semantic search capabilities:

```python
# app/services/conversation_embedding_service.py
from pgvector.psycopg2 import register_vector
import psycopg2
from typing import List

class ConversationEmbeddingService:
    def __init__(self, ai_provider_service: AIProviderService):
        self.ai_service = ai_provider_service
        self.db_connection = self._get_db_connection()
        register_vector(self.db_connection)
    
    async def store_conversation_embedding(
        self, 
        session_id: str, 
        content: str,
        embedding_type: str = "session_summary"
    ):
        """Store conversation embeddings in PostgreSQL"""
        
        # Generate embedding using AI provider
        embedding = await self.ai_service.create_embedding(
            text=content,
            task_type=TaskType.CONTENT_EMBEDDING
        )
        
        if embedding_type == "session_summary":
            query = """
            UPDATE conversation_sessions 
            SET session_summary_embedding = %s,
                session_summary = %s,
                updated_at = NOW()
            WHERE id = %s
            """
            await self._execute_query(query, (embedding, content, session_id))
        
        elif embedding_type == "message_content":
            query = """
            UPDATE conversation_messages 
            SET content_embedding = %s,
                updated_at = NOW()
            WHERE session_id = %s AND content = %s
            """
            await self._execute_query(query, (embedding, session_id, content))
    
    async def find_similar_conversations(
        self, 
        query_text: str, 
        user_id: str,
        limit: int = 10
    ) -> List[dict]:
        """Find similar conversations using vector similarity"""
        
        # Generate query embedding
        query_embedding = await self.ai_service.create_embedding(
            text=query_text,
            task_type=TaskType.CONTENT_EMBEDDING
        )
        
        # Search for similar conversations
        search_query = """
        SELECT cs.id, cs.title, cs.session_summary,
               1 - (cs.session_summary_embedding <=> %s) as similarity
        FROM conversation_sessions cs
        WHERE cs.user_id = %s 
          AND cs.session_summary_embedding IS NOT NULL
        ORDER BY cs.session_summary_embedding <=> %s
        LIMIT %s
        """
        
        results = await self._execute_query(
            search_query, 
            (query_embedding, user_id, query_embedding, limit)
        )
        
        return [
            {
                "session_id": row[0],
                "title": row[1],
                "summary": row[2],
                "similarity": float(row[3])
            }
            for row in results
        ]
```

### Neo4j Vector Integration

Neo4j now also handles knowledge graph embeddings using its native vector indexes:

```python
# app/services/knowledge_embedding_service.py
class KnowledgeEmbeddingService:
    def __init__(self, neo4j_service, ai_provider_service: AIProviderService):
        self.neo4j = neo4j_service
        self.ai_service = ai_provider_service
    
    async def create_knowledge_embeddings(self, node_type: str):
        """Create embeddings for knowledge graph nodes"""
        
        if node_type == "GrammarPoint":
            query = """
            MATCH (g:GrammarPoint)
            WHERE g.embedding IS NULL
            RETURN g.id, g.name, g.description
            """
        elif node_type == "Word":
            query = """
            MATCH (w:Word)
            WHERE w.embedding IS NULL
            RETURN w.id, w.lemma, w.meaning
            """
        
        results = await self.neo4j.execute_query(query)
        
        for record in results:
            node_id = record["g.id"] if node_type == "GrammarPoint" else record["w.id"]
            
            # Create content for embedding
            if node_type == "GrammarPoint":
                content = f"{record['g.name']}: {record['g.description']}"
            else:
                content = f"{record['w.lemma']} - {record['w.meaning']}"
            
            # Generate embedding
            embedding = await self.ai_service.create_embedding(
                text=content,
                task_type=TaskType.CONTENT_EMBEDDING
            )
            
            # Store embedding in Neo4j
            update_query = f"""
            MATCH (n:{node_type} {{id: $node_id}})
            SET n.embedding = $embedding
            """
            
            await self.neo4j.execute_query(
                update_query, 
                {"node_id": node_id, "embedding": embedding}
            )
```

## 📊 Updated Architecture Benefits

### Simplified Stack Advantages:
1. **Reduced Complexity**: 2 databases instead of 3
2. **Better Data Locality**: Embeddings stored with source data
3. **Cost Efficiency**: No separate vector database hosting
4. **Easier Maintenance**: Fewer services to monitor and update
5. **Native Integration**: PostgreSQL pgvector is highly optimized

### Updated Model Usage Recommendations:

| Task Type | Primary Model | Use Case | Storage |
|-----------|---------------|----------|---------|
| **Conversation Analysis** | GPT-4o-mini | Real-time chat analysis | PostgreSQL |
| **Knowledge Embeddings** | text-embedding-3-large | Neo4j concept embeddings | Neo4j vector index |
| **Conversation Embeddings** | text-embedding-3-large | PostgreSQL similarity search | PostgreSQL pgvector |
| **Grammar Generation** | GPT-4o | Complex linguistic explanations | Neo4j + PostgreSQL |
| **Quick Responses** | Gemini 2.5 Flash | Fast user interactions | PostgreSQL |
| **Semantic Search** | Combined | Vector similarity queries | PostgreSQL + Neo4j |