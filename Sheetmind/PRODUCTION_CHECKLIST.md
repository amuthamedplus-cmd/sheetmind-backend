# SheetMind Production Launch Checklist

## Test Results Summary

| Component | Status | Notes |
|-----------|--------|-------|
| Backend Imports | PASS | All modules load correctly |
| Frontend Build | PASS | Builds to 360KB (118KB gzipped) |
| Sheet Analyzer | PASS | Correctly detects column types |
| SmartExecutor | PASS | Generates 7 actions for chart template |
| Intent Detection | PASS | Agent/chart intents detected correctly |
| Server Health | PASS | Returns healthy status |

---

## CRITICAL (Must Fix Before Launch)

### 1. Security - Credentials Exposure

- [ ] **Remove `.env` from version control**
  ```bash
  # Add to .gitignore
  echo "backend/.env" >> .gitignore
  git rm --cached backend/.env
  ```

- [ ] **Rotate ALL exposed credentials immediately:**
  - [ ] Supabase ANON_KEY
  - [ ] Supabase SERVICE_ROLE_KEY
  - [ ] OpenRouter API Key
  - [ ] Gemini API Key
  - [ ] API Analytics Key

- [ ] **Use secrets manager for production:**
  - Option A: Environment variables in hosting platform (Railway, Render, Vercel)
  - Option B: AWS Secrets Manager / Google Secret Manager
  - Option C: Doppler / Vault for secrets management

### 2. Authentication

- [ ] **Set `AUTH_DISABLED=false` in production**
  ```env
  AUTH_DISABLED=false
  APP_ENV=production
  DEBUG=false
  ```

- [ ] **Configure Google OAuth for production domain:**
  - Add production URLs to Google Cloud Console
  - Update Supabase Auth settings with production redirect URLs

### 3. CORS Configuration

- [ ] **Update CORS_ORIGINS for production:**
  ```env
  CORS_ORIGINS=https://docs.google.com,https://your-domain.com
  ```

- [ ] **Remove wildcard headers if not needed:**
  ```python
  # In main.py, restrict to specific headers
  allow_headers=["Authorization", "Content-Type", "X-Requested-With"]
  ```

### 4. Database Setup

- [ ] **Create Supabase tables (if not exist):**

```sql
-- Users table
CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT UNIQUE NOT NULL,
  name TEXT,
  avatar_url TEXT,
  tier TEXT DEFAULT 'free',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Conversations table
CREATE TABLE IF NOT EXISTS conversations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  title TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Messages table
CREATE TABLE IF NOT EXISTS messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
  role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
  content TEXT NOT NULL,
  confidence_score FLOAT,
  sources JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Usage records table
CREATE TABLE IF NOT EXISTS usage_records (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  period TEXT NOT NULL,
  query_count INT DEFAULT 0,
  formula_count INT DEFAULT 0,
  chat_count INT DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id, period)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_usage_records_user_period ON usage_records(user_id, period);
```

- [ ] **Enable Row Level Security (RLS):**

```sql
-- Enable RLS on all tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE usage_records ENABLE ROW LEVEL SECURITY;

-- Users can only see their own data
CREATE POLICY "Users can view own data" ON users
  FOR SELECT USING (auth.uid() = id);

CREATE POLICY "Users can update own data" ON users
  FOR UPDATE USING (auth.uid() = id);

-- Conversations policy
CREATE POLICY "Users can view own conversations" ON conversations
  FOR ALL USING (auth.uid() = user_id);

-- Messages policy (through conversation ownership)
CREATE POLICY "Users can view own messages" ON messages
  FOR ALL USING (
    conversation_id IN (
      SELECT id FROM conversations WHERE user_id = auth.uid()
    )
  );

-- Usage records policy
CREATE POLICY "Users can view own usage" ON usage_records
  FOR SELECT USING (auth.uid() = user_id);
```

---

## HIGH Priority (Should Fix Before Launch)

### 5. Deployment Infrastructure

- [ ] **Create Dockerfile for backend:**

```dockerfile
# backend/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/api/health || exit 1

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Create docker-compose.yml:**

```yaml
# docker-compose.yml
version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - APP_ENV=production
      - DEBUG=false
    env_file:
      - ./backend/.env.production
    volumes:
      - chroma_data:/app/chroma_db
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped

volumes:
  chroma_data:
  redis_data:
```

### 6. Environment Configuration

- [ ] **Create `.env.production` template:**

```env
# Application
APP_NAME=SheetMind
APP_ENV=production
DEBUG=false
HOST=0.0.0.0
PORT=8000
API_PREFIX=/api

# Security
AUTH_DISABLED=false

# Supabase (use secrets manager in production)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# Redis (for caching and rate limiting)
REDIS_URL=redis://redis:6379/0

# AI Providers
OPENROUTER_API_KEY=your-openrouter-key

# LangChain Settings
LANGCHAIN_ENABLED=true
RAG_ENABLED=true
CHROMA_PERSIST_DIR=/app/chroma_db
RAG_THRESHOLD_ROWS=500
RAG_RESULTS_COUNT=30

# CORS
CORS_ORIGINS=https://docs.google.com
FRONTEND_URL=https://your-domain.com

# Rate Limiting
MEMORY_WINDOW_SIZE=10

# Payments (optional)
DODO_PAYMENTS_API_KEY=
DODO_PAYMENTS_WEBHOOK_KEY=
DODO_PAYMENTS_ENVIRONMENT=production
```

### 7. Google Apps Script Deployment

- [ ] **Update API endpoint in Code.gs:**
  ```javascript
  // Change from localhost to production URL
  const API_BASE_URL = 'https://your-production-api.com/api';
  ```

- [ ] **Deploy to Google Workspace Marketplace (optional):**
  - Create Google Cloud project
  - Configure OAuth consent screen
  - Submit for review

- [ ] **Manual deployment steps:**
  ```bash
  cd frontend
  npm run build
  # Copy dist/index.html content to GAS HTML file
  clasp push
  clasp deploy --description "Production v1.0"
  ```

### 8. SSL/TLS Configuration

- [ ] **Ensure HTTPS everywhere:**
  - Backend API must be served over HTTPS
  - Use Let's Encrypt or managed SSL from hosting provider
  - Redirect HTTP to HTTPS

### 9. Monitoring Setup

- [ ] **Add error tracking (Sentry):**
  ```python
  # In main.py
  import sentry_sdk
  sentry_sdk.init(
      dsn="your-sentry-dsn",
      environment=settings.APP_ENV,
      traces_sample_rate=0.1,
  )
  ```

- [ ] **Configure logging for production:**
  ```python
  # Use JSON logging for easier parsing
  import logging
  import json

  class JSONFormatter(logging.Formatter):
      def format(self, record):
          return json.dumps({
              "timestamp": self.formatTime(record),
              "level": record.levelname,
              "message": record.getMessage(),
              "module": record.module,
          })
  ```

---

## MEDIUM Priority (Recommended Before Launch)

### 10. Performance Optimization

- [ ] **Enable Redis caching in production:**
  - Ensure Redis URL is configured
  - Cache frequently accessed data
  - Set appropriate TTLs

- [ ] **Configure connection pooling:**
  - Supabase connection limits
  - Redis connection pool size

- [ ] **Add request timeouts:**
  ```python
  # For AI calls
  timeout = httpx.Timeout(30.0, connect=5.0)
  ```

### 11. Rate Limiting Refinement

- [ ] **Review rate limits for production:**
  ```python
  RATE_LIMITS = {
      "free": 10,   # requests per minute
      "pro": 30,
      "team": 100,
  }
  ```

- [ ] **Add burst protection:**
  - Consider token bucket algorithm for smoother limiting

### 12. Input Validation

- [ ] **Add request size limits:**
  ```python
  # In main.py
  from starlette.middleware.base import BaseHTTPMiddleware

  class LimitRequestSizeMiddleware(BaseHTTPMiddleware):
      async def dispatch(self, request, call_next):
          if request.headers.get("content-length"):
              if int(request.headers["content-length"]) > 10_000_000:  # 10MB
                  return JSONResponse(status_code=413, content={"detail": "Request too large"})
          return await call_next(request)
  ```

- [ ] **Validate sheet data size:**
  - Maximum cells: 50,000
  - Maximum cell content length: 10,000 characters

### 13. API Documentation

- [ ] **Enable OpenAPI docs for production:**
  ```python
  app = FastAPI(
      title="SheetMind API",
      description="AI-powered Google Sheets assistant",
      version="1.0.0",
      docs_url="/docs",  # Or None to disable in production
      redoc_url="/redoc",
  )
  ```

### 14. Backup Strategy

- [ ] **Configure Supabase backups:**
  - Enable Point-in-Time Recovery (PITR)
  - Set backup retention period
  - Test restore procedure

- [ ] **ChromaDB backup (if using RAG):**
  - Schedule regular backups of `/app/chroma_db`
  - Store in cloud storage (S3, GCS)

---

## LOW Priority (Nice to Have)

### 15. Testing

- [ ] **Create basic test suite:**
  ```python
  # tests/test_api.py
  from fastapi.testclient import TestClient
  from app.main import app

  client = TestClient(app)

  def test_health():
      response = client.get("/api/health")
      assert response.status_code == 200
      assert response.json()["status"] == "healthy"
  ```

- [ ] **Add CI/CD pipeline:**
  ```yaml
  # .github/workflows/test.yml
  name: Tests
  on: [push, pull_request]
  jobs:
    test:
      runs-on: ubuntu-latest
      steps:
        - uses: actions/checkout@v3
        - uses: actions/setup-python@v4
          with:
            python-version: '3.11'
        - run: pip install -r backend/requirements.txt
        - run: pip install pytest
        - run: pytest backend/tests/
  ```

### 16. Analytics & Metrics

- [ ] **Track key metrics:**
  - Requests per minute
  - Average response time
  - Error rate
  - LLM token usage
  - User retention

- [ ] **Set up dashboards:**
  - Use API Analytics (already integrated)
  - Add custom metrics to Grafana/DataDog

### 17. Payment Integration

- [ ] **Complete Dodo Payments setup:**
  - Create products in Dodo dashboard
  - Add product IDs to environment
  - Implement webhook validation
  - Test subscription flow

### 18. User Experience

- [ ] **Add loading states:**
  - Show progress for long operations
  - Implement request cancellation

- [ ] **Add error recovery:**
  - Retry failed requests
  - Show helpful error messages

---

## Deployment Options

### Option A: Railway (Recommended for MVP)

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and deploy
railway login
railway init
railway up
```

**Pros:** Easy setup, automatic SSL, built-in Redis
**Cons:** Can get expensive at scale

### Option B: Render

1. Connect GitHub repository
2. Add environment variables
3. Deploy with auto-scaling

**Pros:** Free tier, automatic deploys
**Cons:** Cold starts on free tier

### Option C: Google Cloud Run

```bash
# Build and push image
gcloud builds submit --tag gcr.io/PROJECT_ID/sheetmind-api

# Deploy
gcloud run deploy sheetmind-api \
  --image gcr.io/PROJECT_ID/sheetmind-api \
  --platform managed \
  --allow-unauthenticated
```

**Pros:** Scales to zero, pay-per-use
**Cons:** More complex setup

### Option D: DigitalOcean App Platform

1. Connect repository
2. Configure build settings
3. Add environment variables
4. Deploy

**Pros:** Simple pricing, good performance
**Cons:** Limited free tier

---

## Pre-Launch Checklist

### One Week Before Launch

- [ ] All CRITICAL items completed
- [ ] Security audit performed
- [ ] Load testing completed
- [ ] Monitoring configured
- [ ] Backup strategy tested
- [ ] Documentation updated

### Day Before Launch

- [ ] Final deployment to production
- [ ] Verify all endpoints working
- [ ] Test Google Sheets integration
- [ ] Verify authentication flow
- [ ] Check rate limiting works
- [ ] Confirm logging working

### Launch Day

- [ ] Monitor error rates closely
- [ ] Watch for unusual traffic patterns
- [ ] Be ready to scale if needed
- [ ] Have rollback plan ready
- [ ] Support channels ready

---

## Post-Launch

### First Week

- [ ] Monitor user feedback
- [ ] Fix critical bugs immediately
- [ ] Review performance metrics
- [ ] Adjust rate limits if needed

### First Month

- [ ] Analyze usage patterns
- [ ] Plan feature improvements
- [ ] Review and optimize costs
- [ ] Gather user testimonials

---

## Quick Commands Reference

```bash
# Start backend locally
cd backend && uvicorn app.main:app --reload --port 8000

# Build frontend
cd frontend && npm run build

# Deploy GAS
cd frontend && clasp push && clasp deploy

# Run tests
cd backend && pytest tests/

# Check logs (Docker)
docker logs -f sheetmind-backend

# Check health
curl https://your-api.com/api/health
```

---

## Support Contacts

- **Supabase Dashboard:** https://app.supabase.com
- **OpenRouter Dashboard:** https://openrouter.ai/dashboard
- **Google Cloud Console:** https://console.cloud.google.com
- **Dodo Payments:** https://dashboard.dodopayments.com

---

*Last updated: February 2026*
*SheetMind v1.0.0*
