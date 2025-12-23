"""POST /chat - Send message and get streaming response."""

import json
import logging
import uuid

from fastapi import Cookie, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from apps.chat.chat_history import ChatHistoryManager
from dependencies import get_chat_history_manager, get_rag_service
from services import RAGService

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
    rag_service: RAGService = Depends(get_rag_service),
    chat_history_mgr: ChatHistoryManager = Depends(get_chat_history_manager),
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

    async def event_generator():
        try:
            # 1. Get chat history context
            chat_history = await chat_history_mgr.get_context(session_id)

            # 2. Save user message
            await chat_history_mgr.save_user_message(session_id, request.question)

            # 3. Stream RAG response
            full_answer = ""
            sources = []
            async for chunk in rag_service.query_stream(
                request.question, session_id, chat_history, request.doc_ids
            ):
                # Capture full answer and sources from done chunk
                if chunk.get("type") == "done":
                    full_answer = chunk.get("full_answer", "")
                    sources = chunk.get("sources", [])
                    # Don't yield the done chunk yet - save first
                else:
                    yield f"data: {json.dumps(chunk)}\n\n"

            # 4. Save assistant response
            await chat_history_mgr.save_assistant_message(
                session_id, full_answer, sources
            )
            await chat_history_mgr.maybe_generate_summary(session_id)

            # 5. Now yield the done chunk
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as e:
            logger.exception("[%s] Stream error", request_id)
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Request-ID": request_id,
        },
    )
