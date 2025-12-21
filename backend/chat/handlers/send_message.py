"""POST /chat - Send message and get streaming response."""

import json
import logging
import uuid

from fastapi import Cookie
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from services import get_rag_service

logger = logging.getLogger(__name__)


# --- Request/Response Schemas (API-specific) ---


class ChatRequest(BaseModel):
    """Request body for chat endpoint."""

    question: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Natural language question about the documents",
    )
    doc_ids: list[str] | None = Field(
        None,
        description="Optional: specific document IDs to search. If None, searches all.",
    )


# --- Handler ---


async def send_message(
    request: ChatRequest,
    session_id: str | None = Cookie(default=None),
) -> StreamingResponse:
    """Send a message and get streaming response.

    Returns Server-Sent Events (SSE) stream with chunks:
    - type: "sources" - Retrieved source passages
    - type: "content" - Answer text chunk
    - type: "done" - Stream complete
    - type: "error" - Error occurred
    """
    # Create session if not exists
    if not session_id:
        session_id = str(uuid.uuid4())

    request_id = str(uuid.uuid4())[:8]
    logger.info("[%s] Chat request: %s", request_id, request.question[:100])

    rag_service = get_rag_service()

    async def event_generator():
        async for chunk in rag_service.query_stream(
            request.question, session_id, request.doc_ids
        ):
            yield f"data: {json.dumps(chunk)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Request-ID": request_id,
        },
    )
