"""Pydantic schemas for API request/response models."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# =============================================================================
# Document Schemas
# =============================================================================


class DocumentMetadata(BaseModel):
    """Metadata for an uploaded document."""

    doc_id: str = Field(..., description="Unique document identifier")
    filename: str = Field(..., description="Original filename")
    document_type: str = Field(..., description="File type (pdf, docx, txt)")
    total_chunks: int = Field(..., description="Number of chunks created")
    upload_timestamp: datetime = Field(..., description="When document was uploaded")
    content_hash: str = Field(..., description="SHA256 hash of content")
    page_count: int | None = Field(None, description="Number of pages (if applicable)")


class DocumentUploadResponse(BaseModel):
    """Response after successful document upload."""

    document: DocumentMetadata
    message: str = Field(default="Document uploaded and processed successfully")


class DocumentListResponse(BaseModel):
    """Response for listing documents."""

    documents: list[DocumentMetadata]
    total_count: int


# =============================================================================
# Chat Schemas
# =============================================================================


class ChatRequest(BaseModel):
    """Request body for chat endpoint."""

    question: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Natural language question about the documents",
    )
    doc_ids: list[str] | None = Field(
        None,
        description="Optional: specific document IDs to search. If None, searches all.",
    )


class SourcePassage(BaseModel):
    """A source passage used to generate the answer."""

    text: str = Field(..., description="The passage text")
    filename: str = Field(..., description="Source document filename")
    page_number: int | None = Field(None, description="Page number if available")
    chunk_index: int = Field(..., description="Chunk index in document")
    relevance_score: float = Field(..., description="Similarity score (0-1)")


class ChatResponse(BaseModel):
    """Response from chat endpoint."""

    answer: str = Field(..., description="Generated answer based on documents")
    sources: list[SourcePassage] = Field(
        ..., description="Source passages used to generate answer"
    )
    cached: bool = Field(default=False, description="Whether response was from cache")


class ChatStreamChunk(BaseModel):
    """A chunk of streaming chat response."""

    type: str = Field(..., description="Chunk type: 'content', 'sources', 'done'")
    content: str | None = Field(None, description="Text content for 'content' type")
    sources: list[SourcePassage] | None = Field(
        None, description="Sources for 'sources' type"
    )


# =============================================================================
# Health Schemas
# =============================================================================


class ServiceStatus(BaseModel):
    """Status of an individual service."""

    name: str
    status: str = Field(..., description="healthy, degraded, or unhealthy")
    latency_ms: float | None = Field(None, description="Response time in ms")
    error: str | None = Field(None, description="Error message if unhealthy")


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Overall status: healthy, degraded, unhealthy")
    version: str = Field(..., description="Application version")
    environment: str = Field(..., description="Environment name")
    services: list[ServiceStatus] = Field(..., description="Individual service statuses")
    timestamp: datetime


# =============================================================================
# Session Schemas
# =============================================================================


class SessionInfo(BaseModel):
    """Information about the current session."""

    session_id: str
    document_count: int
    created_at: datetime
    expires_at: datetime


# =============================================================================
# Error Detail Schemas
# =============================================================================


class ValidationErrorDetail(BaseModel):
    """Details for validation errors."""

    field: str
    message: str
    value: Any | None = None


class FileErrorDetail(BaseModel):
    """Details for file-related errors."""

    filename: str
    file_size: int | None = None
    max_size: int | None = None
    file_type: str | None = None
    supported_types: list[str] | None = None

