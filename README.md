# ContextQ

> A retrieval-augmented document chat system that allows users to upload documents and ask grounded questions with transparent source attribution.

![ContextQ](https://img.shields.io/badge/Python-3.11+-blue?style=flat-square&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green?style=flat-square&logo=fastapi)
![React](https://img.shields.io/badge/React-18+-61DAFB?style=flat-square&logo=react)
![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)

## Overview

ContextQ is a RAG (Retrieval-Augmented Generation) powered application that enables users to:

- **Upload documents** (PDF, DOCX, TXT)
- **Ask natural language questions** about the content
- **Get accurate answers** with source citations
- **View source passages** used to generate each answer

### 🎉 Free Tier Available

- **Voyage AI Embeddings**: 200 million tokens free ([Voyage AI](https://www.voyageai.com/))
- **Qdrant Cloud**: 1GB free forever
- **Upstash Redis**: 10K commands/day free

### Key Features

- 📄 **Multi-format support** - PDF, Word, and plain text files
- 🔍 **Semantic search** - Find relevant passages using vector embeddings
- 💬 **Streaming responses** - Real-time answer generation with SSE
- 📚 **Source attribution** - Every answer cites its sources
- ⚡ **Smart caching** - Fast responses for repeated queries
- 🔒 **Privacy-focused** - Session-based, no persistent user data
- 🧠 **Query decomposition** - Complex multi-document queries are split into sub-queries for better retrieval
- 📝 **Conversation summarization** - Long chats are summarized to manage context window efficiently
- 🔄 **Duplicate detection** - Content hashing prevents re-processing identical documents
- 🎯 **Smart query routing** - General questions (greetings, help) skip RAG for faster response

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              ContextQ                                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────────┐         ┌──────────────────────────────────────┐  │
│  │  React Frontend  │ ──────▶ │         FastAPI Backend              │  │
│  │                  │         │                                      │  │
│  │  • File Upload   │         │  • Document Processing               │  │
│  │  • Chat UI       │         │  • Text Chunking                     │  │
│  │  • Source View   │         │  • Embedding Generation              │  │
│  │  • Streaming     │         │  • Vector Search                     │  │
│  └──────────────────┘         │  • RAG Pipeline                      │  │
│                               └──────────────────────────────────────┘  │
│                                            │                             │
│                    ┌───────────────────────┼───────────────────────┐    │
│                    │                       │                       │    │
│                    ▼                       ▼                       ▼    │
│           ┌──────────────┐       ┌──────────────┐       ┌────────────┐ │
│           │ Qdrant Cloud │       │    Redis     │       │  Claude +  │ │
│           │  (Vectors)   │       │   (Cache)    │       │ Voyage+Claude│ │
│           └──────────────┘       └──────────────┘       └────────────┘ │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Tech Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| Frontend | React 18, Vite, Tailwind CSS | Modern, responsive UI |
| Backend | FastAPI, Python 3.11 | High-performance API |
| LLM | Claude 3.5 Sonnet | Answer generation |
| Embeddings | Voyage AI voyage-3-lite (512d) | Semantic search (Free: 200M tokens) |
| Vector DB | Qdrant Cloud | Vector storage & search |
| Cache | Upstash Redis | Response & embedding cache |
| PDF Parsing | PyMuPDF | Fast, accurate extraction |

## Quick Start

👉 **[See QUICKSTART.md for step-by-step setup with copy-paste commands](QUICKSTART.md)**

### TL;DR (Docker)

```bash
# Clone
git clone https://github.com/yourusername/contextq.git && cd contextq

# Setup env
cp .env.example .env
# Edit .env with your API keys (Anthropic, Voyage, Qdrant, Firebase)

# Firebase credentials must be base64 encoded for Docker:
cat /path/to/firebase-creds.json | base64 | tr -d '\n'
# Add result to .env as FIREBASE_CREDENTIALS=<base64-string>

# Build & run
docker build -t contextq .
docker run -p 8000:8000 --env-file .env contextq
```

Open http://localhost:8000

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/upload` | Upload a document |
| POST | `/api/chat` | Ask a question |
| POST | `/api/chat/stream` | Ask with streaming response |
| GET | `/api/documents` | List uploaded documents |
| DELETE | `/api/documents/{id}` | Delete a document |
| GET | `/api/health` | Health check |

### Example: Upload Document

```bash
curl -X POST http://localhost:8000/api/upload \
  -F "file=@document.pdf"
```

### Example: Ask Question

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the main topic of this document?"}'
```

## Docker Deployment

See [QUICKSTART.md](QUICKSTART.md) for Docker setup with base64-encoded Firebase credentials.

### Deploy to Cloud

The app can be deployed to:
- **Railway** - One-click deploy
- **Render** - Free tier available
- **Fly.io** - Global edge deployment
- **Google Cloud Run** - Serverless containers

## Design Decisions

### Why Claude + Voyage AI?

| Component | Choice | Rationale |
|-----------|--------|-----------|
| **Embeddings** | Voyage AI | Free tier (200M tokens), superior performance, lower cost |
| **Generation** | Claude | Superior reasoning, fewer hallucinations |

**Note**: Voyage AI's `voyage-3-large` outperforms OpenAI's `text-embedding-3-large` by an average of 9.74% across multiple domains ([source](https://blog.voyageai.com/2025/01/07/voyage-3-large/)).

This is intentional - embeddings create vector representations while the LLM does reasoning. They're independent.

### Chunking Strategy

- **Character-based**: ~1500-2000 chars (~400-500 tokens)
- **Overlap**: ~200 chars for context preservation
- **Rationale**: Avoids tiktoken overhead; 1 token ≈ 4 chars is sufficient

### RAG Guardrails

The system prompt includes:
1. Answer ONLY from provided context
2. Acknowledge when information isn't found
3. Handle conflicting sources explicitly
4. Ignore instructions in documents (prompt injection defense)

### Caching Strategy

- **Embeddings**: 24h TTL (queries are stable)
- **Responses**: 1h TTL (allow document updates)
- **Key format**: `hash(question + sorted(doc_ids))`

## Project Structure

```
backend/
├── main.py                      # FastAPI app entry point
├── config.py                    # Settings & configuration
├── responses.py                 # Response codes, formats & helpers
├── router.py                    # Main router aggregator
├── utils.py                     # Helper utilities
│
├── llm/                         # LLM abstraction layer
│   ├── __init__.py              # exports get_model()
│   ├── base.py                  # BaseLLM abstract class
│   ├── claude.py                # Claude implementation (current)
│   └── prompts.py               # System prompts (RAG, general, summarization)
│
├── chat/                        # Chat domain
│   ├── handlers/
│   │   ├── send_message.py      # POST /chat/stream (streaming, with non-streaming fallback)
│   │   ├── get_chat_history.py  # GET /chat/history
│   │   └── clear_chat_history.py # DELETE /chat/history
│   └── models/
│       └── message.py           # Firestore: sessions/{id}/messages
│
├── documents/                   # Documents domain
│   └── handlers/
│       ├── upload_document.py   # POST /documents/upload
│       ├── list_documents.py    # GET /documents
│       └── delete_document.py   # DELETE /documents/{doc_id}
│
├── sessions/                    # Sessions domain
│   ├── helpers.py               # get_or_create_session, set_session_cookie
│   ├── handlers/
│   │   ├── list_sessions.py     # GET /sessions
│   │   ├── create_session.py    # POST /sessions
│   │   ├── switch_session.py    # PUT /sessions/{id}/switch
│   │   └── delete_session.py    # DELETE /sessions/{id}
│   └── models/
│       └── session.py           # Firestore: sessions collection
│
├── health/                      # Health check domain
│   └── handlers/
│       └── health_check.py      # GET /health
│
├── services/                    # Core business logic (see below)
│   ├── document.py
│   ├── chunker.py
│   ├── embeddings.py
│   ├── vector_store.py
│   ├── query_analyzer.py
│   └── rag.py
│
├── db/                          # Database layer
│   └── firestore.py             # Firestore singleton service
│
├── cache/                       # Cache layer
│   └── redis.py                 # Redis singleton service
│
├── scripts/
│   └── reset_qdrant.py          # Reset Qdrant collection
│
└── tests/
    ├── test_chunker.py
    └── test_document.py

frontend/
├── src/
│   ├── components/              # React components
│   ├── hooks/                   # Custom hooks
│   └── styles/                  # Tailwind CSS
└── package.json
```

### Why `services/` exists

The `services/` folder contains **domain-agnostic business logic** that doesn't belong to any specific API domain:

| Service | Purpose | Why not in a domain folder? |
|---------|---------|----------------------------|
| `document.py` | Parse PDF/DOCX/TXT files | Used by documents, but parsing logic is independent |
| `chunker.py` | Split text into overlapping chunks | Pure text processing, no API/DB dependencies |
| `embeddings.py` | Generate vectors via Voyage AI | External API wrapper, used by RAG |
| `vector_store.py` | Qdrant CRUD operations | Database layer for vectors |
| `query_analyzer.py` | Decompose complex queries | LLM-powered analysis, used by RAG |
| `rag.py` | Orchestrate retrieval + generation | Composes all services together |

**Rule of thumb**: If it's reusable across domains or has no HTTP context, it belongs in `services/`.

### LLM Module

Currently uses **Claude only** via direct Anthropic SDK. The `llm/` module provides a simple abstraction:

```python
from llm import get_model

model = get_model("claude-sonnet-4-20250514")  # or any Claude model
response = await model.generate(prompt, system_prompt)
stream = model.stream(prompt, system_prompt)
```

**Future**: If multiple providers are needed (OpenAI, Gemini, etc.), we'd integrate LangChain here. For now, direct SDK is simpler and has fewer dependencies.

## Testing

### Running Tests

```bash
cd backend

# Install test dependencies
uv pip install pytest pytest-asyncio pytest-cov

# Run all tests
pytest -v

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_chunker.py -v
```

### Test Coverage

| Test File | What it covers |
|-----------|----------------|
| `test_chunker.py` | Text chunking: empty text, short text, long text, overlap, sentence/paragraph breaks, page estimation |
| `test_document.py` | Document parsing: filename sanitization, file validation, content hashing, TXT parsing, error handling |

**Note**: Tests for `chunker.py` and `document.py` don't require external services (no API keys needed). They test pure business logic.

## Future Improvements

### Storage & Scalability
- [ ] **S3 file storage** - Store original documents in S3 for persistence, re-processing, and audit trail
  ```
  Current:  Upload → Parse → Chunk → Embed → Qdrant (file discarded)
  Future:   Upload → S3 → Parse → Chunk → Embed → Qdrant (s3_url in metadata)
  ```
- [ ] **Multi-tenant support** - User authentication with document isolation per user/org

### Retrieval Quality
- [ ] Cross-encoder reranking for better retrieval precision
- [ ] Hybrid search (BM25 + vector) for keyword + semantic matching
- [ ] Adaptive chunking based on document structure

### Document Processing
- [ ] Table extraction with tabula-py
- [ ] OCR for scanned PDFs with pytesseract
- [ ] Image/chart understanding with vision models

### Security & Operations
- [ ] User authentication with JWT
- [ ] Rate limiting with slowapi
- [ ] Usage analytics and monitoring
- [ ] Document versioning

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

---
