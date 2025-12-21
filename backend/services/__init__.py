"""Services module for cross-cutting business logic.

Contains domain-agnostic services used across multiple modules:
- Embedding generation (Voyage AI)
- Vector store operations (Qdrant)
- RAG orchestration
- Document parsing and chunking
- LLM client
- Chat history management
"""

from services.chat_history import ChatHistoryManager
from services.chunker import Chunker, TextChunk, get_chunker_service
from services.document import (
    DocumentParseError,
    DocumentParser,
    EmptyDocumentError,
    FileTooLargeError,
    UnsupportedFileTypeError,
    get_document_service,
)
from services.embeddings import EmbeddingError, EmbeddingService, get_embedding_service
from services.llm import LLMClient, LLMError
from services.rag import RAGError, RAGService, get_rag_service
from services.types import DocumentInfo, RetrievedChunk
from services.vector_store import VectorStoreError, VectorStoreService, get_vector_store

__all__ = [
    # Core services
    "EmbeddingError",
    "EmbeddingService",
    "get_embedding_service",
    "LLMClient",
    "LLMError",
    "RAGError",
    "RAGService",
    "get_rag_service",
    "VectorStoreError",
    "VectorStoreService",
    "get_vector_store",
    "ChatHistoryManager",
    # Document services
    "Chunker",
    "TextChunk",
    "get_chunker_service",
    "DocumentParser",
    "DocumentParseError",
    "EmptyDocumentError",
    "FileTooLargeError",
    "UnsupportedFileTypeError",
    "get_document_service",
    # Types
    "DocumentInfo",
    "RetrievedChunk",
]
