"""Shared types and dataclasses for services.

Provides typed alternatives to dict[str, Any] for better type safety.
"""

from dataclasses import dataclass


@dataclass
class RetrievedChunk:
    """A chunk retrieved from vector search with relevance score."""

    text: str
    filename: str
    page_number: int | None
    chunk_index: int
    doc_id: str
    score: float


@dataclass
class DocumentInfo:
    """Document metadata from vector store."""

    doc_id: str
    filename: str
    document_type: str
    content_hash: str
    upload_timestamp: str
    total_chunks: int


@dataclass
class ParsedDocument:
    """Result of parsing a document file."""

    text: str
    page_count: int | None
    content_hash: str
    metadata: "DocumentMetadata"


@dataclass
class DocumentMetadata:
    """Metadata extracted from a parsed document."""

    filename: str
    document_type: str
    title: str = ""
    author: str = ""
    subject: str = ""
    creator: str = ""


@dataclass
class TextChunk:
    """A chunk of text with position metadata."""

    text: str
    chunk_index: int
    start_char: int
    end_char: int
    page_number: int | None = None

