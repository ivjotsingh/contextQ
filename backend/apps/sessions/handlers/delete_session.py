"""DELETE /chats/{chat_id} - Delete a chat."""

import logging
import uuid

from fastapi.responses import JSONResponse

from db import get_firestore_service
from responses import ResponseCode, error_response, success_response

logger = logging.getLogger(__name__)


async def delete_chat(chat_id: str) -> JSONResponse:
    """Delete a chat and all its messages."""
    request_id = str(uuid.uuid4())[:8]
    logger.info("[%s] Delete chat request: %s", request_id, chat_id)

    firestore_service = get_firestore_service()

    try:
        success = await firestore_service.delete_chat(chat_id)
        if not success:
            return error_response(
                ResponseCode.INTERNAL_ERROR, "Failed to delete chat", request_id
            )

        return success_response(
            ResponseCode.SUCCESS, {"deleted_chat_id": chat_id}, request_id
        )

    except Exception as e:
        logger.exception("[%s] Failed to delete chat", request_id)
        return error_response(
            ResponseCode.INTERNAL_ERROR, f"Failed to delete chat: {e}", request_id
        )
