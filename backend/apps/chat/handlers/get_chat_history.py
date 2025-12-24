"""GET /chat/history - Get chat history for a chat."""

import logging

from fastapi import HTTPException, Query
from pydantic import BaseModel, Field

from db import get_firestore_service
from responses import ResponseCode, error_dict

logger = logging.getLogger(__name__)


# --- Response Schemas ---


class SourcePassage(BaseModel):
    """Source passage in API response."""

    text: str = Field(..., description="The passage text")
    filename: str = Field(..., description="Source document filename")
    page_number: int | None = Field(None, description="Page number if available")
    chunk_index: int = Field(..., description="Chunk index in document")
    relevance_score: float = Field(..., description="Similarity score (0-1)")


class ChatHistoryMessage(BaseModel):
    """A message in chat history response."""

    id: str = Field(..., description="Message ID")
    role: str = Field(..., description="Message role (user/assistant)")
    content: str = Field(..., description="Message content")
    timestamp: str = Field(..., description="ISO timestamp")
    sources: list[SourcePassage] | None = Field(
        None, description="Source passages for assistant messages"
    )


class ChatHistoryResponse(BaseModel):
    """Response for chat history endpoint."""

    messages: list[ChatHistoryMessage]
    total_count: int = Field(..., description="Total message count")
    has_more: bool = Field(default=False, description="Whether there are more messages")


# --- Handler ---


async def get_chat_history(
    chat_id: str = Query(..., description="Chat ID"),
    limit: int = Query(default=50, description="Max messages to return"),
) -> ChatHistoryResponse:
    """Get chat history for a specific chat."""
    firestore_service = get_firestore_service()

    try:
        messages = await firestore_service.get_messages(chat_id, limit=limit)
        total_count = await firestore_service.get_message_count(chat_id)

        history_messages = [
            ChatHistoryMessage(
                id=msg.get("id", ""),
                role=msg.get("role", ""),
                content=msg.get("content", ""),
                timestamp=msg.get("timestamp", ""),
                sources=[
                    SourcePassage(
                        text=s.get("text", ""),
                        filename=s.get("filename", ""),
                        page_number=s.get("page_number"),
                        chunk_index=s.get("chunk_index", 0),
                        relevance_score=s.get("relevance_score", 0.0),
                    )
                    for s in msg["sources"]
                ]
                if msg.get("sources")
                else None,
            )
            for msg in messages
        ]

        return ChatHistoryResponse(
            messages=history_messages,
            total_count=total_count,
            has_more=total_count > limit,
        )

    except Exception as e:
        logger.exception("Failed to get chat history")
        raise HTTPException(
            status_code=500,
            detail=error_dict(
                ResponseCode.INTERNAL_ERROR, f"Failed to retrieve chat history: {e}"
            ),
        )
