"""GET /chats - List all chats for the current session."""

import logging
import uuid

from fastapi import Cookie, HTTPException
from pydantic import BaseModel, Field

from db import get_firestore_service
from responses import ResponseCode, error_dict

logger = logging.getLogger(__name__)


# --- Response Schemas ---


class ChatMetadata(BaseModel):
    """Metadata for a chat."""

    id: str = Field(..., description="Chat ID")
    title: str = Field(default="New Chat", description="Chat title")
    last_activity: str | None = Field(
        None, description="ISO timestamp of last activity"
    )
    message_count: int = Field(default=0, description="Number of messages")


class ChatListResponse(BaseModel):
    """Response for listing chats."""

    chats: list[ChatMetadata]
    session_id: str = Field(..., description="The browser session ID")


# --- Handler ---


async def list_chats(
    session_id: str | None = Cookie(default=None),
) -> ChatListResponse:
    """List all chats for the current session (browser)."""
    if not session_id:
        session_id = str(uuid.uuid4())

    firestore_service = get_firestore_service()

    try:
        chats = await firestore_service.get_chats(session_id, limit=20)
        chat_list = [
            ChatMetadata(
                id=c["id"],
                title=c.get("title", "New Chat"),
                last_activity=c.get("last_activity"),
                message_count=c.get("message_count", 0),
            )
            for c in chats
        ]
        return ChatListResponse(chats=chat_list, session_id=session_id)

    except Exception as e:
        logger.exception("Failed to list chats")
        raise HTTPException(
            status_code=500,
            detail=error_dict(
                ResponseCode.INTERNAL_ERROR, f"Failed to list chats: {e}"
            ),
        )
