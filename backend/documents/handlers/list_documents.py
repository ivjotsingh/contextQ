"""GET /documents - List all documents for session."""

import logging
import uuid
from datetime import UTC, datetime

from fastapi import Cookie, HTTPException
from pydantic import BaseModel, Field

from responses import ResponseCode, create_error_response
from services import get_vector_store
from services.vector_store import VectorStoreError

logger = logging.getLogger(__name__)


# --- Response Schemas ---


class DocumentMetadata(BaseModel):
    """Metadata for a document."""

    doc_id: str = Field(..., description="Unique document identifier")
    filename: str = Field(..., description="Original filename")
    document_type: str = Field(..., description="File type (pdf, docx, txt)")
    total_chunks: int = Field(..., description="Number of chunks created")
    upload_timestamp: datetime = Field(..., description="When document was uploaded")
    content_hash: str = Field(..., description="SHA256 hash of content")
    page_count: int | None = Field(None, description="Number of pages (if applicable)")


class DocumentListResponse(BaseModel):
    """Response for listing documents."""

    documents: list[DocumentMetadata]
    total_count: int


# --- Handler ---


async def list_documents(
    session_id: str | None = Cookie(default=None),
) -> DocumentListResponse:
    """List all documents for the current session."""
    if not session_id:
        session_id = str(uuid.uuid4())

    vector_store = get_vector_store()

    try:
        docs = await vector_store.get_session_documents(session_id)
        documents = [
            DocumentMetadata(
                doc_id=d.doc_id,
                filename=d.filename,
                document_type=d.document_type,
                total_chunks=d.total_chunks,
                upload_timestamp=(
                    datetime.fromisoformat(d.upload_timestamp)
                    if d.upload_timestamp
                    else datetime.now(UTC)
                ),
                content_hash=d.content_hash or "",
                page_count=d.page_count,
            )
            for d in docs
        ]
        return DocumentListResponse(documents=documents, total_count=len(documents))

    except VectorStoreError as e:
        raise HTTPException(
            status_code=500,
            detail=create_error_response(ResponseCode.VECTOR_STORE_ERROR, str(e)),
        )

