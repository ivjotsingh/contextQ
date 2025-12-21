"""GET /sessions - List all chat sessions."""

import logging
import uuid

from fastapi import Cookie, HTTPException
from pydantic import BaseModel, Field

from db import get_firestore_service
from responses import ResponseCode, create_error_response

logger = logging.getLogger(__name__)


# --- Response Schemas ---


class SessionMetadata(BaseModel):
    """Metadata for a chat session."""

    id: str = Field(..., description="Session ID")
    title: str = Field(default="New Chat", description="Session title")
    last_activity: str | None = Field(None, description="ISO timestamp of last activity")
    message_count: int = Field(default=0, description="Number of messages in session")


class SessionListResponse(BaseModel):
    """Response for listing sessions."""

    sessions: list[SessionMetadata]
    current_session_id: str = Field(..., description="The current active session ID")


# --- Handler ---


async def list_sessions(
    session_id: str | None = Cookie(default=None),
) -> SessionListResponse:
    """List all chat sessions."""
    if not session_id:
        session_id = str(uuid.uuid4())

    firestore_service = get_firestore_service()

    try:
        sessions = await firestore_service.get_sessions(limit=20)
        session_list = [
            SessionMetadata(
                id=s["id"],
                title=s.get("title", "New Chat"),
                last_activity=s.get("last_activity"),
                message_count=s.get("message_count", 0),
            )
            for s in sessions
        ]
        return SessionListResponse(sessions=session_list, current_session_id=session_id)

    except Exception as e:
        logger.exception("Failed to list sessions")
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                ResponseCode.INTERNAL_ERROR, f"Failed to list sessions: {e}"
            ),
        )

