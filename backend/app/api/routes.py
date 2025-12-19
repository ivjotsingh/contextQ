"""API routes for ContextQ.

Endpoints:
- POST /api/upload - Upload and process documents
- POST /api/chat - Ask questions about documents
- GET /api/documents - List uploaded documents
- DELETE /api/documents/{doc_id} - Delete a document
- GET /api/health - Health check
"""

import logging
import os
import tempfile
import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import (
    APIRouter,
    Cookie,
    Depends,
    File,
    HTTPException,
    Request,
    UploadFile,
)
from fastapi.responses import JSONResponse, StreamingResponse

from app.api.schemas import (
    ChatRequest,
    ChatResponse,
    DocumentListResponse,
    DocumentMetadata,
    DocumentUploadResponse,
    HealthResponse,
    ServiceStatus,
)
from app.config import get_settings
from app.responses import (
    ResponseCode,
    create_error_response,
    create_success_response,
    get_http_status,
)
from app.services.cache import CacheService
from app.services.chunker import ChunkerService
from app.services.document import (
    DocumentParseError,
    DocumentService,
    EmptyDocumentError,
    FileTooLargeError,
    UnsupportedFileTypeError,
)
from app.services.embeddings import EmbeddingError, EmbeddingService
from app.services.rag import LLMError, RAGError, RAGService
from app.services.vector_store import VectorStoreError, VectorStoreService

logger = logging.getLogger(__name__)

router = APIRouter()

# =============================================================================
# Dependency Injection
# =============================================================================


def get_document_service() -> DocumentService:
    """Get document service instance."""
    return DocumentService()


def get_chunker_service() -> ChunkerService:
    """Get chunker service instance."""
    return ChunkerService()


def get_embedding_service() -> EmbeddingService:
    """Get embedding service instance."""
    return EmbeddingService()


def get_vector_store() -> VectorStoreService:
    """Get vector store instance."""
    return VectorStoreService()


def get_cache_service() -> CacheService:
    """Get cache service instance."""
    return CacheService()


def get_rag_service(
    embedding_service: EmbeddingService = Depends(get_embedding_service),
    vector_store: VectorStoreService = Depends(get_vector_store),
    cache_service: CacheService = Depends(get_cache_service),
) -> RAGService:
    """Get RAG service instance with dependencies."""
    return RAGService(embedding_service, vector_store, cache_service)


async def get_or_create_session(
    request: Request,
    session_id: Annotated[str | None, Cookie()] = None,
) -> str:
    """Get existing session ID or create new one.

    Session ID is stored in httpOnly cookie.
    """
    if session_id:
        return session_id
    return str(uuid.uuid4())


# =============================================================================
# Health Check
# =============================================================================


@router.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check(
    vector_store: VectorStoreService = Depends(get_vector_store),
    cache_service: CacheService = Depends(get_cache_service),
) -> HealthResponse:
    """Check health of all services.

    Returns overall status and individual service statuses.
    """
    settings = get_settings()
    services: list[ServiceStatus] = []

    # Check Qdrant
    qdrant_health = await vector_store.health_check()
    services.append(
        ServiceStatus(
            name="qdrant",
            status=qdrant_health["status"],
            latency_ms=qdrant_health.get("latency_ms"),
            error=qdrant_health.get("error"),
        )
    )

    # Check Redis
    redis_health = await cache_service.health_check()
    services.append(
        ServiceStatus(
            name="redis",
            status=redis_health["status"],
            latency_ms=redis_health.get("latency_ms"),
            error=redis_health.get("error"),
        )
    )

    # Determine overall status
    statuses = [s.status for s in services]
    if all(s == "healthy" for s in statuses):
        overall_status = "healthy"
    elif any(s == "unhealthy" for s in statuses):
        overall_status = "unhealthy"
    else:
        overall_status = "degraded"

    return HealthResponse(
        status=overall_status,
        version="0.1.0",
        environment=settings.environment,
        services=services,
        timestamp=datetime.now(UTC),
    )


# =============================================================================
# Document Upload
# =============================================================================


@router.post("/upload", tags=["Documents"])
async def upload_document(
    file: UploadFile = File(...),
    session_id: str = Depends(get_or_create_session),
    document_service: DocumentService = Depends(get_document_service),
    chunker_service: ChunkerService = Depends(get_chunker_service),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
    vector_store: VectorStoreService = Depends(get_vector_store),
    cache_service: CacheService = Depends(get_cache_service),
) -> JSONResponse:
    """Upload and process a document.

    Accepts PDF, DOCX, and TXT files.
    Parses, chunks, embeds, and stores the document for RAG queries.
    """
    request_id = str(uuid.uuid4())[:8]
    logger.info(
        "[%s] Upload request: %s (%s bytes)",
        request_id,
        file.filename,
        file.size,
    )

    try:
        # Validate file
        settings = get_settings()
        file_ext = document_service.validate_file(
            filename=file.filename or "unknown",
            file_size=file.size or 0,
            content_type=file.content_type,
        )

        # Save to temp file
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=file_ext
        ) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_path = temp_file.name

        try:
            # Parse document
            parse_result = await document_service.parse_file(
                file_path=temp_path,
                filename=file.filename or "document",
            )

            # Check for duplicate
            existing_doc_id = await vector_store.check_hash_exists(
                content_hash=parse_result["content_hash"],
                session_id=session_id,
            )

            if existing_doc_id:
                logger.info("[%s] Document already exists: %s", request_id, existing_doc_id)
                response = create_success_response(
                    code=ResponseCode.DUPLICATE_DOCUMENT,
                    data={"doc_id": existing_doc_id, "message": "Document already processed"},
                    request_id=request_id,
                )
                json_response = JSONResponse(content=response, status_code=200)
                json_response.set_cookie(
                    key="session_id",
                    value=session_id,
                    httponly=True,
                    max_age=settings.session_ttl,
                    samesite="lax",
                )
                return json_response

            # Chunk text
            chunks = chunker_service.chunk_text(
                text=parse_result["text"],
                page_count=parse_result.get("page_count"),
            )

            # Check chunk limit
            if len(chunks) > settings.max_chunks_per_doc:
                raise FileTooLargeError(
                    f"Document produces {len(chunks)} chunks, "
                    f"exceeding limit of {settings.max_chunks_per_doc}"
                )

            # Generate embeddings
            chunk_texts = [c.text for c in chunks]
            embeddings = await embedding_service.embed_texts(chunk_texts)

            # Prepare chunk data
            chunk_data = [
                {
                    "text": c.text,
                    "chunk_index": c.chunk_index,
                    "page_number": c.page_number,
                }
                for c in chunks
            ]

            # Store in vector database
            doc_id = str(uuid.uuid4())
            upload_timestamp = datetime.now(UTC).isoformat()

            metadata = {
                "filename": parse_result["metadata"]["filename"],
                "document_type": parse_result["metadata"]["document_type"],
                "content_hash": parse_result["content_hash"],
                "upload_timestamp": upload_timestamp,
            }

            await vector_store.upsert_chunks(
                chunks=chunk_data,
                embeddings=embeddings,
                doc_id=doc_id,
                session_id=session_id,
                metadata=metadata,
            )

            # Add to session
            await cache_service.add_document_to_session(session_id, doc_id)

            # Build response
            doc_metadata = DocumentMetadata(
                doc_id=doc_id,
                filename=metadata["filename"],
                document_type=metadata["document_type"],
                total_chunks=len(chunks),
                upload_timestamp=datetime.fromisoformat(upload_timestamp),
                content_hash=parse_result["content_hash"],
                page_count=parse_result.get("page_count"),
            )

            response = create_success_response(
                code=ResponseCode.DOCUMENT_UPLOADED,
                data=doc_metadata.model_dump(mode="json"),
                request_id=request_id,
            )

            logger.info(
                "[%s] Document processed: %s (%d chunks)",
                request_id,
                doc_id,
                len(chunks),
            )

            json_response = JSONResponse(
                content=response,
                status_code=get_http_status(ResponseCode.DOCUMENT_UPLOADED),
            )
            json_response.set_cookie(
                key="session_id",
                value=session_id,
                httponly=True,
                max_age=settings.session_ttl,
                samesite="lax",
            )
            return json_response

        finally:
            # Clean up temp file
            os.unlink(temp_path)

    except UnsupportedFileTypeError as e:
        logger.warning("[%s] Unsupported file type: %s", request_id, e)
        response = create_error_response(
            code=ResponseCode.UNSUPPORTED_FILE_TYPE,
            custom_message=str(e),
            request_id=request_id,
        )
        return JSONResponse(
            content=response,
            status_code=get_http_status(ResponseCode.UNSUPPORTED_FILE_TYPE),
        )

    except FileTooLargeError as e:
        logger.warning("[%s] File too large: %s", request_id, e)
        response = create_error_response(
            code=ResponseCode.FILE_TOO_LARGE,
            custom_message=str(e),
            request_id=request_id,
        )
        return JSONResponse(
            content=response,
            status_code=get_http_status(ResponseCode.FILE_TOO_LARGE),
        )

    except EmptyDocumentError as e:
        logger.warning("[%s] Empty document: %s", request_id, e)
        response = create_error_response(
            code=ResponseCode.EMPTY_DOCUMENT,
            custom_message=str(e),
            request_id=request_id,
        )
        return JSONResponse(
            content=response,
            status_code=get_http_status(ResponseCode.EMPTY_DOCUMENT),
        )

    except DocumentParseError as e:
        logger.error("[%s] Parse error: %s", request_id, e)
        response = create_error_response(
            code=ResponseCode.CORRUPTED_FILE,
            custom_message=str(e),
            request_id=request_id,
        )
        return JSONResponse(
            content=response,
            status_code=get_http_status(ResponseCode.CORRUPTED_FILE),
        )

    except EmbeddingError as e:
        logger.error("[%s] Embedding error: %s", request_id, e)
        response = create_error_response(
            code=ResponseCode.EMBEDDING_FAILED,
            custom_message=str(e),
            request_id=request_id,
        )
        return JSONResponse(
            content=response,
            status_code=get_http_status(ResponseCode.EMBEDDING_FAILED),
        )

    except VectorStoreError as e:
        logger.error("[%s] Vector store error: %s", request_id, e)
        response = create_error_response(
            code=ResponseCode.VECTOR_STORE_ERROR,
            custom_message=str(e),
            request_id=request_id,
        )
        return JSONResponse(
            content=response,
            status_code=get_http_status(ResponseCode.VECTOR_STORE_ERROR),
        )

    except Exception as e:
        logger.exception("[%s] Unexpected error during upload", request_id)
        response = create_error_response(
            code=ResponseCode.INTERNAL_ERROR,
            error_details={"exception": str(e)},
            request_id=request_id,
        )
        return JSONResponse(
            content=response,
            status_code=get_http_status(ResponseCode.INTERNAL_ERROR),
        )


# =============================================================================
# Chat
# =============================================================================


@router.post("/chat", response_model=ChatResponse, tags=["Chat"])
async def chat(
    request: ChatRequest,
    session_id: str = Depends(get_or_create_session),
    rag_service: RAGService = Depends(get_rag_service),
) -> ChatResponse:
    """Ask a question about uploaded documents.

    Returns answer with source passages.
    """
    request_id = str(uuid.uuid4())[:8]
    logger.info("[%s] Chat request: %s", request_id, request.question[:100])

    try:
        response = await rag_service.query(
            question=request.question,
            session_id=session_id,
            doc_ids=request.doc_ids,
        )
        return response

    except LLMError as e:
        logger.error("[%s] LLM error: %s", request_id, e)
        raise HTTPException(
            status_code=get_http_status(ResponseCode.LLM_ERROR),
            detail=create_error_response(
                code=ResponseCode.LLM_ERROR,
                custom_message=str(e),
                request_id=request_id,
            ),
        )

    except RAGError as e:
        logger.error("[%s] RAG error: %s", request_id, e)
        raise HTTPException(
            status_code=get_http_status(ResponseCode.INTERNAL_ERROR),
            detail=create_error_response(
                code=ResponseCode.INTERNAL_ERROR,
                custom_message=str(e),
                request_id=request_id,
            ),
        )


@router.post("/chat/stream", tags=["Chat"])
async def chat_stream(
    request: ChatRequest,
    session_id: str = Depends(get_or_create_session),
    rag_service: RAGService = Depends(get_rag_service),
) -> StreamingResponse:
    """Ask a question with streaming response.

    Returns Server-Sent Events stream.
    """
    request_id = str(uuid.uuid4())[:8]
    logger.info("[%s] Streaming chat request: %s", request_id, request.question[:100])

    async def event_generator():
        """Generate SSE events from RAG stream."""
        import json

        async for chunk in rag_service.query_stream(
            question=request.question,
            session_id=session_id,
            doc_ids=request.doc_ids,
        ):
            yield f"data: {json.dumps(chunk)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Request-ID": request_id,
        },
    )


# =============================================================================
# Document Management
# =============================================================================


@router.get("/documents", response_model=DocumentListResponse, tags=["Documents"])
async def list_documents(
    session_id: str = Depends(get_or_create_session),
    vector_store: VectorStoreService = Depends(get_vector_store),
) -> DocumentListResponse:
    """List all documents for the current session."""
    try:
        docs = await vector_store.get_session_documents(session_id)

        documents = [
            DocumentMetadata(
                doc_id=d["doc_id"],
                filename=d["filename"],
                document_type=d["document_type"],
                total_chunks=d["total_chunks"],
                upload_timestamp=datetime.fromisoformat(d["upload_timestamp"])
                if d.get("upload_timestamp")
                else datetime.now(UTC),
                content_hash=d.get("content_hash", ""),
                page_count=None,
            )
            for d in docs
        ]

        return DocumentListResponse(
            documents=documents,
            total_count=len(documents),
        )

    except VectorStoreError as e:
        raise HTTPException(
            status_code=get_http_status(ResponseCode.VECTOR_STORE_ERROR),
            detail=create_error_response(
                code=ResponseCode.VECTOR_STORE_ERROR,
                custom_message=str(e),
            ),
        )


@router.delete("/documents/{doc_id}", tags=["Documents"])
async def delete_document(
    doc_id: str,
    session_id: str = Depends(get_or_create_session),
    vector_store: VectorStoreService = Depends(get_vector_store),
    cache_service: CacheService = Depends(get_cache_service),
) -> JSONResponse:
    """Delete a document and its vectors.

    Also invalidates related cache entries.
    """
    request_id = str(uuid.uuid4())[:8]
    logger.info("[%s] Delete request for doc: %s", request_id, doc_id)

    try:
        # Delete from vector store
        deleted_count = await vector_store.delete_document(doc_id, session_id)

        if deleted_count == 0:
            response = create_error_response(
                code=ResponseCode.DOCUMENT_NOT_FOUND,
                request_id=request_id,
            )
            return JSONResponse(
                content=response,
                status_code=get_http_status(ResponseCode.DOCUMENT_NOT_FOUND),
            )

        # Invalidate cache
        await cache_service.invalidate_document_cache(doc_id, session_id)

        # Remove from session
        await cache_service.remove_document_from_session(session_id, doc_id)

        response = create_success_response(
            code=ResponseCode.DOCUMENT_DELETED,
            data={"doc_id": doc_id, "chunks_deleted": deleted_count},
            request_id=request_id,
        )
        return JSONResponse(content=response, status_code=200)

    except VectorStoreError as e:
        logger.error("[%s] Delete error: %s", request_id, e)
        response = create_error_response(
            code=ResponseCode.VECTOR_STORE_ERROR,
            custom_message=str(e),
            request_id=request_id,
        )
        return JSONResponse(
            content=response,
            status_code=get_http_status(ResponseCode.VECTOR_STORE_ERROR),
        )

