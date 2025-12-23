"""DELETE /sessions/{target_session_id} - Delete a session."""

import logging
import uuid

from fastapi import Cookie
from fastapi.responses import JSONResponse

from apps.sessions.helpers import set_session_cookie
from db import get_firestore_service
from responses import ResponseCode, error_response, success_response

logger = logging.getLogger(__name__)


async def delete_session(
    target_session_id: str,
    session_id: str | None = Cookie(default=None),
) -> JSONResponse:
    """Delete a session and all its messages."""
    if not session_id:
        session_id = str(uuid.uuid4())

    request_id = str(uuid.uuid4())[:8]
    logger.info("[%s] Delete session request: %s", request_id, target_session_id)

    firestore_service = get_firestore_service()

    try:
        success = await firestore_service.delete_session(target_session_id)
        if not success:
            return error_response(
                ResponseCode.INTERNAL_ERROR, "Failed to delete session", request_id
            )

        resp = success_response(
            ResponseCode.SUCCESS, {"deleted_session_id": target_session_id}, request_id
        )

        # If deleting current session, create a new one
        if target_session_id == session_id:
            new_session_id = str(uuid.uuid4())
            await firestore_service.create_session(new_session_id)
            resp = set_session_cookie(resp, new_session_id)

        return resp

    except Exception as e:
        logger.exception("[%s] Failed to delete session", request_id)
        return error_response(
            ResponseCode.INTERNAL_ERROR, f"Failed to delete session: {e}", request_id
        )
