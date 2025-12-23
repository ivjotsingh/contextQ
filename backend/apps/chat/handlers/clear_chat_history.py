"""DELETE /chat/history - Clear chat history for session."""

import logging
import uuid

from fastapi import Cookie
from fastapi.responses import JSONResponse

from db import get_firestore_service
from responses import ResponseCode, error_response, success_response

logger = logging.getLogger(__name__)


async def clear_chat_history(
    session_id: str | None = Cookie(default=None),
) -> JSONResponse:
    """Clear chat history for the current session."""
    if not session_id:
        session_id = str(uuid.uuid4())

    request_id = str(uuid.uuid4())[:8]
    logger.info(
        "[%s] Clear chat history request for session: %s", request_id, session_id
    )

    firestore_service = get_firestore_service()

    try:
        deleted_count = await firestore_service.clear_history(session_id)
        return success_response(
            ResponseCode.SUCCESS, {"messages_deleted": deleted_count}, request_id
        )
    except Exception as e:
        logger.exception("[%s] Failed to clear chat history", request_id)
        return error_response(
            ResponseCode.INTERNAL_ERROR,
            f"Failed to clear chat history: {e}",
            request_id,
        )
