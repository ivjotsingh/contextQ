"""PUT /sessions/{target_session_id}/switch - Switch to a different session."""

import uuid

from fastapi.responses import JSONResponse

from apps.sessions.helpers import set_session_cookie
from responses import ResponseCode, success_dict


async def switch_session(target_session_id: str) -> JSONResponse:
    """Switch to a different session."""
    request_id = str(uuid.uuid4())[:8]
    resp = JSONResponse(
        content=success_dict(
            ResponseCode.SUCCESS, {"session_id": target_session_id}, request_id
        ),
        status_code=200,
    )
    return set_session_cookie(resp, target_session_id)
