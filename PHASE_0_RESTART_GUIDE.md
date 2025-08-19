# 🚀 Phase 0 Restart Guide - Simplified Architecture

## 🎯 Overview
This guide will help you restart Phase 0 with the simplified architecture (PostgreSQL + Neo4j).

**Good News: You don't need to delete Docker!** We just need to clean up the configuration.

## 📋 Pre-Flight Checklist

### ✅ What's Already Done:
- [x] Updated PLANNING.md with new architecture
- [x] Updated docker-compose.yml (removed Weaviate)
- [x] Created PostgreSQL schema with pgvector
- [x] Updated TASK.md with new dependencies
- [x] Updated README.md

### 🧹 What Needs Cleanup:
- [ ] Create .env.template file
- [ ] Test Docker setup
- [ ] Verify database connections
- [ ] Clean up any remaining containers

## 🔧 Step-by-Step Restart

### Step 1: Clean Up Existing Docker (Optional)
If you want a completely fresh start:

```powershell
# Stop all containers
docker-compose down

# Remove volumes (optional - will delete data)
docker-compose down -v

# Remove unused containers and images (optional)
docker system prune -f
```

### Step 2: Create Environment Configuration

Create a `.env.template` file in the root directory:

```bash
# AI Language Tutor - Environment Configuration Template

# =============================================================================
# DATABASE CONFIGURATION
# =============================================================================

# PostgreSQL Database (User data, conversations, embeddings)
DATABASE_URL=postgresql://postgres:testpassword123@localhost:5432/ai_language_tutor
POSTGRES_USER=postgres
POSTGRES_PASSWORD=testpassword123
POSTGRES_DB=ai_language_tutor

# Neo4j Knowledge Graph Database
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=testpassword123

# =============================================================================
# AI SERVICES CONFIGURATION
# =============================================================================

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Google Gemini Configuration
GEMINI_API_KEY=your_gemini_api_key_here

# =============================================================================
# APPLICATION SECURITY
# =============================================================================

# JWT Configuration (generate with: openssl rand -hex 32)
JWT_SECRET_KEY=your_jwt_secret_key_here
JWT_ALGORITHM=HS256

# =============================================================================
# DEVELOPMENT CONFIGURATION
# =============================================================================
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO
```

### Step 3: Copy and Configure Environment

```powershell
# Copy template to actual env file
Copy-Item .env.template .env

# Generate JWT secret key
$jwtSecret = -join ((1..64) | ForEach {'{0:X}' -f (Get-Random -Max 16)})
Write-Host "Generated JWT Secret: $jwtSecret"

# Edit .env file with your actual API keys
```

### Step 4: Test Docker Setup

```powershell
# Build and start services
docker-compose up --build -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f
```

### Step 5: Verify Database Connections

```powershell
# Test PostgreSQL connection
docker-compose exec postgres psql -U postgres -d ai_language_tutor -c "SELECT version();"

# Test Neo4j connection (should show Neo4j browser at http://localhost:7474)
# Username: neo4j, Password: testpassword123
```

### Step 6: Verify pgvector Extension

```powershell
# Check if pgvector extension is installed
docker-compose exec postgres psql -U postgres -d ai_language_tutor -c "SELECT * FROM pg_extension WHERE extname = 'vector';"
```

## 🐛 Common Issues & Solutions

### Issue 1: PostgreSQL Connection Refused
```powershell
# Check if PostgreSQL is running
docker-compose ps postgres

# Restart PostgreSQL
docker-compose restart postgres

# Check logs
docker-compose logs postgres
```

### Issue 2: Neo4j Authentication Error
```powershell
# Reset Neo4j password
docker-compose exec neo4j cypher-shell -u neo4j -p neo4j "CALL dbms.security.changePassword('testpassword123')"
```

### Issue 3: pgvector Extension Not Found
```powershell
# Rebuild PostgreSQL container
docker-compose down
docker-compose up --build postgres
```

### Issue 4: Port Conflicts
```powershell
# Check what's using the ports
netstat -an | findstr ":5432"
netstat -an | findstr ":7474"

# Kill processes if needed or change ports in docker-compose.yml
```

## ✅ Verification Steps

### 1. Database Connectivity Test
```powershell
# PostgreSQL
docker-compose exec postgres psql -U postgres -d ai_language_tutor -c "SELECT COUNT(*) FROM users;"

# Neo4j (visit http://localhost:7474)
# Login with neo4j/testpassword123
```

### 2. pgvector Test
```powershell
docker-compose exec postgres psql -U postgres -d ai_language_tutor -c "
SELECT session_summary_embedding <-> '[0.1,0.2,0.3]'::vector as distance 
FROM conversation_sessions 
WHERE session_summary_embedding IS NOT NULL 
LIMIT 1;
"
```

### 3. Service Health Check
```powershell
# All services should be healthy
docker-compose ps

# Expected services:
# - ai-tutor-postgres (healthy)
# - ai-tutor-neo4j (up)
```

## 🎯 Next Steps After Restart

1. **Phase 0 Completion**: Continue with backend and frontend setup
2. **API Development**: Start building FastAPI application
3. **Database Migrations**: Run Alembic migrations
4. **Testing**: Set up pytest and test database connections

## 📚 Key Changes Summary

### Removed:
- ❌ Weaviate service and configuration
- ❌ Weaviate-related environment variables
- ❌ weaviate-client Python dependency

### Added:
- ✅ PostgreSQL with pgvector extension
- ✅ Vector similarity indexes
- ✅ Conversation embedding columns
- ✅ Simplified 2-database architecture

### Updated:
- ✅ Docker service dependencies
- ✅ Environment variable configuration
- ✅ Database schema with vector support
- ✅ Task list and documentation

## 🆘 Getting Help

If you encounter issues:

1. **Check Docker logs**: `docker-compose logs [service-name]`
2. **Verify configuration**: Ensure .env file has correct values
3. **Database connection**: Test connections manually
4. **Port conflicts**: Check if ports 5432, 7474, 7687 are available
5. **Restart services**: `docker-compose restart [service-name]`

The simplified architecture should be much more reliable and easier to manage! 🎉
