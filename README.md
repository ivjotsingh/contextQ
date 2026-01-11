# ContextQ

> **Production-Grade Document Q&A with Intelligent RAG** — A sophisticated retrieval-augmented generation system featuring smart query expansion, streaming responses, and transparent source attribution. Built for performance, scalability, and reliability.

![Python](https://img.shields.io/badge/Python-3.11+-blue?style=flat-square&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green?style=flat-square&logo=fastapi)
![React](https://img.shields.io/badge/React-18+-61DAFB?style=flat-square&logo=react)
![TypeScript](https://img.shields.io/badge/TypeScript-5+-3178C6?style=flat-square&logo=typescript)
![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)

---

## 🏆 What Makes ContextQ Special

ContextQ isn't just another RAG demo — it's a **production-ready**, **enterprise-grade** system demonstrating best practices in modern AI application development:

### 🎯 Intelligent Query Routing
- **Automatic query analysis** — Distinguishes greetings, meta-questions, and document queries
- **Fast-path optimization** — Skip LLM analysis for simple queries
- **Query expansion for context-dependent questions** — Follow-ups like "now?" automatically expand to full queries
- **Document-aware queries** — System knows actual filenames and references them precisely

### 🚀 Production-Grade Architecture
- **Clean Architecture** — Feature modules, dependency injection, standardized responses
- **Dockerized deployment** — Multi-stage build for optimized container images
- **Pre-commit hooks** — Automated linting (Ruff) and testing before every commit
- **Request tracing** — Every request gets a unique ID tracked across all logs
- **Graceful degradation** — Chat works even if persistence fails
- **LRU-cached singletons** — Prevents memory leaks from repeated dependency instantiation
- **Rate limiting** — Per-minute and per-hour limits protect against cost overruns
- **Health checks** — Qdrant and Firestore connectivity monitoring
- **Lifespan management** — Proper async resource initialization and cleanup

### 💡 Sophisticated RAG Pipeline
- **Dynamic relevance thresholding** — Configurable similarity scores filter low-quality matches
- **Session-based document scoping** — Isolates documents per browser session
- **Filename-aware embeddings** — Queries like "show me turnus.pdf" actually work
- **Embedding cache** — In-memory LRU cache reduces API calls and costs
- **Chunk deduplication** — Prevents redundant context in retrieval
- **Source transparency** — Every answer includes  passages with relevance scores

### 🎨 Premium User Experience
- **Real-time streaming** — SSE streaming with word-by-word updates
- **Progress tracking** — Upload progress with XMLHttpRequest
- **Expandable sources** — Click to see full context passages
- **Source grouping** — "X sources from Y documents" clarity
- **Session persistence** — Documents and chats survive page refresh
- **Modern UI** — Glassmorphism, dark mode, smooth animations

### 📊 Enterprise-Ready Features
- **Duplicate detection** — SHA-256 content hashing prevents re-processing
- **Path traversal protection** — Filename sanitization prevents directory escape attacks
- **Prompt injection protection** — System prompts ignore malicious instructions in document content
- **Table extraction** — DOCX tables preserved correctly
- **Async/await throughout** — Non-blocking I/O for scalability
- **Structured logging** — Production-ready observability
- **Type safety** — Pydantic models, TypeScript strict mode
- **Error boundaries** — React error boundaries prevent UI crashes

---

## 🎉 Cost-Effective Free Tier

Run the entire stack for **free** during development:

| Service | Free Tier | Purpose |
|---------|-----------|---------|
| **Voyage AI** | 200M tokens | Document embeddings (voyage-3-lite, 512d) |
| **Qdrant Cloud** | 1GB storage | Vector database for semantic search |
| **Firebase** | Firestore free tier | Chat history and session persistence |
| **Claude API** | Pay-as-you-go | Answer generation |

---

## 🏗️ Architecture Overview

```
┌────────────────────────────────────────────────────────────────────────────┐
│                            ContextQ System                                  │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌────────────────────┐        ┌──────────────────────────────────────┐   │
│  │  React Frontend    │ ────▶  │       FastAPI Backend                 │   │
│  │  (TypeScript)      │        │                                       │   │
│  │                    │        │  ┌─────────────────────────────────┐  │   │
│  │  • Drag-drop       │        │  │  Query Router (Intelligent)     │  │   │
│  │    upload          │        │  ├─────────────────────────────────┤  │   │
│  │  • Streaming       │        │  │  • Fast-path for greetings      │  │   │
│  │    chat UI         │        │  │  • Query expansion             │  │   │
│  │  • Source cards    │        │  │  • Document context injection   │  │   │
│  │  • Progress        │        │  └─────────────────────────────────┘  │   │
│  │    tracking        │        │                                       │   │
│  │  • Session         │        │  ┌─────────────────────────────────┐  │   │
│  │    management      │        │  │  RAG Pipeline                   │  │   │
│  └────────────────────┘        │  ├─────────────────────────────────┤  │   │
│                                │  │  • Voyage AI embeddings         │  │   │
│                                │  │  • Qdrant vector search         │  │   │
│                                │  │  • Relevance filtering          │  │   │
│                                │  │  • Claude generation            │  │   │
│                                │  └─────────────────────────────────┘  │   │
│                                │                                       │   │
│                                │  ┌─────────────────────────────────┐  │   │
│                                │  │  Document Processor             │  │   │
│                                │  ├─────────────────────────────────┤  │   │
│                                │  │  • PDF/DOCX/TXT parsing         │  │   │
│                                │  │  • Table extraction             │  │   │
│                                │  │  • Smart chunking (overlapping) │  │   │
│                                │  │  • Duplicate detection (SHA256) │  │   │
│                                │  └─────────────────────────────────┘  │   │
│                                └──────────────────────────────────────┘   │
│                                             │                              │
│                 ┌───────────────────────────┼───────────────────────┐      │
│                 │                           │                       │      │
│                 ▼                           ▼                       ▼      │
│        ┌──────────────┐            ┌──────────────┐       ┌────────────┐  │
│        │ Qdrant Cloud │            │   Firebase   │       │   Claude   │  │
│        │              │            │              │       │     +      │  │
│        │ • Vectors    │            │ • Chats      │       │  Voyage AI │  │
│        │ • Metadata   │            │ • Sessions   │       │            │  │
│        │ • Filtering  │            │ • History    │       │            │  │
│        └──────────────┘            └──────────────┘       └────────────┘  │
│                                                                             │
└────────────────────────────────────────────────────────────────────────────┘
```

### Request Flow: Document Query

```
1. User Query: "What are the main risks in the report?"
       │
       ▼
2. Query Analysis (Claude)
   → skip_rag=false, expanded_query="What are the main risks in the report?"
       │
       ▼
3. Fetch Session Documents
   → [report.pdf, summary.docx]
       │
       ▼
4. Embed Query (Voyage AI)
   → "Document: report.pdf\n\nWhat are the main risks..."
       │
       ▼
5. Vector Search (Qdrant)
   → Top 5 chunks, relevance > 0.34
       │
       ▼
6. Filter by Relevance
   → 3 chunks pass threshold
       │
       ▼
7. Generate Answer (Claude, SSE streaming)
   → "Based on the provided documents, the main risks are..."
       │
       ▼
8. Return with Sources
   → Full answer + 3 source cards with passages
```

---

## 🧩 Key Features Breakdown

### Document Processing Pipeline

| Feature | Implementation | Why It Matters |
|---------|----------------|----------------|
| **Multi-format support** | PyPDF2, python-docx, built-in text | PDF, DOCX, TXT all supported |
| **Table extraction** | DOCX table parsing to Markdown | Preserves structured data |
| **Duplicate detection** | SHA-256 content hashing | Prevents wasting embedding tokens |
| **Smart chunking** | Recursive splitting at sentence boundaries | Better semantic coherence |
| **Overlapping chunks** | 1500 chars, 200 overlap (~13%) | Prevents context loss at boundaries |
| **Filename in embeddings** | `"Document: {filename}\n\n{content}"` | Enables filename-based queries |

### Intelligent Query Routing

```python
# Fast Path (50ms)
"hi" → No LLM call → Standard greeting

# Meta Query (500ms)
"what can you do?" → LLM analysis → skip_rag=true → Capabilities response

# Single Document Query (2s)
"summarize this doc" → LLM analysis → RAG pipeline

# Multi-Document Query (3s)
"compare resume.pdf and job description.pdf"
  → LLM analysis 
  → expanded_query="Comparison of content between resume.pdf and job description.pdf"
  → RAG pipeline
```

### Streaming Response System

- **Server-Sent Events (SSE)** — Real-time word-by-word streaming
- **Source-first delivery** — Sources appear before answer starts
- **Graceful completion** — `done` event signals end
- **Error handling** — Network errors don't crash the UI
- **Cancellation support** — Abort ongoing requests

### Session Architecture

| Identifier | Scope | Storage | Purpose |
|------------|-------|---------|---------|
| `session_id` | Browser | Cookie | Document isolation per browser |
| `chat_id` | Conversation | Firestore | Multiple chats per session |
| `doc_id` | Document | Qdrant | Unique document identifier |

**Design rationale**: One browser can have multiple conversations, each accessing the same set of uploaded documents.

---

## 🛠️ Tech Stack Deep Dive

### Backend

| Component | Choice | Rationale |
|-----------|--------|-----------|
| **Python 3.11** | Latest stable | Union types native, modern async support |
| **FastAPI 0.115** | Modern async framework | Native async, auto OpenAPI docs, Pydantic v2 |
| **uv** | Package manager | 10-100x faster than pip, deterministic installs |
| **Ruff** | Linting | Rust-based, 10-100x faster than pylint/flake8 |
| **pytest** | Testing | Industry standard, rich plugin ecosystem |

### Frontend

| Component | Choice | Rationale |
|-----------|--------|-----------|
| **React 18** | UI framework | Concurrent rendering, best ecosystem |
| **TypeScript 5** | Type safety | Catch errors at compile time |
| **Vite** | Build tool | Instant HMR, esbuild speed |
| **Tailwind CSS** | Styling | Utility-first, no CSS naming conflicts |
| **Lucide React** | Icons | Tree-shakeable, modern design |

### AI Services

| Service | Model | Purpose | Performance |
|---------|-------|---------|-------------|
| **Voyage AI** | voyage-3-lite (512d) | Embeddings | 200M free tokens, SOTA retrieval |
| **Claude** | Sonnet 4 | Generation | Superior reasoning, context following |

**Why Voyage over OpenAI?** 
- ✅ Free 200M tokens (vs OpenAI's paid-only)
- ✅ Optimized for RAG use cases with efficient 512d vectors

**Why Claude over GPT?**
- ✅ Better instruction following
- ✅ Lower hallucination rate
- ✅ Superior at citing sources accurately

---

## 📐 Production Engineering Highlights

### Dependency Injection with LRU Caching

```python
# ❌ Memory leak - creates new instance per request
def get_vector_store():
    return VectorStoreService()

# ✅ Singleton pattern - one instance app-wide
@lru_cache(maxsize=1)
def get_vector_store():
    return VectorStoreService()
```

**Impact**: Prevents memory leaks from instantiating expensive services (Qdrant clients, embedding models) per request.

### Request Tracing

Every request gets a unique 8-char ID:

```python
request_id = str(uuid.uuid4())[:8]
logger.info("[%s] Processing query: %s", request_id, question[:100])
# ... later ...
logger.error("[%s] RAG pipeline failed: %s", request_id, error)
```

**Impact**: Debug production issues by grepping logs for `[abc12345]`.

### Graceful Degradation

```python
try:
    await firestore.save_message(chat_id, message)
except Exception as e:
    logger.warning("Failed to save to Firestore: %s", e)
    # Chat continues working without persistence
```

**Impact**: Chat remains functional even if Firebase is down.

### Rate Limiting (Sliding Window)

```python
# Per-minute: Burst protection
# Per-hour: Cost control
RateLimitConfig(
    requests_per_minute=20,
    requests_per_hour=200,
)
```

**Impact**: Prevents API cost explosions from bugs or abuse.

---

## 🧪 Testing Strategy

```bash
# Run tests
uv run pytest -v

# With coverage
uv run pytest --cov=. --cov-report=html
```

**Current Coverage**: ~40%

Covered areas:
- ✅ Chunking logic (overlapping, sentence boundaries)
- ✅ Document parsing (PDF, DOCX, TXT)
- ✅ Duplicate detection (hash validation)

*Higher coverage would add integration tests for Qdrant/Firebase/Claude (requires mocking or paid test instances).*

---

## 📂 Project Structure (Clean Architecture)

```
backend/
├── main.py                      # FastAPI app, CORS, lifespan
├── config.py                    # Pydantic settings with env vars
├── dependencies.py              # DI with LRU-cached singletons
├── responses.py                 # Standardized ResponseCode enum
├── router.py                    # Route aggregator
│
├── apps/                        # Feature modules (vertical slices)
│   ├── chat/
│   │   ├── handlers/
│   │   │   ├── stream_response.py    # SSE streaming, query routing
│   │   │   └── get_chat_history.py   # Conversation history
│   │   ├── chat_history.py           # Persistence manager
│   │   ├── session_helpers.py         # Cookie management
│   │   └── routes.py
│   │
│   ├── documents/
│   │   ├── handlers/
│   │   │   ├── upload_document.py    # Parse, chunk, embed, store
│   │   │   ├── list_documents.py     # Session-scoped listing
│   │   │   └── delete_document.py    # Qdrant + metadata cleanup
│   │   └── routes.py
│   │
│   └── health/
│       └── handlers/check_health.py  # Qdrant + Firebase health
│
├── services/                    # Reusable business logic
│   ├── document.py              # PDF/DOCX/TXT parsing + tables
│   ├── chunker.py               # Recursive text splitting
│   ├── embeddings.py            # Voyage AI with retry logic
│   ├── vector_store.py          # Qdrant CRUD + search
│   └── rag.py                   # Pure retrieval + generation
│
├── llm/
│   ├── service.py               # LLM abstraction (Claude)
│   └── prompts/                 # Engineered system prompts
│       ├── assistant.py         # General assistant capabilities
│       ├── document_qa.py       # RAG-specific instructions
│       └── query_analysis.py    # Query routing (skip_rag, expansion)
│
├── middleware/
│   └── rate_limit.py            # Sliding window rate limiter
│
├── db/
│   └── firestore.py             # Firebase operations
│
└── tests/
    ├── test_chunker.py          # Chunking edge cases
    └── test_document.py         # Parsing validation
```

**Design Principles**:
- **Feature modules in `/apps`** — Each feature is self-contained
- **Reusable services in `/services`** — Domain-agnostic logic
- **Clean separation** — Handlers call services, services don't know HTTP

---

## 🎯 Design Decisions

### Why This Chunking Strategy?

```python
CHUNK_SIZE = 1500      # ~375 tokens at 4 chars/token
CHUNK_OVERLAP = 200    # ~13% overlap
```

**Rationale**:
1. **Voyage-3-lite optimized for 300-500 tokens** — Larger chunks would exceed model sweet spot
2. **Overlap preserves context** — Prevents information loss at chunk boundaries
3. **Sentence-aware breaking** — Chunks don't split mid-sentence (when possible)
4. **Industry standard** — Research shows 10-20% overlap optimal for retrieval

### Why Firebase for Chat History?

| Alternative | Cons | Firebase Pros |
|-------------|------|---------------|
| **PostgreSQL** | Infrastructure overhead, need vector extension | Serverless, free tier, real-time |
| **Redis** | Volatile, need backup strategy | Persistent, indexed queries |
| **Qdrant** | Not optimized for transactional data | Purpose-built for chat |

**Winner**: Firebase Firestore — Serverless, persistent, free tier, composite indexes.

### Why Cookie-Based Sessions?

| Alternative | Cons | Cookie Pros |
|-------------|------|-------------|
| **JWT tokens** | Requires auth system, expiration management | Automatic browser handling |
| **URL params** | Insecure, breaks on copy/paste | httpOnly, secure flags |
| **Local storage** | Per-origin, cross-tab sync issues | Server-controlled |

**Winner**: Session cookies — Simple, secure, no frontend state management.

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.11+**
- **Node 18+** (for frontend)
- **API Keys**: [Voyage AI](https://www.voyageai.com/), [Anthropic Claude](https://www.anthropic.com/)
- **Firebase Project**: [Create free project](https://console.firebase.google.com/)
- **Qdrant Cloud**: [Free 1GB cluster](https://qdrant.tech/)

### Setup (5 minutes)

```bash
# 1. Clone
git clone https://github.com/ivjotsingh/contextQ.git
cd contextQ

# 2. Backend setup
cd backend
cp .env.example .env
# Edit .env with your API keys

# Install dependencies
uv sync

# Run backend
uv run uvicorn main:app --reload
# → http://localhost:8000

# 3. Frontend setup (new terminal)
cd ../frontend
npm install
npm run dev
# → http://localhost:5173
```

### Environment Variables

```bash
# .env file
ANTHROPIC_API_KEY=sk-ant-...
VOYAGE_API_KEY=pa-...

# Firebase (from firebase console → project settings)
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_PRIVATE_KEY_ID=abc123...
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n..."
FIREBASE_CLIENT_EMAIL=firebase-adminsdk-...@....iam.gserviceaccount.com
FIREBASE_CLIENT_ID=123456789...

# Qdrant Cloud
QDRANT_URL=https://your-cluster.qdrant.io
QDRANT_API_KEY=your-api-key
```

### Firebase Index Setup

Create composite index in [Firestore Console](https://console.firebase.google.com/):

| Collection | Fields (in order) | Type |
|------------|-------------------|------|
| `chats` | `session_id` | Ascending |
| `chats` | `last_activity` | Descending |
| `chats` | `__name__` | Descending |

---

## 📚 API Documentation

Auto-generated OpenAPI docs at `/docs` when running backend.

### Example: Stream Chat Response

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -H "Cookie: session_id=$SESSION_ID" \
  -d '{
    "question": "What are the key findings?",
    "chat_id": "abc-123",
    "doc_ids": null
  }'
```

Response (SSE stream):
```
data: {"type":"sources","sources":[{"text":"...","filename":"report.pdf","relevance_score":0.89}]}

data: {"type":"content","content":"Based"}
data: {"type":"content","content":" on"}
data: {"type":"content","content":" the"}
...
data: {"type":"done"}
```

---

## 🏅 Production Deployment Checklist

- [ ] Set `CORS_ORIGINS` to your frontend domain
- [ ] Enable Firebase security rules  
- [ ] Set up Qdrant authentication
- [ ] Configure rate limits for production scale
- [ ] Set `secure=True` for session cookies (HTTPS only)
- [ ] Add monitoring (Sentry, Datadog, etc.)
- [ ] Set up backup for Firestore
- [ ] Configure auto-scaling for FastAPI workers
- [ ] Add CDN for frontend static files
- [ ] Enable Qdrant backups

---

## 🔮 Future Improvements

### Out of Scope for This Project

**RAG & Retrieval Enhancements:**
- **Hybrid search** — Combine BM25 (keyword) + vector (semantic) for best results
- **Semantic chunking** — Chunk by meaning instead of fixed size
- **Multi-modal support** — Extract and search images/charts from PDFs
- **Citation markers** — LLM outputs [1], [2] references linked to source chunks

**Production Infrastructure:**
- **Caching layer** — Redis for embeddings, responses, and hot documents
- **Cost tracking** — Real-time API cost monitoring with budget alerts
- **Latency optimizations** — Parallel embedding, response streaming from first token

**Security & Compliance:**
- **Authentication** — User accounts with JWT, role-based access control
- **Document-level permissions** — Multi-tenant isolation, access control lists
- **Output validation** — PII detection, toxic content filtering
- **GDPR compliance** — Right to delete, data export

**User Experience:**
- **OCR support** — Scanned PDFs via pytesseract or AWS Textract
- **Multi-language** — i18n for global users
- **Export functionality** — Chat history to PDF/Markdown
- **Document annotations** — Highlight and note passages
- **Voice input/output** — Speech-to-text queries, text-to-speech answers
- **Collaborative Q&A** — Multiple users asking about shared documents

**Advanced Features:**
- **Document versioning** — Track changes, compare versions
- **Usage analytics** — User behavior insights, popular queries
- **Smart suggestions** — Recommend related questions based on context

---

## 🤝 Acknowledgments

Built using industry-best practices from:
- [FastAPI Best Practices](https://github.com/zhanymkanov/fastapi-best-practices)
- [Qdrant RAG Patterns](https://qdrant.tech/documentation/tutorials/rag/)
- [React TypeScript Patterns](https://react-typescript-cheatsheet.netlify.app/)

---

## 📄 License

MIT — See [LICENSE](LICENSE) for details.

---

**Built with ❤️ for production-grade AI applications**

[View on GitHub](https://github.com/ivjotsingh/contextQ/tree/contextQ)
