"""RAG (Retrieval-Augmented Generation) service.

Pure retrieval service that handles:
1. Embed user question
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
    1. Embed the question
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
        message: str,
        session_id: str,
        doc_ids: list[str] | None = None,
        sub_queries: list[str] | None = None,
    ) -> RetrievalResult:
        """Retrieve relevant chunks for a question.

        Args:
            message: User's question.
            session_id: Session identifier.
            doc_ids: Document IDs to search.
            sub_queries: Optional sub-queries for decomposition.

        Returns:
            RetrievalResult with chunks, context, sources, and relevance flag.
        """
        if not message or not message.strip():
            raise ValueError("Message cannot be empty")
        if not session_id:
            raise ValueError("Session ID is required")

        message = message.strip()

        # 1. Retrieve chunks
        chunks = await self._retrieve_chunks(
            message, session_id, doc_ids or [], sub_queries
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

        self._log_retrieval_metrics(chunks, relevant_chunks, min_score)

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
    ) -> str:
        """Build RAG prompt for LLM.

        Args:
            message: User's question.
            context: Document context from retrieval.
            chat_history: Formatted chat history.

        Returns:
            Complete prompt for LLM.
        """
        history = f"CONVERSATION HISTORY:\n{chat_history}\n\n" if chat_history else ""
        return f"""{history}Based on the following document excerpts, please answer the question.

DOCUMENT CONTEXT:
{context}

QUESTION: {message}

Please provide a clear, accurate answer based only on the information in the documents above."""

    async def _retrieve_chunks(
        self,
        message: str,
        session_id: str,
        doc_ids: list[str],
        sub_queries: list[str] | None = None,
    ) -> list[RetrievedChunk]:
        """Retrieve chunks, optionally using decomposition."""
        if sub_queries:
            return await self._retrieve_with_decomposition(
                message, sub_queries, session_id, doc_ids
            )
        else:
            query_embedding = await self.embedding_service.embed_text(message)
            return await self.vector_store.search(
                query_embedding=query_embedding,
                session_id=session_id,
                doc_ids=doc_ids,
            )

    async def _retrieve_with_decomposition(
        self,
        original_message: str,
        sub_queries: list[str],
        session_id: str,
        doc_ids: list[str],
    ) -> list[RetrievedChunk]:
        """Retrieve chunks using query decomposition."""
        all_chunks: list[RetrievedChunk] = []
        seen_chunk_ids: set[str] = set()
        top_k = self.settings.decomposition_top_k

        # Embed all queries at once
        queries = [original_message] + sub_queries
        embeddings = await self.embedding_service.embed_texts(queries)

        for _query, embedding in zip(queries, embeddings, strict=False):
            chunks = await self.vector_store.search(
                query_embedding=embedding,
                session_id=session_id,
                doc_ids=doc_ids,
                top_k=top_k,
            )

            for chunk in chunks:
                chunk_id = f"{chunk.doc_id}_{chunk.chunk_index}"
                if chunk_id not in seen_chunk_ids:
                    seen_chunk_ids.add(chunk_id)
                    all_chunks.append(chunk)

        # Sort by score, limit results
        all_chunks.sort(key=lambda x: x.score, reverse=True)
        max_total = self.settings.retrieval_top_k * 2

        logger.info(
            "Decomposition: %d unique chunks (limited to %d)",
            len(all_chunks),
            max_total,
        )

        return all_chunks[:max_total]

    def _log_retrieval_metrics(
        self,
        all_chunks: list[RetrievedChunk],
        relevant_chunks: list[RetrievedChunk],
        threshold: float,
    ) -> None:
        """Log retrieval quality metrics."""
        if all_chunks:
            scores = [c.score for c in all_chunks]
            logger.info(
                "Retrieval: total=%d, relevant=%d (threshold=%.2f), scores=[%.3f-%.3f]",
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
