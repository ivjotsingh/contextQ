"""Pytest configuration and fixtures for ContextQ tests."""

import os
import sys
from unittest.mock import AsyncMock, MagicMock

import pytest

# Add app to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture
def mock_settings():
    """Mock application settings."""
    settings = MagicMock()
    settings.anthropic_api_key = "test-anthropic-key"
    settings.voyage_api_key = "test-voyage-key"
    settings.qdrant_url = "http://localhost:6333"
    settings.qdrant_api_key = "test-qdrant-key"
    settings.qdrant_collection = "test_documents"
    settings.redis_url = "redis://localhost:6379"
    settings.environment = "test"
    settings.debug = True
    settings.max_file_size_mb = 10
    settings.max_file_size_bytes = 10 * 1024 * 1024
    settings.max_chunks_per_doc = 500
    settings.chunk_size = 1500
    settings.chunk_overlap = 200
    settings.embedding_model = "text-embedding-3-small"
    settings.embedding_dimensions = 1536
    settings.llm_model = "claude-sonnet-4-20250514"
    settings.retrieval_top_k = 5
    settings.llm_temperature = 0.2
    settings.llm_max_tokens = 2048
    settings.embedding_cache_ttl = 86400
    settings.response_cache_ttl = 3600
    settings.session_ttl = 86400
    settings.embedding_batch_size = 64
    return settings


@pytest.fixture
def mock_embedding_service():
    """Mock embedding service."""
    service = AsyncMock()
    service.embed_text.return_value = [0.1] * 1536
    service.embed_texts.return_value = [[0.1] * 1536]
    return service


@pytest.fixture
def mock_vector_store():
    """Mock vector store service."""
    service = AsyncMock()
    service.initialize.return_value = None
    service.check_hash_exists.return_value = None
    service.upsert_chunks.return_value = 5
    service.search.return_value = [
        {
            "text": "Sample chunk text",
            "filename": "test.pdf",
            "page_number": 1,
            "chunk_index": 0,
            "doc_id": "test-doc-id",
            "score": 0.95,
        }
    ]
    service.delete_document.return_value = 5
    service.get_session_documents.return_value = []
    service.health_check.return_value = {"status": "healthy", "latency_ms": 10}
    return service


@pytest.fixture
def mock_cache_service():
    """Mock cache service."""
    service = AsyncMock()
    service.get_embedding.return_value = None
    service.set_embedding.return_value = True
    service.get_response.return_value = None
    service.set_response.return_value = True
    service.get_session_doc_ids.return_value = ["test-doc-id"]
    service.add_document_to_session.return_value = True
    service.remove_document_from_session.return_value = True
    service.invalidate_document_cache.return_value = 0
    service.health_check.return_value = {"status": "healthy", "latency_ms": 5}
    return service


@pytest.fixture
def sample_pdf_content():
    """Sample PDF text content for testing."""
    return """
    This is a sample document for testing the ContextQ application.
    
    Chapter 1: Introduction
    
    ContextQ is a RAG-powered document chat system that allows users to upload
    documents and ask questions about their content. The system uses vector
    embeddings to find relevant passages and generates answers using Claude.
    
    Chapter 2: Features
    
    Key features include:
    - Document upload (PDF, DOCX, TXT)
    - Natural language queries
    - Source attribution
    - Streaming responses
    
    Chapter 3: Architecture
    
    The system uses FastAPI for the backend, React for the frontend, Qdrant
    for vector storage, and Redis for caching.
    """


@pytest.fixture
def sample_chunks():
    """Sample text chunks for testing."""
    return [
        {
            "text": "This is chunk 1 about introduction.",
            "chunk_index": 0,
            "page_number": 1,
        },
        {
            "text": "This is chunk 2 about features.",
            "chunk_index": 1,
            "page_number": 1,
        },
        {
            "text": "This is chunk 3 about architecture.",
            "chunk_index": 2,
            "page_number": 2,
        },
    ]

