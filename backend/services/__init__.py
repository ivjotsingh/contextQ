"""Services module for cross-cutting business logic.

Contains domain-agnostic services used across multiple modules:
- Embedding generation (Voyage AI)
- Vector store operations (Qdrant)
- RAG orchestration
- Document parsing and chunking
- LLM client
- Chat history management

Note: Service instances are now managed via dependencies.py using FastAPI DI.
"""

from services.chat_history import ChatHistoryManager
from services.chunker import Chunker, TextChunk
from services.document import (
    DocumentParseError,
    DocumentParser,
    EmptyDocumentError,
    FileTooLargeError,
    UnsupportedFileTypeError,
)
from services.embeddings import EmbeddingError, EmbeddingService
from services.llm import LLMClient, LLMError
from services.rag import RAGError, RAGService
from services.types import DocumentInfo, RetrievedChunk
from services.vector_store import VectorStoreError, VectorStoreService

__all__ = [
    # Core services
    "EmbeddingError",
    "EmbeddingService",
    "LLMClient",
    "LLMError",
    "RAGError",
    "RAGService",
    "VectorStoreError",
    "VectorStoreService",
    "ChatHistoryManager",
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
