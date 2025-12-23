"""FastAPI dependency injection for services.

Replaces global singleton pattern with proper DI using Depends().
Services are cached with @lru_cache() to avoid recreation per request.
"""

from functools import lru_cache

from fastapi import Depends

from db import FirestoreService
from services.chunker import Chunker
from services.embeddings import EmbeddingService
from services.rag import RAGService
from services.vector_store import VectorStoreService

# --- Cached Singletons ---
# These are created once and reused across all requests


@lru_cache
def get_embedding_service() -> EmbeddingService:
    """Get cached embedding service (expensive - has API client)."""
    return EmbeddingService()


@lru_cache
def get_vector_store() -> VectorStoreService:
    """Get cached vector store service (expensive - has Qdrant client)."""
    return VectorStoreService()


@lru_cache
def get_firestore_service() -> FirestoreService:
    """Get cached Firestore service."""
    return FirestoreService()


# --- Lightweight Services (per-request is fine) ---


def get_chunker() -> Chunker:
    """Get chunker (stateless, cheap to create)."""
    return Chunker()


# --- Composed Services ---
# Use Depends() for proper FastAPI DI chaining


def get_rag_service(
    embedding_service: EmbeddingService = Depends(get_embedding_service),
    vector_store: VectorStoreService = Depends(get_vector_store),
    firestore_service: FirestoreService = Depends(get_firestore_service),
) -> RAGService:
    """Get RAG service with injected dependencies.

    FastAPI will automatically inject the cached dependencies.
    """
    return RAGService(
        embedding_service=embedding_service,
        vector_store=vector_store,
        firestore_service=firestore_service,
    )
