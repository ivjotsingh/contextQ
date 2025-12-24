"""DELETE /documents/{doc_id} - Delete a document."""

import logging
import uuid

from fastapi import Cookie
from fastapi.responses import JSONResponse

from dependencies import get_vector_store
from responses import ResponseCode, error_response, success_response
from services.vector_store import VectorStoreError

logger = logging.getLogger(__name__)


async def delete_document(
    doc_id: str,
    session_id: str | None = Cookie(default=None),
) -> JSONResponse:
    """Delete a document and its vectors."""
    if not session_id:
        session_id = str(uuid.uuid4())

    request_id = str(uuid.uuid4())[:8]
    logger.info("[%s] Delete request for doc: %s", request_id, doc_id)

    vector_store = get_vector_store()

    try:
        deleted_count = await vector_store.delete_document(doc_id, session_id)
        if deleted_count == 0:
            return error_response(
                ResponseCode.DOCUMENT_NOT_FOUND, request_id=request_id
            )

        return success_response(
            ResponseCode.DOCUMENT_DELETED,
            {"doc_id": doc_id, "chunks_deleted": deleted_count},
            request_id,
        )

    except VectorStoreError as e:
        logger.error("[%s] Delete error: %s", request_id, e)
        return error_response(ResponseCode.VECTOR_STORE_ERROR, str(e), request_id)

    except Exception as e:
        logger.exception("[%s] Unexpected error deleting document", request_id)
        return error_response(ResponseCode.INTERNAL_ERROR, str(e), request_id)
