"""Services module for cross-cutting business logic.

Contains domain-agnostic services used across multiple modules:
- Embedding generation (Voyage AI)
- Vector store operations (Qdrant)
- RAG orchestration
- Document parsing and chunking

Note: Service instances are now managed via dependencies.py using FastAPI DI.
Note: LLM client is in llm/ module, not here.
Note: Chat history management is in apps/chat/, not here.
"""

from services.chunker import Chunker, TextChunk
from services.document import (
    DocumentParseError,
    DocumentParser,
    EmptyDocumentError,
    FileTooLargeError,
    UnsupportedFileTypeError,
)
from services.embeddings import EmbeddingError, EmbeddingService
from services.rag import RAGService, RetrievalResult
from services.vector_store import (
    DocumentInfo,
    RetrievedChunk,
    VectorStoreError,
    VectorStoreService,
)

__all__ = [
    # Core services
    "EmbeddingError",
    "EmbeddingService",
    "RAGService",
    "RetrievalResult",
    "VectorStoreError",
    "VectorStoreService",
    # Document services
    "Chunker",
    "TextChunk",
    "DocumentParser",
    "DocumentParseError",
    "EmptyDocumentError",
    "FileTooLargeError",
    "UnsupportedFileTypeError",
    # Types
    "DocumentInfo",
    "RetrievedChunk",
]
