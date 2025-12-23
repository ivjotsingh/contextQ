"""Firestore document schemas for chat messages.

These represent the structure of documents stored in Firestore,
not API request/response schemas.
"""

from pydantic import BaseModel, Field


class SourceDocument(BaseModel):
    """Source passage stored with assistant messages in Firestore."""

    text: str = Field(..., description="The passage text")
    filename: str = Field(..., description="Source document filename")
    page_number: int | None = Field(None, description="Page number if available")
    chunk_index: int = Field(..., description="Chunk index in document")
    relevance_score: float = Field(..., description="Similarity score (0-1)")


class MessageDocument(BaseModel):
    """Chat message document stored in Firestore.

    Path: sessions/{session_id}/messages/{message_id}
    """

    id: str = Field(..., description="Message ID")
    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")
    timestamp: str = Field(..., description="ISO timestamp")
    sources: list[SourceDocument] | None = Field(
        None, description="Source passages (assistant messages only)"
    )
