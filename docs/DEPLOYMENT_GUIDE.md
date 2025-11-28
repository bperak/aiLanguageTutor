# AI Language Tutor - Deployment Guide

A comprehensive guide for deploying the AI Language Tutor platform to production environments, including cloud infrastructure setup, CI/CD automation, and operational procedures.

## 🎯 Overview

The AI Language Tutor is designed for cloud-native deployment with containerized services, automated CI/CD pipelines, and scalable infrastructure. This guide covers deployment to Google Cloud Platform (recommended) as well as alternative platforms.

### Architecture Summary
- **Frontend**: Next.js application (Google Cloud Run / Vercel)
- **Backend**: FastAPI application (Google Cloud Run)
- **Databases**: PostgreSQL (Cloud SQL) + Neo4j (AuraDB)
- **AI Services**: OpenAI API + Google Gemini API
- **Validation Interface**: Streamlit (Google Cloud Run)

## 🏗️ Infrastructure Requirements

### Minimum Production Requirements
- **CPU**: 2 vCPUs per service
- **Memory**: 4GB RAM per service  
- **Storage**: 20GB SSD per instance
- **Database**: 
  - PostgreSQL: 2 vCPU, 7.5GB RAM, 100GB SSD
  - Neo4j: 4 vCPU, 16GB RAM, 200GB SSD

### Recommended Production Setup
- **CPU**: 4 vCPUs per service (auto-scaling)
- **Memory**: 8GB RAM per service
- **Storage**: 50GB SSD per instance
- **Database**: 
  - PostgreSQL: 4 vCPU, 15GB RAM, 500GB SSD
  - Neo4j: 8 vCPU, 32GB RAM, 1TB SSD

## 🌐 Google Cloud Platform Deployment (Recommended)

### Prerequisites
1. **Google Cloud Account** with billing enabled
2. **Google Cloud CLI** installed locally
3. **Docker** installed for container builds
4. **Domain name** for custom URLs (optional)

### Step 1: Project Setup
```bash
# Create new Google Cloud project
gcloud projects create ai-language-tutor --name="AI Language Tutor"

# Set project as default
gcloud config set project ai-language-tutor

# Enable required APIs
gcloud services enable run.googleapis.com
gcloud services enable sql-component.googleapis.com  
gcloud services enable secretmanager.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable cloudresourcemanager.googleapis.com
```

### Step 2: Database Setup

#### PostgreSQL (Cloud SQL)
```bash
# Create PostgreSQL instance
gcloud sql instances create ai-tutor-postgres \
    --database-version=POSTGRES_15 \
    --tier=db-g1-small \
    --region=us-central1 \
    --storage-type=SSD \
    --storage-size=100GB \
    --backup \
    --maintenance-window-day=SUN \
    --maintenance-window-hour=06

# Create database
gcloud sql databases create ai_language_tutor \
    --instance=ai-tutor-postgres

# Create user
gcloud sql users create app-user \
    --instance=ai-tutor-postgres \
    --password=[SECURE_PASSWORD]
```

#### Neo4j AuraDB
1. Go to [Neo4j Aura Console](https://console.neo4j.io/)
2. Create new AuraDB instance:
   - **Name**: ai-tutor-knowledge-graph
   - **Region**: us-central1 (match GCP region)
   - **Size**: Professional (8GB memory)
3. Save connection credentials securely

### Step 3: Secrets Management
```bash
# Store database credentials
gcloud secrets create postgres-url \
    --data-file=- <<< "postgresql://app-user:[PASSWORD]@/ai_language_tutor?host=/cloudsql/ai-language-tutor:us-central1:ai-tutor-postgres"

gcloud secrets create neo4j-uri \
    --data-file=- <<< "[NEO4J_URI]"

gcloud secrets create neo4j-user \
    --data-file=- <<< "[NEO4J_USERNAME]"

gcloud secrets create neo4j-password \
    --data-file=- <<< "[NEO4J_PASSWORD]"

# Store API keys
gcloud secrets create openai-api-key \
    --data-file=- <<< "[OPENAI_API_KEY]"

gcloud secrets create gemini-api-key \
    --data-file=- <<< "[GEMINI_API_KEY]"

# Store JWT secret
gcloud secrets create jwt-secret-key \
    --data-file=- <<< "[RANDOMLY_GENERATED_SECRET_KEY]"
```

### Step 4: Backend Deployment
```bash
# Navigate to backend directory
cd backend

# Build and deploy to Cloud Run
gcloud run deploy ai-tutor-backend \
    --source . \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated \
    --set-env-vars="ENVIRONMENT=production" \
    --set-secrets="DATABASE_URL=postgres-url:latest,NEO4J_URI=neo4j-uri:latest,NEO4J_USER=neo4j-user:latest,NEO4J_PASSWORD=neo4j-password:latest,OPENAI_API_KEY=openai-api-key:latest,GEMINI_API_KEY=gemini-api-key:latest,SECRET_KEY=jwt-secret-key:latest" \
    --add-cloudsql-instances ai-language-tutor:us-central1:ai-tutor-postgres \
    --memory 2Gi \
    --cpu 2 \
    --max-instances 10
```

### Step 5: Frontend Deployment
```bash
# Navigate to frontend directory
cd ../frontend

# Set up environment variables for build
echo "NEXT_PUBLIC_API_BASE_URL=https://ai-tutor-backend-[HASH]-uc.a.run.app" > .env.local
echo "NEXT_PUBLIC_APP_NAME=AI Language Tutor" >> .env.local

# Build and deploy to Cloud Run
gcloud run deploy ai-tutor-frontend \
    --source . \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated \
    --memory 1Gi \
    --cpu 1 \
    --max-instances 5
```

### Step 6: Validation Interface Deployment
```bash
# Navigate to validation interface
cd ../validation-ui

# Deploy Streamlit interface (admin only)
gcloud run deploy ai-tutor-validation \
    --source . \
    --platform managed \
    --region us-central1 \
    --no-allow-unauthenticated \
    --set-secrets="NEO4J_URI=neo4j-uri:latest,NEO4J_USER=neo4j-user:latest,NEO4J_PASSWORD=neo4j-password:latest" \
    --memory 2Gi \
    --cpu 2 \
    --max-instances 3
```

## 🔄 CI/CD Pipeline (GitHub Actions)

### GitHub Secrets Setup
Add these secrets to your GitHub repository:

```bash
# Google Cloud
GOOGLE_APPLICATION_CREDENTIALS_JSON  # Service account key JSON
GCP_PROJECT_ID                       # ai-language-tutor

# Database & API Keys  
OPENAI_API_KEY                       # OpenAI API key
GEMINI_API_KEY                       # Google Gemini API key
NEO4J_URI                           # Neo4j connection URI
NEO4J_USER                          # Neo4j username
NEO4J_PASSWORD                      # Neo4j password
DATABASE_URL                         # PostgreSQL connection string
SECRET_KEY                           # JWT secret key
```

### CI/CD Workflow
Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Google Cloud Run

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

env:
  PROJECT_ID: ai-language-tutor
  REGION: us-central1

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
          
      - name: Install backend dependencies
        run: |
          cd backend
          pip install poetry
          poetry install
          
      - name: Run backend tests
        run: |
          cd backend
          poetry run pytest tests/ -v
          
      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '18'
          
      - name: Install frontend dependencies
        run: |
          cd frontend
          npm ci
          
      - name: Run frontend tests
        run: |
          cd frontend
          npm run test:ci

  deploy-backend:
    if: github.ref == 'refs/heads/main'
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Google Cloud
        uses: google-github-actions/setup-gcloud@v1
        with:
          service_account_key: ${{ secrets.GOOGLE_APPLICATION_CREDENTIALS_JSON }}
          project_id: ${{ env.PROJECT_ID }}
          
      - name: Deploy Backend
        run: |
          gcloud run deploy ai-tutor-backend \
            --source ./backend \
            --platform managed \
            --region ${{ env.REGION }} \
            --allow-unauthenticated \
            --set-env-vars="ENVIRONMENT=production" \
            --set-secrets="DATABASE_URL=${{ secrets.DATABASE_URL }},NEO4J_URI=${{ secrets.NEO4J_URI }},OPENAI_API_KEY=${{ secrets.OPENAI_API_KEY }}" \
            --memory 2Gi \
            --cpu 2

  deploy-frontend:
    if: github.ref == 'refs/heads/main'  
    needs: [test, deploy-backend]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Google Cloud
        uses: google-github-actions/setup-gcloud@v1
        with:
          service_account_key: ${{ secrets.GOOGLE_APPLICATION_CREDENTIALS_JSON }}
          project_id: ${{ env.PROJECT_ID }}
          
      - name: Deploy Frontend
        run: |
          cd frontend
          echo "NEXT_PUBLIC_API_BASE_URL=https://ai-tutor-backend-[HASH]-uc.a.run.app" > .env.local
          gcloud run deploy ai-tutor-frontend \
            --source . \
            --platform managed \
            --region ${{ env.REGION }} \
            --allow-unauthenticated
```

## 🐳 Docker Configuration

### Backend Dockerfile
```dockerfile
# backend/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pyproject.toml poetry.lock ./
RUN pip install poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-dev

# Copy application
COPY . .

# Create non-root user
RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app /app
USER app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Frontend Dockerfile
```dockerfile
# frontend/Dockerfile
FROM node:18-alpine AS deps
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:18-alpine AS runner
WORKDIR /app
ENV NODE_ENV production
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs
EXPOSE 3000
ENV PORT 3000

CMD ["node", "server.js"]
```

## 🔒 Security Configuration

### Cloud Run Security
```bash
# Configure IAM for services
gcloud run services add-iam-policy-binding ai-tutor-backend \
    --region us-central1 \
    --member="allUsers" \
    --role="roles/run.invoker"

# For validation interface (admin only)
gcloud run services add-iam-policy-binding ai-tutor-validation \
    --region us-central1 \
    --member="user:admin@yourdomain.com" \
    --role="roles/run.invoker"
```

### SSL/TLS Configuration
```bash
# Map custom domain (optional)
gcloud run domain-mappings create \
    --service ai-tutor-frontend \
    --domain app.yourdomain.com \
    --region us-central1
```

## 📊 Monitoring and Logging

### Cloud Monitoring Setup
```bash
# Enable monitoring
gcloud services enable monitoring.googleapis.com
gcloud services enable logging.googleapis.com

# Create alerting policies
gcloud alpha monitoring policies create --policy-from-file=monitoring-policy.yaml
```

### Monitoring Policy Example
```yaml
# monitoring-policy.yaml
displayName: "High Error Rate"
conditions:
  - displayName: "Error rate > 5%"
    conditionThreshold:
      filter: 'resource.type="cloud_run_revision"'
      comparison: COMPARISON_GREATER_THAN
      thresholdValue: 0.05
      duration: "300s"
notificationChannels:
  - "projects/ai-language-tutor/notificationChannels/[CHANNEL_ID]"
```

### Log Analysis Queries
```sql
-- Error rate tracking
SELECT 
  timestamp,
  severity,
  textPayload,
  resource.labels.service_name
FROM `ai-language-tutor.cloud_run_logs` 
WHERE severity >= "ERROR"
  AND timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR)
ORDER BY timestamp DESC

-- Performance monitoring
SELECT 
  AVG(CAST(JSON_EXTRACT_SCALAR(httpRequest, '$.latency') AS FLOAT64)) as avg_latency,
  COUNT(*) as request_count
FROM `ai-language-tutor.cloud_run_logs`
WHERE httpRequest IS NOT NULL
  AND timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR)
GROUP BY TIMESTAMP_TRUNC(timestamp, MINUTE)
ORDER BY timestamp DESC
```

## 🔄 Alternative Deployment Options

### Vercel (Frontend Only)
```bash
# Install Vercel CLI
npm i -g vercel

# Deploy from frontend directory
cd frontend
vercel --prod

# Set environment variables
vercel env add NEXT_PUBLIC_API_BASE_URL production
```

### AWS Deployment
```bash
# Using AWS App Runner for backend
aws apprunner create-service \
    --service-name ai-tutor-backend \
    --source-configuration file://apprunner-source.json
```

### Docker Compose (Development/Small Production)
```yaml
# docker-compose.prod.yml
version: '3.8'
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=production
    env_file:
      - .env.prod
    depends_on:
      - postgres
      
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_BASE_URL=http://backend:8000
      
  postgres:
    image: postgres:15
    environment:
      - POSTGRES_DB=ai_language_tutor
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

## 🔧 Maintenance and Operations

### Database Migrations
```bash
# Run migrations in production
gcloud run jobs execute migration-job \
    --region us-central1 \
    --task-timeout 3600

# Manual migration via Cloud Run
gcloud run services update ai-tutor-backend \
    --region us-central1 \
    --set-env-vars "RUN_MIGRATIONS=true"
```

### Backup Procedures
```bash
# PostgreSQL backup (automated)
gcloud sql backups create \
    --instance=ai-tutor-postgres \
    --description="Manual backup before deployment"

# Neo4j backup (via Neo4j Ops Manager)
# Access Neo4j console for automated backup configuration
```

### Health Checks
```bash
# Backend health
curl https://ai-tutor-backend-[HASH]-uc.a.run.app/health

# Frontend health  
curl https://ai-tutor-frontend-[HASH]-uc.a.run.app/api/health

# Database connectivity
curl https://ai-tutor-backend-[HASH]-uc.a.run.app/api/v1/health/db
```

### Scaling Configuration
```bash
# Auto-scaling settings
gcloud run services update ai-tutor-backend \
    --region us-central1 \
    --min-instances 1 \
    --max-instances 20 \
    --cpu-throttling \
    --concurrency 80
```

## 📋 Pre-Deployment Checklist

### Environment Setup
- [ ] Google Cloud project created and configured
- [ ] All required APIs enabled  
- [ ] Service account created with proper permissions
- [ ] Secrets stored in Secret Manager
- [ ] Domain name configured (optional)

### Database Setup
- [ ] PostgreSQL instance created and accessible
- [ ] Neo4j AuraDB instance created and connected
- [ ] Database migrations tested
- [ ] Backup procedures configured

### Application Deployment
- [ ] Backend deployed and responding to health checks
- [ ] Frontend deployed and accessible
- [ ] Validation interface deployed (admin access)
- [ ] All services communicating properly

### Security and Monitoring
- [ ] HTTPS/SSL configured
- [ ] IAM permissions properly configured  
- [ ] Monitoring and alerting set up
- [ ] Log aggregation working
- [ ] Security scanning completed

### Performance and Reliability
- [ ] Load testing completed
- [ ] Auto-scaling configured
- [ ] Error rates within acceptable limits
- [ ] Response times meeting SLA requirements

## 🚀 Post-Deployment Verification

### Functional Testing
```bash
# Test user registration
curl -X POST https://your-domain.com/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"test","email":"test@example.com","password":"testpass123"}'

# Test conversation creation
curl -X POST https://your-domain.com/api/v1/conversations/sessions \
  -H "Authorization: Bearer [JWT_TOKEN]" \
  -H "Content-Type: application/json" \
  -d '{"title":"Test Conversation","language_code":"ja"}'
```

### Performance Verification
- [ ] Page load times < 3 seconds
- [ ] API response times < 500ms  
- [ ] Database query performance acceptable
- [ ] Memory usage within limits
- [ ] CPU utilization normal

---

*This deployment guide provides comprehensive instructions for production deployment of the AI Language Tutor platform. For development setup, see the main README.md file.*
