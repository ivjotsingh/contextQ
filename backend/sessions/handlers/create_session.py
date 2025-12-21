"""POST /sessions - Create a new chat session."""

import logging
import uuid

from fastapi.responses import JSONResponse

from db import get_firestore_service
from responses import ResponseCode, create_success_response, error_response
from sessions.helpers import set_session_cookie

logger = logging.getLogger(__name__)


async def create_session() -> JSONResponse:
    """Create a new chat session."""
    request_id = str(uuid.uuid4())[:8]
    new_session_id = str(uuid.uuid4())

    firestore_service = get_firestore_service()

    try:
        session = await firestore_service.create_session(new_session_id)
        resp = JSONResponse(
            content=create_success_response(ResponseCode.SUCCESS, session, request_id),
            status_code=201,
        )
        return set_session_cookie(resp, new_session_id)

    except Exception as e:
        logger.exception("[%s] Failed to create session", request_id)
        return error_response(
            ResponseCode.INTERNAL_ERROR, f"Failed to create session: {e}", request_id
        )

