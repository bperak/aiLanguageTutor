# AI Language Tutor - Testing Strategies

Comprehensive testing documentation covering unit tests, integration tests, end-to-end testing, and quality assurance strategies for the AI Language Tutor platform.

## 🎯 Testing Philosophy

Our testing strategy follows the **Testing Pyramid** approach with emphasis on:
- **Fast Feedback**: Quick unit tests for immediate developer feedback
- **Comprehensive Coverage**: Testing all critical paths and edge cases
- **Realistic Scenarios**: Integration tests that mirror real user workflows
- **Automated Quality Gates**: Preventing regressions through CI/CD integration
- **User-Centric E2E**: End-to-end tests focused on user journeys

### Testing Principles
1. **Test-Driven Development (TDD)**: Write tests before implementation
2. **Behavior-Driven Development (BDD)**: Tests describe expected behavior
3. **Fail Fast**: Tests should fail quickly and provide clear error messages
4. **Isolation**: Tests should not depend on external systems unless necessary
5. **Maintainability**: Tests should be easy to read, write, and maintain

## 📊 Testing Pyramid

```
    /\
   /  \     E2E Tests (10%)
  /____\    - User workflows
 /      \   - Cross-service integration
/__________\ Integration Tests (30%)
            - API endpoints
            - Database operations
            - External service mocks

Unit Tests (60%)
- Business logic
- Components
- Utilities
- Services
```

## 🧪 Backend Testing (Python/FastAPI)

### Test Structure
```
backend/tests/
├── __init__.py
├── conftest.py              # Pytest configuration and fixtures
├── unit/                    # Unit tests (60% of total)
│   ├── test_auth_service.py
│   ├── test_conversation_service.py
│   ├── test_grammar_service.py
│   └── test_srs_algorithms.py
├── integration/             # Integration tests (30% of total)
│   ├── test_auth_endpoints.py
│   ├── test_conversation_flow.py
│   ├── test_database_operations.py
│   └── test_ai_provider_integration.py
└── e2e/                     # End-to-end tests (10% of total)
    ├── test_user_registration_flow.py
    ├── test_conversation_complete_flow.py
    └── test_learning_progress_flow.py
```

### Test Configuration (conftest.py)
```python
import pytest
import asyncio
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db import get_db, Base
from app.core.config import settings

# Test database URL (in-memory SQLite)
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def db():
    """Create test database."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client(db):
    """Create test client with database dependency override."""
    def override_get_db():
        try:
            yield db
        finally:
            db.close()
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture
def auth_headers(client):
    """Create authenticated user and return auth headers."""
    # Create test user
    user_data = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpassword123"
    }
    
    # Register user
    client.post("/api/v1/auth/register", json=user_data)
    
    # Login and get token
    response = client.post("/api/v1/auth/login", data={
        "username": user_data["username"],
        "password": user_data["password"]
    })
    
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
```

### Unit Testing Examples

#### Service Layer Testing
```python
# tests/unit/test_conversation_service.py
import pytest
from unittest.mock import Mock, AsyncMock
from uuid import uuid4

from app.services.conversation_service import ConversationService
from app.schemas.conversation import ConversationCreate, MessageCreate

class TestConversationService:
    
    @pytest.fixture
    def mock_db(self):
        return Mock()
    
    @pytest.fixture
    def mock_ai_service(self):
        ai_service = Mock()
        ai_service.generate_response = AsyncMock(return_value="Mock AI response")
        return ai_service
    
    @pytest.fixture
    def conversation_service(self, mock_db, mock_ai_service):
        return ConversationService(mock_db, mock_ai_service)
    
    @pytest.mark.asyncio
    async def test_create_conversation_session(self, conversation_service, mock_db):
        # Arrange
        user_id = uuid4()
        session_data = ConversationCreate(
            title="Test Conversation",
            language_code="ja",
            session_type="chat"
        )
        
        mock_db.add = Mock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        # Act
        result = await conversation_service.create_session(user_id, session_data)
        
        # Assert
        assert result.title == "Test Conversation"
        assert result.language_code == "ja"
        assert result.user_id == user_id
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_add_message_with_ai_response(self, conversation_service):
        # Arrange
        session_id = uuid4()
        message_data = MessageCreate(
            role="user",
            content="Hello, how are you?"
        )
        
        # Act
        result = await conversation_service.add_message_with_ai_response(
            session_id, message_data
        )
        
        # Assert
        assert len(result) == 2  # User message + AI response
        assert result[0].role == "user"
        assert result[1].role == "assistant"
        assert result[1].content == "Mock AI response"
```

#### Algorithm Testing
```python
# tests/unit/test_srs_algorithms.py
import pytest
from datetime import datetime, timedelta

from app.services.srs_service import SRSService, calculate_next_review

class TestSRSAlgorithms:
    
    def test_calculate_next_review_correct_answer(self):
        """Test SRS algorithm for correct answers."""
        # Arrange
        current_interval = 1
        current_ease = 2.5
        quality = 4  # Good answer
        
        # Act
        next_interval, next_ease = calculate_next_review(
            current_interval, current_ease, quality
        )
        
        # Assert
        assert next_interval > current_interval
        assert next_ease >= current_ease
    
    def test_calculate_next_review_incorrect_answer(self):
        """Test SRS algorithm for incorrect answers."""
        # Arrange
        current_interval = 7
        current_ease = 2.5
        quality = 1  # Incorrect answer
        
        # Act
        next_interval, next_ease = calculate_next_review(
            current_interval, current_ease, quality
        )
        
        # Assert
        assert next_interval == 1  # Reset to beginning
        assert next_ease < 2.5  # Decrease ease factor
    
    @pytest.mark.parametrize("quality,expected_min_interval", [
        (1, 1),    # Incorrect -> Reset to 1
        (2, 1),    # Hard -> Reset to 1  
        (3, 3),    # Good -> Increase
        (4, 4),    # Easy -> Larger increase
    ])
    def test_srs_quality_responses(self, quality, expected_min_interval):
        """Test different quality responses."""
        interval, ease = calculate_next_review(1, 2.5, quality)
        assert interval >= expected_min_interval
```

### Integration Testing Examples

#### API Endpoint Testing
```python
# tests/integration/test_auth_endpoints.py
import pytest

class TestAuthEndpoints:
    
    def test_user_registration_success(self, client):
        """Test successful user registration."""
        # Arrange
        user_data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "securepassword123"
        }
        
        # Act
        response = client.post("/api/v1/auth/register", json=user_data)
        
        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == user_data["username"]
        assert data["email"] == user_data["email"]
        assert "id" in data
        assert "password" not in data  # Ensure password not returned
    
    def test_user_registration_duplicate_username(self, client):
        """Test registration with duplicate username."""
        # Arrange
        user_data = {
            "username": "testuser",
            "email": "different@example.com",
            "password": "password123"
        }
        
        # Create first user
        client.post("/api/v1/auth/register", json=user_data)
        
        # Act - Try to create duplicate
        response = client.post("/api/v1/auth/register", json={
            **user_data,
            "email": "another@example.com"
        })
        
        # Assert
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"].lower()
    
    def test_login_success(self, client):
        """Test successful login."""
        # Arrange
        user_data = {
            "username": "loginuser",
            "email": "login@example.com", 
            "password": "loginpassword123"
        }
        client.post("/api/v1/auth/register", json=user_data)
        
        # Act
        response = client.post("/api/v1/auth/login", data={
            "username": user_data["username"],
            "password": user_data["password"]
        })
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
```

#### Database Operations Testing
```python
# tests/integration/test_database_operations.py
import pytest
from app.models.user import User
from app.models.conversation import ConversationSession

class TestDatabaseOperations:
    
    def test_user_creation_and_retrieval(self, db):
        """Test creating and retrieving users from database."""
        # Arrange
        user = User(
            username="dbtest",
            email="db@example.com",
            hashed_password="hashed_password"
        )
        
        # Act
        db.add(user)
        db.commit()
        db.refresh(user)
        
        retrieved_user = db.query(User).filter(User.username == "dbtest").first()
        
        # Assert
        assert retrieved_user is not None
        assert retrieved_user.username == "dbtest"
        assert retrieved_user.email == "db@example.com"
        assert retrieved_user.id == user.id
    
    def test_conversation_cascade_delete(self, db):
        """Test cascade deletion of conversations when user deleted."""
        # Arrange
        user = User(
            username="cascadetest",
            email="cascade@example.com",
            hashed_password="hashed"
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
        conversation = ConversationSession(
            user_id=user.id,
            title="Test Conversation",
            language_code="ja"
        )
        db.add(conversation)
        db.commit()
        
        # Act
        db.delete(user)
        db.commit()
        
        # Assert
        remaining_conversations = db.query(ConversationSession).filter(
            ConversationSession.user_id == user.id
        ).all()
        assert len(remaining_conversations) == 0
```

### End-to-End Testing

#### Complete User Workflows
```python
# tests/e2e/test_user_registration_flow.py
import pytest

class TestUserRegistrationFlow:
    
    def test_complete_registration_to_conversation(self, client):
        """Test complete user journey from registration to first conversation."""
        
        # Step 1: Register user
        user_data = {
            "username": "e2euser",
            "email": "e2e@example.com",
            "password": "e2epassword123"
        }
        
        register_response = client.post("/api/v1/auth/register", json=user_data)
        assert register_response.status_code == 201
        
        # Step 2: Login
        login_response = client.post("/api/v1/auth/login", data={
            "username": user_data["username"],
            "password": user_data["password"]
        })
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Step 3: Get user profile
        profile_response = client.get("/api/v1/auth/me", headers=headers)
        assert profile_response.status_code == 200
        
        # Step 4: Create conversation session
        conversation_data = {
            "title": "My First Conversation",
            "language_code": "ja",
            "session_type": "chat"
        }
        
        session_response = client.post(
            "/api/v1/conversations/sessions",
            json=conversation_data,
            headers=headers
        )
        assert session_response.status_code == 201
        session_id = session_response.json()["id"]
        
        # Step 5: Add message to conversation
        message_data = {
            "role": "user",
            "content": "こんにちは、元気ですか？"
        }
        
        message_response = client.post(
            f"/api/v1/conversations/sessions/{session_id}/messages",
            json=message_data,
            headers=headers
        )
        assert message_response.status_code == 201
        
        # Step 6: Verify conversation history
        history_response = client.get(
            f"/api/v1/conversations/sessions/{session_id}/messages",
            headers=headers
        )
        assert history_response.status_code == 200
        messages = history_response.json()
        assert len(messages) >= 1
        assert messages[0]["content"] == message_data["content"]
```

## 🌐 Frontend Testing (React/Next.js)

### Test Structure
```
frontend/
├── __tests__/              # Test files
│   ├── components/
│   ├── pages/
│   └── utils/
├── jest.config.js          # Jest configuration
├── jest.setup.js           # Test setup
└── package.json           # Test scripts
```

### Test Configuration

#### jest.config.js
```javascript
const nextJest = require('next/jest')

const createJestConfig = nextJest({
  dir: './',
})

const customJestConfig = {
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
  moduleNameMapping: {
    '^@/components/(.*)$': '<rootDir>/src/components/$1',
    '^@/pages/(.*)$': '<rootDir>/src/pages/$1',
    '^@/lib/(.*)$': '<rootDir>/src/lib/$1',
  },
  testEnvironment: 'jest-environment-jsdom',
  collectCoverageFrom: [
    'src/**/*.{js,jsx,ts,tsx}',
    '!src/**/*.d.ts',
    '!src/app/**/layout.tsx',
    '!src/app/**/page.tsx',
  ],
  coverageReporters: ['text', 'lcov', 'html'],
  coverageThreshold: {
    global: {
      branches: 80,
      functions: 80,
      lines: 80,
      statements: 80,
    },
  },
}

module.exports = createJestConfig(customJestConfig)
```

#### jest.setup.js
```javascript
import '@testing-library/jest-dom'

// Mock Next.js router
jest.mock('next/router', () => ({
  useRouter() {
    return {
      route: '/',
      pathname: '/',
      query: {},
      asPath: '/',
      push: jest.fn(),
      pop: jest.fn(),
      reload: jest.fn(),
      back: jest.fn(),
      prefetch: jest.fn(),
      beforePopState: jest.fn(),
      events: {
        on: jest.fn(),
        off: jest.fn(),
        emit: jest.fn(),
      },
    }
  },
}))

// Mock API calls
global.fetch = jest.fn()

// Setup API mocks
beforeEach(() => {
  fetch.mockClear()
})
```

### Component Testing Examples

#### UI Component Testing
```typescript
// __tests__/components/ui/Button.test.tsx
import { render, screen, fireEvent } from '@testing-library/react'
import { Button } from '@/components/ui/button'

describe('Button Component', () => {
  it('renders with correct text', () => {
    render(<Button>Click me</Button>)
    
    expect(screen.getByRole('button', { name: /click me/i })).toBeInTheDocument()
  })
  
  it('handles click events', () => {
    const handleClick = jest.fn()
    render(<Button onClick={handleClick}>Click me</Button>)
    
    fireEvent.click(screen.getByRole('button'))
    expect(handleClick).toHaveBeenCalledTimes(1)
  })
  
  it('shows disabled state', () => {
    render(<Button disabled>Disabled</Button>)
    
    const button = screen.getByRole('button')
    expect(button).toBeDisabled()
    expect(button).toHaveClass('disabled:opacity-50')
  })
  
  it('renders different variants', () => {
    const { rerender } = render(<Button variant="default">Default</Button>)
    expect(screen.getByRole('button')).toHaveClass('bg-primary')
    
    rerender(<Button variant="destructive">Delete</Button>)
    expect(screen.getByRole('button')).toHaveClass('bg-destructive')
    
    rerender(<Button variant="outline">Outline</Button>)
    expect(screen.getByRole('button')).toHaveClass('border-input')
  })
})
```

#### Page Component Testing
```typescript
// __tests__/pages/login.test.tsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import LoginPage from '@/app/(auth)/login/page'

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })

const renderWithClient = (component: React.ReactElement) => {
  const testQueryClient = createTestQueryClient()
  return render(
    <QueryClientProvider client={testQueryClient}>
      {component}
    </QueryClientProvider>
  )
}

describe('Login Page', () => {
  beforeEach(() => {
    fetch.mockResolvedValue({
      ok: true,
      json: async () => ({
        access_token: 'mock-token',
        token_type: 'bearer',
      }),
    })
  })
  
  it('renders login form', () => {
    renderWithClient(<LoginPage />)
    
    expect(screen.getByLabelText(/username/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument()
  })
  
  it('submits form with valid data', async () => {
    renderWithClient(<LoginPage />)
    
    fireEvent.change(screen.getByLabelText(/username/i), {
      target: { value: 'testuser' },
    })
    fireEvent.change(screen.getByLabelText(/password/i), {
      target: { value: 'password123' },
    })
    
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }))
    
    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith('/api/v1/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: 'username=testuser&password=password123',
      })
    })
  })
  
  it('displays error for invalid credentials', async () => {
    fetch.mockResolvedValueOnce({
      ok: false,
      json: async () => ({ detail: 'Invalid credentials' }),
    })
    
    renderWithClient(<LoginPage />)
    
    fireEvent.change(screen.getByLabelText(/username/i), {
      target: { value: 'wronguser' },
    })
    fireEvent.change(screen.getByLabelText(/password/i), {
      target: { value: 'wrongpass' },
    })
    
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }))
    
    await waitFor(() => {
      expect(screen.getByText(/invalid credentials/i)).toBeInTheDocument()
    })
  })
})
```

### Custom Hook Testing
```typescript
// __tests__/hooks/useAuth.test.tsx
import { renderHook, act } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useAuth } from '@/hooks/useAuth'

const wrapper = ({ children }: { children: React.ReactNode }) => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  )
}

describe('useAuth Hook', () => {
  beforeEach(() => {
    localStorage.clear()
    fetch.mockClear()
  })
  
  it('starts with no authenticated user', () => {
    const { result } = renderHook(() => useAuth(), { wrapper })
    
    expect(result.current.user).toBeNull()
    expect(result.current.isAuthenticated).toBe(false)
  })
  
  it('logs in user successfully', async () => {
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        access_token: 'mock-token',
        token_type: 'bearer',
      }),
    })
    
    const { result } = renderHook(() => useAuth(), { wrapper })
    
    await act(async () => {
      await result.current.login('testuser', 'password123')
    })
    
    expect(localStorage.getItem('auth_token')).toBe('mock-token')
    expect(result.current.isAuthenticated).toBe(true)
  })
})
```

## 🔧 Test Automation & CI/CD

### GitHub Actions Workflow
```yaml
# .github/workflows/test.yml
name: Test Suite

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  backend-tests:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: test_db
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
          
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
          
      - name: Install Poetry
        uses: snok/install-poetry@v1
        
      - name: Install dependencies
        run: |
          cd backend
          poetry install
          
      - name: Run unit tests
        run: |
          cd backend
          poetry run pytest tests/unit/ -v --cov=app --cov-report=xml
          
      - name: Run integration tests
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost/test_db
        run: |
          cd backend
          poetry run pytest tests/integration/ -v
          
      - name: Upload coverage reports
        uses: codecov/codecov-action@v3
        with:
          file: backend/coverage.xml
          flags: backend

  frontend-tests:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '18'
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json
          
      - name: Install dependencies
        run: |
          cd frontend
          npm ci
          
      - name: Run unit tests
        run: |
          cd frontend
          npm run test:coverage
          
      - name: Upload coverage reports
        uses: codecov/codecov-action@v3
        with:
          directory: frontend/coverage
          flags: frontend

  e2e-tests:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
          
      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '18'
          
      - name: Start backend
        run: |
          cd backend
          poetry install
          poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 &
          
      - name: Start frontend
        run: |
          cd frontend
          npm ci
          npm run build
          npm run start &
          
      - name: Wait for services
        run: |
          npx wait-on http://localhost:8000/health
          npx wait-on http://localhost:3000
          
      - name: Run E2E tests
        run: |
          cd backend
          poetry run pytest tests/e2e/ -v
```

### Test Scripts (package.json)
```json
{
  "scripts": {
    "test": "jest",
    "test:watch": "jest --watch",
    "test:coverage": "jest --coverage",
    "test:ci": "jest --ci --coverage --watchAll=false",
    "test:e2e": "playwright test"
  }
}
```

## 🎯 Test Coverage & Quality Gates

### Coverage Requirements
- **Overall Coverage**: Minimum 80%
- **Unit Tests**: Minimum 85%
- **Integration Tests**: Minimum 75%
- **Critical Paths**: 100% coverage required
- **New Code**: Must maintain or improve coverage

### Quality Gates
```python
# pytest.ini
[tool:pytest]
minversion = 7.0
addopts = 
    --strict-markers
    --strict-config
    --verbose
    --cov=app
    --cov-report=term-missing
    --cov-report=html
    --cov-report=xml
    --cov-fail-under=80
testpaths = tests
markers =
    unit: Unit tests
    integration: Integration tests  
    e2e: End-to-end tests
    slow: Slow running tests
```

### Code Quality Checks
```yaml
# Pre-commit hooks
repos:
  - repo: local
    hooks:
      - id: pytest-unit
        name: pytest-unit
        entry: poetry run pytest tests/unit/
        language: system
        pass_filenames: false
        
      - id: coverage-check
        name: coverage-check
        entry: poetry run pytest --cov=app --cov-fail-under=80
        language: system
        pass_filenames: false
```

## 🔍 Test Categories & Strategies

### Performance Testing
```python
# tests/performance/test_api_performance.py
import pytest
import time
from concurrent.futures import ThreadPoolExecutor
import statistics

class TestAPIPerformance:
    
    @pytest.mark.slow
    def test_conversation_endpoint_response_time(self, client, auth_headers):
        """Test conversation endpoint response time under load."""
        
        def make_request():
            start_time = time.time()
            response = client.post(
                "/api/v1/conversations/sessions",
                json={"title": "Performance Test", "language_code": "ja"},
                headers=auth_headers
            )
            end_time = time.time()
            return end_time - start_time, response.status_code
        
        # Run concurrent requests
        with ThreadPoolExecutor(max_workers=10) as executor:
            results = list(executor.map(lambda _: make_request(), range(50)))
        
        response_times = [result[0] for result in results]
        status_codes = [result[1] for result in results]
        
        # Assert performance requirements
        assert all(code == 201 for code in status_codes)
        assert statistics.mean(response_times) < 0.5  # 500ms average
        assert max(response_times) < 2.0  # 2s maximum
```

### Security Testing
```python
# tests/security/test_auth_security.py
import pytest

class TestAuthSecurity:
    
    def test_sql_injection_prevention(self, client):
        """Test SQL injection attempts are prevented."""
        malicious_input = "'; DROP TABLE users; --"
        
        response = client.post("/api/v1/auth/login", data={
            "username": malicious_input,
            "password": "password"
        })
        
        # Should not cause server error, should return 401
        assert response.status_code == 401
        assert "Invalid credentials" in response.json()["detail"]
    
    def test_password_requirements_enforced(self, client):
        """Test password strength requirements."""
        weak_passwords = ["123", "password", "qwerty", "abc123"]
        
        for weak_password in weak_passwords:
            response = client.post("/api/v1/auth/register", json={
                "username": f"user_{weak_password}",
                "email": f"{weak_password}@example.com",
                "password": weak_password
            })
            
            assert response.status_code == 400
            assert "password" in response.json()["detail"].lower()
    
    def test_rate_limiting_auth_endpoints(self, client):
        """Test rate limiting on authentication endpoints."""
        # Attempt multiple rapid login attempts
        for i in range(6):  # Assuming 5 attempt limit
            response = client.post("/api/v1/auth/login", data={
                "username": "nonexistent",
                "password": "wrongpassword"
            })
            
            if i < 5:
                assert response.status_code == 401
            else:
                assert response.status_code == 429  # Too Many Requests
```

### Accessibility Testing
```javascript
// __tests__/accessibility/a11y.test.tsx
import { render } from '@testing-library/react'
import { axe, toHaveNoViolations } from 'jest-axe'
import LoginPage from '@/app/(auth)/login/page'

expect.extend(toHaveNoViolations)

describe('Accessibility Tests', () => {
  it('login page should not have accessibility violations', async () => {
    const { container } = render(<LoginPage />)
    const results = await axe(container)
    expect(results).toHaveNoViolations()
  })
  
  it('navigation should be keyboard accessible', async () => {
    const { container } = render(<NavBar />)
    
    // Test keyboard navigation
    const navLinks = container.querySelectorAll('a')
    navLinks.forEach(link => {
      expect(link).toHaveAttribute('tabIndex')
    })
    
    const results = await axe(container)
    expect(results).toHaveNoViolations()
  })
})
```

## 📊 Test Reporting & Analytics

### Coverage Reporting
```bash
# Generate comprehensive coverage report
poetry run pytest --cov=app --cov-report=html --cov-report=xml --cov-report=term

# View coverage in browser
open htmlcov/index.html
```

### Test Result Analysis
```python
# Custom pytest plugin for analytics
# conftest.py
import json
from datetime import datetime

def pytest_sessionfinish(session, exitstatus):
    """Generate test analytics after session."""
    stats = {
        "timestamp": datetime.now().isoformat(),
        "total_tests": session.testscollected,
        "passed": len([r for r in session.testresults if r.passed]),
        "failed": len([r for r in session.testresults if r.failed]),
        "skipped": len([r for r in session.testresults if r.skipped]),
        "duration": session.duration,
        "coverage_percentage": session.coverage_percentage
    }
    
    with open("test_analytics.json", "w") as f:
        json.dump(stats, f, indent=2)
```

## 🚀 Best Practices & Guidelines

### Test Writing Guidelines
1. **AAA Pattern**: Arrange, Act, Assert
2. **Descriptive Names**: Test names should describe expected behavior
3. **Single Responsibility**: One test should verify one behavior
4. **Independent Tests**: Tests should not depend on each other
5. **Data Cleanup**: Clean up test data after each test

### Mock Strategy
```python
# Good: Mock external dependencies
@pytest.fixture
def mock_openai_client():
    with patch('app.services.ai_service.openai') as mock:
        mock.chat.completions.create.return_value = Mock(
            choices=[Mock(message=Mock(content="Mock response"))]
        )
        yield mock

# Avoid: Mocking internal business logic
# Don't mock the code you're testing
```

### Test Data Management
```python
# factories.py - Use factories for test data
import factory
from app.models.user import User

class UserFactory(factory.Factory):
    class Meta:
        model = User
    
    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@example.com")
    hashed_password = "hashed_password_value"

# Usage in tests
def test_user_creation():
    user = UserFactory()
    assert user.username.startswith("user")
```

## 📈 Continuous Improvement

### Test Metrics Tracking
- **Test Execution Time**: Monitor for performance regression
- **Flaky Test Rate**: Identify and fix unstable tests
- **Coverage Trends**: Ensure coverage doesn't decrease
- **Bug Escape Rate**: Tests should catch bugs before production

### Regular Test Maintenance
- **Quarterly Review**: Remove obsolete tests
- **Performance Optimization**: Optimize slow test suites
- **Test Documentation**: Keep test purposes clear
- **Tool Updates**: Keep testing frameworks current

---

*This testing strategy ensures comprehensive quality assurance for the AI Language Tutor platform. Follow these guidelines to maintain high code quality and reliable user experiences.*
