# ContextQ Quickstart

Get ContextQ running locally in **5 minutes** or deploy with Docker in **3 minutes**.

---

## Prerequisites

- **Python 3.11+** — [Download](https://www.python.org/downloads/)
- **Node.js 18+** — [Download](https://nodejs.org/)
- **uv** (Python package manager) — [Install](https://docs.astral.sh/uv/)
- **Docker** (optional, for containerized deployment) — [Install](https://docs.docker.com/get-docker/)

---

## Required Services & API Keys

| Service | Purpose | Free Tier | Get Started |
|---------|---------|-----------|-------------|
| **Anthropic** | LLM (Claude Sonnet 4) | Pay-as-you-go (~$0.003/query) | [Get API Key](https://console.anthropic.com/) |
| **Voyage AI** | Document embeddings | **200M tokens FREE** | [Get API Key](https://www.voyageai.com/) |
| **Qdrant Cloud** | Vector database | **1GB free forever** | [Create Cluster](https://cloud.qdrant.io/) |
| **Firebase** | Chat history + sessions | **Free tier** (Firestore) | [Create Project](https://console.firebase.google.com/) |

---

## Setup Guide

### 1. Clone the Repository

```bash
git clone https://github.com/ivjotsingh/contextQ.git
cd contextQ
```

### 2. Get Your Firebase Service Account

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Select or create a project
3. Navigate to **Project Settings** (⚙️ icon)
4. Go to **Service Accounts** tab
5. Click **Generate new private key**
6. Download the JSON file (e.g., `firebase-key.json`)

**Important:** Keep this file secure and never commit it to version control.

### 3. Create Firestore Composite Index

This index is required for listing chats by session:

1. In Firebase Console, go to **Firestore Database**
2. Click **Indexes** tab → **Create Index**
3. Configure:
   - **Collection ID**: `chats`
   - **Fields**:
     - `session_id` — **Ascending**
     - `last_activity` — **Descending**  
     - `__name__` — **Descending**
   - **Query scope**: Collection
4. Click **Create**

> Note: Index creation can take a few minutes.

---

## Option A: Local Development (Recommended for Development)

### 1. Setup Environment Variables

```bash
cp .env.example .env
```

Edit `.env` and add your credentials:

```bash
# .env
ANTHROPIC_API_KEY=sk-ant-api03-...
VOYAGE_API_KEY=pa-...
QDRANT_URL=https://your-cluster.qdrant.io:6333
QDRANT_API_KEY=...

# For local dev, use file path (easier)
FIREBASE_CREDENTIALS=/absolute/path/to/your-firebase-key.json
```

### 2. Start Backend

```bash
cd backend

# Install dependencies
uv sync

# Run with hot reload
uv run uvicorn main:app --reload --port 8000
```

Backend will be available at **http://localhost:8000**

### 3. Start Frontend (New Terminal)

```bash
cd frontend

# Install dependencies
npm install

# Run dev server
npm run dev
```

Frontend will be available at **http://localhost:5173**

### 4. Verify Everything Works

```bash
# Health check
curl http://localhost:8000/api/health

# Expected response:
# {"status":"healthy","qdrant_connected":true,"firestore_connected":true}
```

---

## Option B: Docker (Recommended for Production)

### 1. Setup Environment Variables

```bash
cp .env.example .env
```

### 2. Encode Firebase Credentials for Docker

**Why?** Docker environment variables can't handle multi-line JSON files directly, so we base64 encode them.

```bash
# Encode your Firebase JSON to base64 (single line)
cat /path/to/your-firebase-key.json | base64 | tr -d '\n' > firebase_base64.txt

# The output is a long base64 string like:
# eyJ0eXBlIjoic2VydmljZV9hY2NvdW50IiwicHJvamVjdF9pZCI6...
```

### 3. Update `.env` with Base64 Credentials

```bash
# .env
ANTHROPIC_API_KEY=sk-ant-api03-...
VOYAGE_API_KEY=pa-...
QDRANT_URL=https://your-cluster.qdrant.io:6333
QDRANT_API_KEY=...

# Paste the base64 string from firebase_base64.txt
FIREBASE_CREDENTIALS=eyJ0eXBlIjoic2VydmljZV9hY2NvdW50IiwicHJvamVjdF9pZCI6...
```

### 4. Build & Run

```bash
# Build image
docker build -t contextq .

# Run container
docker run -d \
  --name contextq \
  -p 8000:8000 \
  --env-file .env \
  contextq

# View logs
docker logs -f contextq
```

Application will be available at **http://localhost:8000**

---

## Troubleshooting

### ❌ "FIREBASE_CREDENTIALS is not valid JSON, file path, or base64"

**Solution:**
- **For local dev**: Ensure the file path is absolute and the JSON file exists
- **For Docker**: Make sure you base64 encoded the JSON correctly:
  ```bash
  cat your-firebase-key.json | base64 | tr -d '\n'
  ```

### ❌ "Cannot connect to Qdrant"

**Solution:**
- Ensure `QDRANT_URL` includes the port `:6333`
- Example: `https://abc-xyz.us-east4-0.gcp.cloud.qdrant.io:6333`
- Verify your API key is correct in Qdrant Cloud dashboard

### ❌ "Embedding service validation failed"

**Solution:**
- Check your `VOYAGE_API_KEY` is valid
- Go to [Voyage AI Dashboard](https://www.voyageai.com/) to verify
- Free tier provides 200M tokens

### ❌ "Firestore index not found"

**Solution:**
- You need to create the composite index manually in Firebase Console
- See **Step 3** in setup above
- Index creation takes a few minutes — wait and retry

### ❌ Documents not showing after upload

**Solution:**
- Check browser console for errors (F12)
- Verify the upload completed (check backend logs)
- Try refreshing the page

---

## Next Steps

1. **Upload a document** — Try PDF, DOCX, or TXT (max 10MB)
2. **Ask questions** — Natural language queries about your documents
3. **View sources** — Click the sources button to see where answers came from
4. **Create multiple chats** — Each chat maintains its own conversation history

---

## Development Workflow

### Running Tests

```bash
cd backend
uv run pytest -v

# With coverage
uv run pytest --cov=. --cov-report=html
```

### Linting

```bash
cd backend
uv run ruff check .

# Auto-fix
uv run ruff check . --fix
```

### Pre-commit Hooks

```bash
cd backend
uv run pre-commit install
uv run pre-commit run --all-files
```

---

## Production Deployment Checklist

Before deploying to production:

- [ ] Set `ENVIRONMENT=production` in `.env`
- [ ] Use base64-encoded Firebase credentials in Docker
- [ ] Configure CORS origins in `config.py` to match your frontend domain
- [ ] Set up HTTPS (use reverse proxy like nginx, Caddy, or cloud load balancer)
- [ ] Enable Firebase security rules
- [ ] Set up monitoring (Sentry, Datadog, etc.)
- [ ] Configure backups for Firestore
- [ ] Review rate limits in `config.py`
- [ ] Use secrets management (AWS Secrets Manager, Google Secret Manager, etc.)

---

## Additional Resources

- **Full Documentation**: See [README.md](README.md)
- **API Documentation**: Visit `/docs` endpoint when backend is running
- **Issues**: [GitHub Issues](https://github.com/ivjotsingh/contextQ/issues)

---

**Questions?** Check the troubleshooting section above or open an issue on GitHub.
