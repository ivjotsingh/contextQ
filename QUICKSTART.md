# Quick Start Guide - ContextQ

This guide will help you get ContextQ up and running in minutes.

## Prerequisites

Before you start, make sure you have:

- **Python 3.11+** installed
- **Node.js 18+** installed
- **API Keys** for:
  - Anthropic (Claude) - [Get here](https://console.anthropic.com/)
  - Voyage AI (Embeddings) - [Get here](https://www.voyageai.com/) - **Free tier: 200M tokens**
  - Qdrant Cloud - [Get here](https://cloud.qdrant.io/) - **Free tier: 1GB**
  - Upstash Redis - [Get here](https://upstash.com/) - **Free tier: 10K commands/day**

## Step 1: Clone & Setup Environment

```bash
# Navigate to project directory
cd /Users/ivjot/Desktop/contextQ

# Copy environment template
cp .env.example .env

# Edit .env file with your API keys
# You can use nano, vim, or any text editor
nano .env
```

Fill in your `.env` file:
```bash
ANTHROPIC_API_KEY=sk-ant-api03-your-key-here
VOYAGE_API_KEY=your-voyage-api-key-here
QDRANT_URL=https://your-cluster.qdrant.io
QDRANT_API_KEY=your-qdrant-key-here
REDIS_URL=redis://default:your-password@your-redis.upstash.io:6379
ENVIRONMENT=development
DEBUG=false
```

## Step 2: Setup Backend

```bash
# Navigate to backend directory
cd backend

# Install uv if you don't have it (one-time setup)
# On macOS/Linux:
curl -LsSf https://astral.sh/uv/install.sh | sh
# Or with Homebrew:
# brew install uv

# Create virtual environment and install dependencies with uv
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -r requirements.txt

# Alternative: uv can manage everything automatically
# uv pip install -r requirements.txt  # Creates venv automatically if needed
```

## Step 3: Setup Frontend

```bash
# Open a new terminal window/tab
# Navigate to frontend directory
cd /Users/ivjot/Desktop/contextQ/frontend

# Install dependencies
npm install
```

## Step 4: Run the Application

### Option A: Development Mode (Recommended for development)

**Terminal 1 - Backend:**
```bash
cd /Users/ivjot/Desktop/contextQ/backend
source .venv/bin/activate  # If not already activated
# Or with uv: uv run uvicorn app.main:app --reload --port 8000
uvicorn app.main:app --reload --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process  ← Auto-reload enabled!
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

**Note**: The `--reload` flag enables **auto-reload** - the backend will automatically restart when you change Python files.

**Terminal 2 - Frontend:**
```bash
cd /Users/ivjot/Desktop/contextQ/frontend
npm run dev
```

You should see:
```
  VITE v6.0.1  ready in XXX ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
```

**Note**: Vite has **Hot Module Replacement (HMR)** enabled by default - changes to React components will update instantly without a full page reload!

### Option B: Production Mode (Single Process)

The backend can serve the frontend if it's built:

```bash
# Build frontend first
cd frontend
npm run build

# Run backend (it will serve the built frontend)
cd ../backend
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Visit: http://localhost:8000

## Step 5: Access the Application

- **Frontend**: http://localhost:5173 (development) or http://localhost:8000 (production)
- **API Docs**: http://localhost:8000/api/docs
- **Health Check**: http://localhost:8000/api/health

## Step 6: Test the Application

1. **Upload a document**:
   - Click "Upload" tab in sidebar
   - Drag & drop a PDF, DOCX, or TXT file
   - Wait for processing to complete

2. **Ask a question**:
   - Switch to "Chat" view
   - Type a question about your document
   - Press Enter or click Send
   - View the answer with source citations

## Troubleshooting

### Vector Dimension Mismatch

**Error**: `Vector dimension error: expected dim: 1024, got 512` (or similar)

This happens when you switch embedding providers or the Qdrant collection was created with different dimensions.

**Solution**: Reset the Qdrant collection:
```bash
cd backend
source .venv/bin/activate
python reset_qdrant.py
```

This will delete the old collection and create a new one with the correct dimensions.

### Backend Issues

**Import errors:**
```bash
# Make sure virtual environment is activated
source .venv/bin/activate

# Reinstall dependencies with uv (faster)
uv pip install -r requirements.txt

# Or with regular pip
pip install -r requirements.txt
```

**Port already in use:**
```bash
# Use a different port
uvicorn app.main:app --reload --port 8001
```

**Environment variables not loading:**
```bash
# Make sure .env file is in the backend directory
# Or set them manually:
export ANTHROPIC_API_KEY=your-key
export VOYAGE_API_KEY=your-key
# etc.
```

### Frontend Issues

**npm install fails:**
```bash
# Clear cache and retry
rm -rf node_modules package-lock.json
npm install
```

**Port already in use:**
```bash
# Vite will automatically use next available port
# Or specify manually in vite.config.js
```

**API connection errors:**
- Make sure backend is running on port 8000
- Check browser console for CORS errors
- Verify proxy settings in `vite.config.js`

### Common Errors

**"voyageai package not installed"**
```bash
pip install voyageai>=0.2.0
```

**"Qdrant connection failed"**
- Verify QDRANT_URL and QDRANT_API_KEY in .env
- Check if Qdrant collection exists (it will be created automatically)

**"Redis connection failed"**
- Verify REDIS_URL in .env
- Test connection: `redis-cli -u $REDIS_URL ping`

## Docker Deployment (Alternative)

If you prefer Docker:

```bash
# Build the image
docker build -t contextq .

# Run with environment variables
docker run -p 8000:8000 \
  --env-file .env \
  contextq
```

## Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Check [backend/README.md](backend/README.md) for API details
- Explore the code structure and customize as needed

## Getting Help

- Check the logs in terminal for error messages
- Visit API docs at http://localhost:8000/api/docs
- Review the health endpoint: http://localhost:8000/api/health

---

Happy coding! 🚀

