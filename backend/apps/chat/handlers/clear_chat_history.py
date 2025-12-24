"""DELETE /chat/history - Clear chat history for a chat."""

import logging
import uuid

from fastapi import Query
from fastapi.responses import JSONResponse

from db import get_firestore_service
from responses import ResponseCode, error_response, success_response

logger = logging.getLogger(__name__)


async def clear_chat_history(
    chat_id: str = Query(..., description="Chat ID to clear"),
) -> JSONResponse:
    """Clear chat history for a specific chat."""
    request_id = str(uuid.uuid4())[:8]
    logger.info("[%s] Clear chat history for chat: %s", request_id, chat_id)

    firestore_service = get_firestore_service()

    try:
        deleted_count = await firestore_service.clear_history(chat_id)
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
