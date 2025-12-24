"""POST /chats - Create a new chat."""

import logging
import uuid

from fastapi import Cookie
from fastapi.responses import JSONResponse

from apps.sessions.helpers import set_session_cookie
from db import get_firestore_service
from responses import ResponseCode, error_response, success_dict

logger = logging.getLogger(__name__)


async def create_chat(
    session_id: str | None = Cookie(default=None),
) -> JSONResponse:
    """Create a new chat for the current session (browser)."""
    if not session_id:
        session_id = str(uuid.uuid4())

    request_id = str(uuid.uuid4())[:8]
    chat_id = str(uuid.uuid4())

    firestore_service = get_firestore_service()

    try:
        chat = await firestore_service.create_chat(chat_id, session_id)
        resp = JSONResponse(
            content=success_dict(ResponseCode.SUCCESS, chat, request_id),
            status_code=201,
        )
        # Ensure session cookie is set
        return set_session_cookie(resp, session_id)

    except Exception as e:
        logger.exception("[%s] Failed to create chat", request_id)
        return error_response(
            ResponseCode.INTERNAL_ERROR, f"Failed to create chat: {e}", request_id
        )
