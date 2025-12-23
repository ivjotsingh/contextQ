# ContextQ Quickstart

Get ContextQ running in 5 minutes.

## Prerequisites

- **Node.js 18+** - [Install](https://nodejs.org/)  
- **Python 3.11+** - [Install](https://www.python.org/)
- **Docker** (optional) - [Install](https://docs.docker.com/get-docker/)

### Required API Keys

| Service | Purpose | Get Key |
|---------|---------|---------|
| Anthropic | LLM (Claude) | https://console.anthropic.com/ |
| Voyage AI | Embeddings (200M free tokens) | https://www.voyageai.com/ |
| Qdrant Cloud | Vector database (1GB free) | https://cloud.qdrant.io/ |
| Firebase | Chat history storage | https://console.firebase.google.com/ |

---

## Option 1: Docker (Recommended)

### Step 1: Clone & Setup

```bash
git clone https://github.com/yourusername/contextq.git
cd contextq
cp .env.example .env
```

### Step 2: Add API Keys to `.env`

Edit `.env` and fill in your API keys:

```bash
# .env
ANTHROPIC_API_KEY=sk-ant-...
VOYAGE_API_KEY=pa-...
QDRANT_URL=https://xxx.cloud.qdrant.io:6333
QDRANT_API_KEY=...
```

### Step 3: Add Firebase Credentials (Base64)

Firebase credentials contain newlines (in the private key), so we base64 encode them:

```bash
# Convert your Firebase JSON to base64 and add to .env
BASE64=$(cat path/to/your-firebase-credentials.json | base64 | tr -d '\n')
echo "FIREBASE_CREDENTIALS=$BASE64" >> .env
```

### Step 4: Build & Run

```bash
docker build -t contextq .
docker run -p 8000:8000 --env-file .env contextq
```

### Step 5: Open App

Visit http://localhost:8000

---

## Option 2: Local Development

### Step 1: Clone & Setup

```bash
git clone https://github.com/yourusername/contextq.git
cd contextq
cp .env.example .env
```

### Step 2: Add API Keys to `.env`

Edit `.env` with your keys. For local development, you can use a file path for Firebase:

```bash
ANTHROPIC_API_KEY=sk-ant-...
VOYAGE_API_KEY=pa-...
QDRANT_URL=https://xxx.cloud.qdrant.io:6333
QDRANT_API_KEY=...
FIREBASE_CREDENTIALS=/path/to/your-firebase-credentials.json
```

### Step 3: Start Backend

```bash
cd backend

# Install uv if not installed
# curl -LsSf https://astral.sh/uv/install.sh | sh

uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Step 4: Start Frontend (new terminal)

```bash
cd frontend
npm install
npm run dev
```

### Step 5: Open App

Visit http://localhost:5173

---

## Firebase Setup

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Create or select a project
3. Go to **Project Settings** → **Service Accounts**
4. Click **Generate new private key**
5. Download the JSON file

For Docker, base64 encode it:
```bash
cat your-firebase-key.json | base64 | tr -d '\n'
```

---

## Verify It Works

```bash
# Health check
curl http://localhost:8000/api/health

# Should return:
# {"status":"healthy",...}
```

---

## Troubleshooting

### Docker: "FIREBASE_CREDENTIALS is not valid JSON"
- Make sure you base64 encoded the JSON file
- Don't use a file path in Docker, use base64

### Local: "Cannot connect to Qdrant"
- Check your `QDRANT_URL` includes the port `:6333`
- Verify API key is correct

### "Embedding service validation failed"
- Check your `VOYAGE_API_KEY` is valid
- Free tier: 200M tokens

---

## Next Steps

- Upload a PDF/DOCX/TXT file
- Ask questions about the document
- View source citations in responses

For full documentation, see [README.md](README.md).
