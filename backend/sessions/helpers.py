"""Session cookie utilities."""

import uuid

from fastapi import Cookie
from fastapi.responses import JSONResponse

from config import get_settings


def set_session_cookie(response: JSONResponse, session_id: str) -> JSONResponse:
    """Set session cookie on response."""
    settings = get_settings()
    response.set_cookie(
        key="session_id",
        value=session_id,
        max_age=settings.session_ttl_hours * 3600,
        httponly=True,
        samesite="lax",
        secure=False,  # Set True in production with HTTPS
    )
    return response


def get_or_create_session(session_id: str | None = Cookie(default=None)) -> str:
    """Get existing session ID from cookie or create new one."""
    if session_id:
        return session_id
    return str(uuid.uuid4())

