"""POST /documents/upload - Upload and process a document."""

import logging
import os
import tempfile
import uuid
from datetime import UTC, datetime

from fastapi import Cookie, File, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from config import get_settings
from responses import ResponseCode, error_response, success_response
from services import (
    get_chunker_service,
    get_document_service,
    get_embedding_service,
    get_vector_store,
)
from services.document import (
    DocumentParseError,
    EmptyDocumentError,
    FileTooLargeError,
    UnsupportedFileTypeError,
)
from services.embeddings import EmbeddingError
from services.vector_store import VectorStoreError
from sessions.helpers import set_session_cookie

logger = logging.getLogger(__name__)


# --- Response Schema ---


class DocumentMetadata(BaseModel):
    """Metadata for an uploaded document."""

    doc_id: str = Field(..., description="Unique document identifier")
    filename: str = Field(..., description="Original filename")
    document_type: str = Field(..., description="File type (pdf, docx, txt)")
    total_chunks: int = Field(..., description="Number of chunks created")
    upload_timestamp: datetime = Field(..., description="When document was uploaded")
    content_hash: str = Field(..., description="SHA256 hash of content")
    page_count: int | None = Field(None, description="Number of pages (if applicable)")


# --- Error mapping ---

UPLOAD_ERROR_MAP = {
    UnsupportedFileTypeError: ResponseCode.UNSUPPORTED_FILE_TYPE,
    FileTooLargeError: ResponseCode.FILE_TOO_LARGE,
    EmptyDocumentError: ResponseCode.EMPTY_DOCUMENT,
    DocumentParseError: ResponseCode.CORRUPTED_FILE,
    EmbeddingError: ResponseCode.EMBEDDING_FAILED,
    VectorStoreError: ResponseCode.VECTOR_STORE_ERROR,
}


# --- Handler ---


async def upload_document(
    file: UploadFile = File(...),
    session_id: str | None = Cookie(default=None),
) -> JSONResponse:
    """Upload and process a document (PDF, DOCX, TXT)."""
    if not session_id:
        session_id = str(uuid.uuid4())

    request_id = str(uuid.uuid4())[:8]
    logger.info("[%s] Upload request: %s (%s bytes)", request_id, file.filename, file.size)

    # Get services
    document_service = get_document_service()
    chunker_service = get_chunker_service()
    embedding_service = get_embedding_service()
    vector_store = get_vector_store()
    settings = get_settings()

    try:
        file_ext = document_service.validate_file(
            filename=file.filename or "unknown",
            file_size=file.size or 0,
            content_type=file.content_type,
        )

        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_path = temp_file.name

        try:
            parse_result = await document_service.parse_file(
                temp_path, file.filename or "document"
            )

            existing_doc_id = await vector_store.check_hash_exists(
                parse_result["content_hash"], session_id
            )
            if existing_doc_id:
                logger.info("[%s] Document already exists: %s", request_id, existing_doc_id)
                resp = success_response(
                    ResponseCode.DUPLICATE_DOCUMENT,
                    {"doc_id": existing_doc_id, "message": "Document already processed"},
                    request_id,
                )
                return set_session_cookie(resp, session_id)

            chunks = chunker_service.chunk_text(
                parse_result["text"], parse_result.get("page_count")
            )
            if len(chunks) > settings.max_chunks_per_doc:
                raise FileTooLargeError(
                    f"Document produces {len(chunks)} chunks, exceeding limit of {settings.max_chunks_per_doc}"
                )

            embeddings = await embedding_service.embed_texts([c.text for c in chunks])

            doc_id = str(uuid.uuid4())
            upload_timestamp = datetime.now(UTC).isoformat()
            metadata = {
                "filename": parse_result["metadata"]["filename"],
                "document_type": parse_result["metadata"]["document_type"],
                "content_hash": parse_result["content_hash"],
                "upload_timestamp": upload_timestamp,
            }

            await vector_store.upsert_chunks(
                chunks=[
                    {"text": c.text, "chunk_index": c.chunk_index, "page_number": c.page_number}
                    for c in chunks
                ],
                embeddings=embeddings,
                doc_id=doc_id,
                session_id=session_id,
                metadata=metadata,
            )

            doc_metadata = DocumentMetadata(
                doc_id=doc_id,
                filename=metadata["filename"],
                document_type=metadata["document_type"],
                total_chunks=len(chunks),
                upload_timestamp=datetime.fromisoformat(upload_timestamp),
                content_hash=parse_result["content_hash"],
                page_count=parse_result.get("page_count"),
            )

            logger.info(
                "[%s] Document processed: %s (%d chunks)", request_id, doc_id, len(chunks)
            )
            resp = success_response(
                ResponseCode.DOCUMENT_UPLOADED, doc_metadata.model_dump(mode="json"), request_id
            )
            return set_session_cookie(resp, session_id)

        finally:
            os.unlink(temp_path)

    except tuple(UPLOAD_ERROR_MAP.keys()) as e:
        code = UPLOAD_ERROR_MAP[type(e)]
        log_fn = logger.warning if code.value.startswith("1") else logger.error
        log_fn("[%s] %s: %s", request_id, type(e).__name__, e)
        return error_response(code, str(e), request_id)

    except Exception as e:
        logger.exception("[%s] Unexpected error during upload", request_id)
        return error_response(ResponseCode.INTERNAL_ERROR, str(e), request_id)
