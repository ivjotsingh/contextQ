"""RAG (Retrieval-Augmented Generation) service.

Pure retrieval service that handles:
1. Embed search query
2. Retrieve relevant chunks from vector store
3. Filter and build context

This service does NOT handle:
- LLM generation (handled by caller/handler)
- Query analysis (handled by caller)
- Chat history persistence (handled by caller)
"""

import logging
from dataclasses import dataclass
from typing import Any

from config import get_settings
from services.embeddings import EmbeddingService
from services.vector_store import RetrievedChunk, VectorStoreService

logger = logging.getLogger(__name__)


__all__ = ["RAGService", "RetrievalResult"]


@dataclass
class RetrievalResult:
    """Result of retrieval operation."""

    chunks: list[RetrievedChunk]
    context: str
    sources: list[dict[str, Any]]
    has_relevant_content: bool


class RAGService:
    """Pure retrieval service for RAG pipeline.

    Use retrieve() to:
    1. Embed the search query
    2. Search for relevant chunks
    3. Filter and build context

    LLM generation is handled separately by the caller.
    """

    def __init__(
        self,
        embedding_service: EmbeddingService,
        vector_store: VectorStoreService,
    ) -> None:
        """Initialize RAG service."""
        self.settings = get_settings()
        self.embedding_service = embedding_service
        self.vector_store = vector_store

    async def get_session_documents(self, session_id: str):
        """Get documents for a session (passthrough to vector store)."""
        return await self.vector_store.get_session_documents(session_id)

    async def retrieve(
        self,
        expanded_query: str,
        session_id: str,
        doc_ids: list[str] | None = None,
    ) -> RetrievalResult:
        """Retrieve relevant chunks for a search query.

        Args:
            expanded_query: Optimized query for vector search (from query analysis).
            session_id: Session identifier.
            doc_ids: Document IDs to search.

        Returns:
            RetrievalResult with chunks, context, sources, and relevance flag.
        """
        if not expanded_query or not expanded_query.strip():
            raise ValueError("Search query cannot be empty")
        if not session_id:
            raise ValueError("Session ID is required")

        expanded_query = expanded_query.strip()

        # 1. Embed and search
        query_embedding = await self.embedding_service.embed_text(expanded_query)
        chunks = await self.vector_store.search(
            query_embedding=query_embedding,
            session_id=session_id,
            doc_ids=doc_ids or [],
        )

        # 2. No chunks found
        if not chunks:
            return RetrievalResult(
                chunks=[],
                context="",
                sources=[],
                has_relevant_content=False,
            )

        # 3. Filter by relevance
        min_score = self.settings.min_relevance_score
        relevant_chunks = [c for c in chunks if c.score >= min_score]

        self._log_retrieval_metrics(expanded_query, chunks, relevant_chunks, min_score)

        if not relevant_chunks:
            return RetrievalResult(
                chunks=[],
                context="",
                sources=[],
                has_relevant_content=False,
            )

        # 4. Build context and sources
        context = self._build_context(relevant_chunks)
        sources = self._chunks_to_source_dicts(relevant_chunks)

        return RetrievalResult(
            chunks=relevant_chunks,
            context=context,
            sources=sources,
            has_relevant_content=True,
        )

    def build_rag_prompt(
        self,
        message: str,
        context: str,
        chat_history: str = "",
        expanded_query: str | None = None,
    ) -> str:
        """Build RAG prompt for LLM.

        Args:
            message: Original user message.
            context: Document context from retrieval.
            chat_history: Formatted chat history.
            expanded_query: Rewritten search query (shown if different from message).

        Returns:
            Complete prompt for LLM.
        """
        from llm.prompts import DOCUMENT_QA_USER_PROMPT

        history = f"CONVERSATION HISTORY:\n{chat_history}\n\n" if chat_history else ""

        # If expanded_query differs from message, show the interpretation
        interpretation = ""
        if expanded_query and expanded_query.strip().lower() != message.strip().lower():
            interpretation = f"\nINTERPRETED AS: {expanded_query}\n"

        return DOCUMENT_QA_USER_PROMPT.format(
            history=history,
            context=context,
            message=message,
            interpretation=interpretation,
        )

    def _log_retrieval_metrics(
        self,
        expanded_query: str,
        all_chunks: list[RetrievedChunk],
        relevant_chunks: list[RetrievedChunk],
        threshold: float,
    ) -> None:
        """Log retrieval quality metrics."""
        if all_chunks:
            scores = [c.score for c in all_chunks]
            logger.info(
                "Retrieval for '%s': total=%d, relevant=%d (threshold=%.2f), scores=[%.3f-%.3f]",
                expanded_query[:50],
                len(all_chunks),
                len(relevant_chunks),
                threshold,
                min(scores),
                max(scores),
            )

    def _build_context(self, chunks: list[RetrievedChunk]) -> str:
        """Build context string from chunks."""
        parts = []
        for i, chunk in enumerate(chunks, 1):
            source = f"[Source {i}: {chunk.filename}"
            if chunk.page_number:
                source += f", page {chunk.page_number}"
            source += "]"
            parts.append(f"{source}\n{chunk.text}")
        return "\n\n---\n\n".join(parts)

    def _chunks_to_source_dicts(
        self,
        chunks: list[RetrievedChunk],
    ) -> list[dict[str, Any]]:
        """Convert chunks to source dicts for API response."""
        return [
            {
                "text": c.text[:500] + "..." if len(c.text) > 500 else c.text,
                "filename": c.filename,
                "page_number": c.page_number,
                "chunk_index": c.chunk_index,
                "relevance_score": round(c.score, 4),
            }
            for c in chunks
        ]
