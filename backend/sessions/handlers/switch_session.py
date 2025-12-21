"""PUT /sessions/{target_session_id}/switch - Switch to a different session."""

import uuid

from fastapi.responses import JSONResponse

from responses import ResponseCode, create_success_response
from sessions.helpers import set_session_cookie


async def switch_session(target_session_id: str) -> JSONResponse:
    """Switch to a different session."""
    request_id = str(uuid.uuid4())[:8]
    resp = JSONResponse(
        content=create_success_response(
            ResponseCode.SUCCESS, {"session_id": target_session_id}, request_id
        ),
        status_code=200,
    )
    return set_session_cookie(resp, target_session_id)

