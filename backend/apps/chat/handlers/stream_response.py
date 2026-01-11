"""POST /chat - Stream chat response.

Orchestrates the chat flow:
1. Get chat history context
2. Analyze query (skip RAG? decompose?)
3. Retrieve relevant context (RAGService)
4. Stream LLM response
5. Save to chat history
"""

import asyncio
import json
import logging
import uuid
from collections.abc import AsyncGenerator
from typing import Any

from anthropic import APITimeoutError
from fastapi import Cookie, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from apps.chat.chat_history import ChatHistoryManager
from config import get_settings
from dependencies import get_chat_history_manager, get_rag_service
from llm import LLMService
from llm.prompts import (
    ASSISTANT_SYSTEM_PROMPT,
    DOCUMENT_QA_SYSTEM_PROMPT,
    QUERY_ANALYSIS_PROMPT,
    QUERY_ANALYSIS_SCHEMA,
    QUERY_ANALYSIS_SYSTEM_PROMPT,
    QueryAnalysisResult,
)
from services import RAGService

logger = logging.getLogger(__name__)


# --- Request Schema ---


class ChatRequest(BaseModel):
    """Request body for chat endpoint."""

    message: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="User's message or question",
        alias="question",
    )
    chat_id: str = Field(
        ...,
        description="Chat ID for conversation history",
    )
    doc_ids: list[str] | None = Field(
        None,
        description="Optional: specific document IDs to search. If None, searches all.",
    )


# --- Query Analyzer (private to this handler) ---


class _QueryAnalyzer:
    """Analyzes queries to determine routing (RAG vs general)."""

    def __init__(self) -> None:
        settings = get_settings()
        self._llm = LLMService()
        self._max_sub_queries = settings.max_sub_queries
        self._timeout = settings.query_analysis_timeout
        self._model = settings.query_analysis_model

    async def analyze(
        self,
        message: str,
        chat_history: str = "",
        document_names: list[str] | None = None,
    ) -> QueryAnalysisResult:
        """Analyze query to determine routing."""
        # Fast path: very short = likely greeting
        words = message.split()
        if len(words) <= 2:
            lower = message.lower().strip()
            if lower in ("hi", "hello", "hey", "help", "?", "thanks", "thank you"):
                return QueryAnalysisResult(
                    skip_rag=True,
                    needs_decomposition=False,
                    sub_queries=[],
                    reasoning="Greeting detected",
                )

        # Use LLM for analysis
        try:
            chat_history_section = (
                f"Recent chat history:\n{chat_history}"
                if chat_history
                else "No prior chat history."
            )

            docs_section = ""
            if document_names:
                docs_list = "\n".join(f"- {name}" for name in document_names)
                docs_section = f"\n\nAvailable documents:\n{docs_list}"

            prompt = QUERY_ANALYSIS_PROMPT.format(
                question=message,
                chat_history_section=chat_history_section + docs_section,
                max_sub_queries=self._max_sub_queries,
            )

            result = await asyncio.wait_for(
                self._llm.generate_structured_output(
                    prompt=prompt,
                    system=QUERY_ANALYSIS_SYSTEM_PROMPT,
                    tool_name="analyze_query",
                    tool_schema=QUERY_ANALYSIS_SCHEMA,
                    model=self._model,
                    temperature=0,
                    max_tokens=500,
                ),
                timeout=self._timeout,
            )

            skip_rag = result.get("skip_rag", False)
            needs_decomposition = result.get("needs_decomposition", False)
            sub_queries = result.get("sub_queries", [])[: self._max_sub_queries]
            reasoning = result.get("reasoning", "")

            sub_queries = [
                sq.strip()[:500]
                for sq in sub_queries
                if isinstance(sq, str) and sq.strip()
            ]

            if needs_decomposition and not sub_queries:
                needs_decomposition = False

            return QueryAnalysisResult(
                skip_rag=skip_rag,
                needs_decomposition=needs_decomposition,
                sub_queries=sub_queries,
                reasoning=reasoning,
            )

        except (TimeoutError, APITimeoutError) as e:
            logger.warning("Query analysis timed out: %s", e)
            return QueryAnalysisResult(
                skip_rag=False,
                needs_decomposition=False,
                sub_queries=[],
                reasoning="Analysis timed out",
            )

        except Exception as e:
            logger.warning("Query analysis failed: %s", e)
            return QueryAnalysisResult(
                skip_rag=False,
                needs_decomposition=False,
                sub_queries=[],
                reasoning=f"Analysis error: {e}",
            )


# --- Response Generators ---


async def _stream_general_response(
    message: str,
    chat_history: str,
) -> AsyncGenerator[dict[str, Any], None]:
    """Stream a general (non-RAG) response."""
    llm = LLMService()

    yield {"type": "sources", "sources": []}

    history_section = (
        f"CONVERSATION HISTORY:\n{chat_history}\n\n" if chat_history else ""
    )
    prompt = f"{history_section}User message: {message}"

    answer_parts: list[str] = []
    async for chunk in llm.stream(prompt, ASSISTANT_SYSTEM_PROMPT, temperature=0.7):
        answer_parts.append(chunk)
        yield {"type": "content", "content": chunk}

    full_answer = "".join(answer_parts)
    yield {"type": "done", "full_answer": full_answer, "sources": []}


async def _stream_rag_response(
    message: str,
    session_id: str,
    chat_history: str,
    doc_ids: list[str],
    sub_queries: list[str] | None,
    rag_service: RAGService,
) -> AsyncGenerator[dict[str, Any], None]:
    """Stream a RAG response.

    1. Retrieve relevant chunks
    2. Stream sources
    3. Stream LLM response
    """
    llm = LLMService()

    # 1. Retrieve context
    retrieval = await rag_service.retrieve(
        message=message,
        session_id=session_id,
        doc_ids=doc_ids,
        sub_queries=sub_queries,
    )

    # 2. No relevant content found
    if not retrieval.has_relevant_content:
        yield {"type": "sources", "sources": []}
        no_content_msg = (
            "I couldn't find any relevant information in the uploaded documents."
        )
        yield {"type": "content", "content": no_content_msg}
        yield {"type": "done", "full_answer": no_content_msg, "sources": []}
        return

    # 3. Yield sources first (for UI)
    yield {"type": "sources", "sources": retrieval.sources}

    # 4. Build prompt and stream LLM response
    prompt = rag_service.build_rag_prompt(message, retrieval.context, chat_history)

    answer_parts: list[str] = []
    async for chunk in llm.stream(prompt, DOCUMENT_QA_SYSTEM_PROMPT):
        answer_parts.append(chunk)
        yield {"type": "content", "content": chunk}

    full_answer = "".join(answer_parts)
    yield {"type": "done", "full_answer": full_answer, "sources": retrieval.sources}


# --- Handler ---


async def stream_response(
    request: ChatRequest,
    session_id: str | None = Cookie(default=None),
    rag_service: RAGService = Depends(get_rag_service),
    chat_history_mgr: ChatHistoryManager = Depends(get_chat_history_manager),
) -> StreamingResponse:
    """Stream a chat response.

    Orchestrates:
    1. Prepare context and analyze query
    2. Route to appropriate response generator
    3. Stream response (LLM generation happens here)
    4. Save to chat history
    """
    if not session_id:
        session_id = str(uuid.uuid4())

    chat_id = request.chat_id
    request_id = str(uuid.uuid4())[:8]
    logger.info("[%s] Chat: %s", request_id, request.message[:100])

    # --- Prepare context ---
    chat_history = await chat_history_mgr.get_context(chat_id)
    await chat_history_mgr.save_user_message(chat_id, request.message)

    # --- Fetch documents early (needed for analysis) ---
    docs = await rag_service.get_session_documents(session_id)
    doc_ids = [d.doc_id for d in docs]
    doc_names = [d.filename for d in docs]

    # --- Fast path: Skip LLM analysis for simple greetings ---
    simple_greetings = {"hi", "hello", "hey", "help", "?", "thanks", "thank you"}
    message_lower = request.message.lower().strip()
    is_simple_greeting = (
        len(request.message.split()) <= 2 and message_lower in simple_greetings
    )

    if is_simple_greeting:
        analysis = QueryAnalysisResult(
            skip_rag=True,
            needs_decomposition=False,
            sub_queries=[],
            reasoning="Simple greeting (fast path)",
        )
        logger.debug("[%s] Fast path: greeting detected, skipping analysis", request_id)
    else:
        analyzer = _QueryAnalyzer()
        analysis = await analyzer.analyze(request.message, chat_history, doc_names)
        logger.info(
            "[%s] Query Analysis: skip_rag=%s, decompose=%s, reasoning=%s",
            request_id,
            analysis.skip_rag,
            analysis.needs_decomposition,
            analysis.reasoning,
        )
        if analysis.needs_decomposition and analysis.sub_queries:
            logger.info(
                "[%s] Decomposed into %d sub-queries: %s",
                request_id,
                len(analysis.sub_queries),
                analysis.sub_queries,
            )

    # --- SSE Generator ---
    async def generate_sse_events():
        try:
            full_answer = ""
            sources: list[dict[str, Any]] = []

            if analysis.skip_rag:
                # General response (no RAG)
                async for chunk in _stream_general_response(
                    request.message, chat_history
                ):
                    if chunk.get("type") == "done":
                        full_answer = chunk.get("full_answer", "")
                        sources = chunk.get("sources", [])
                    else:
                        yield f"data: {json.dumps(chunk)}\n\n"

            elif not doc_ids:
                # No documents uploaded
                no_docs_msg = "No documents have been uploaded yet. Please upload some documents first."
                yield f"data: {json.dumps({'type': 'sources', 'sources': []})}\n\n"
                yield f"data: {json.dumps({'type': 'content', 'content': no_docs_msg})}\n\n"
                full_answer = no_docs_msg

            else:
                # RAG response: retrieve context, then stream LLM
                async for chunk in _stream_rag_response(
                    message=request.message,
                    session_id=session_id,
                    chat_history=chat_history,
                    doc_ids=request.doc_ids or doc_ids,
                    sub_queries=analysis.sub_queries
                    if analysis.needs_decomposition
                    else None,
                    rag_service=rag_service,
                ):
                    if chunk.get("type") == "done":
                        full_answer = chunk.get("full_answer", "")
                        sources = chunk.get("sources", [])
                    else:
                        yield f"data: {json.dumps(chunk)}\n\n"

            # Save assistant response
            await chat_history_mgr.save_assistant_message(chat_id, full_answer, sources)
            await chat_history_mgr.maybe_generate_summary(chat_id)

            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as e:
            logger.exception("[%s] Stream error", request_id)
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"

    return StreamingResponse(
        generate_sse_events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Request-ID": request_id,
        },
    )
