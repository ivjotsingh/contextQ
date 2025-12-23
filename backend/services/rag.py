"""RAG (Retrieval-Augmented Generation) service.

Orchestrates the RAG pipeline:
1. Analyze query to determine if RAG is needed
2. Embed user question
3. Retrieve relevant chunks from vector store (filtered by session_id)
4. Generate answer with Claude (streaming)

Note: This service is stateless and does not manage chat history persistence.
Chat history should be managed by the application layer (chat handlers).
"""

import asyncio
import logging
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from typing import Any

from anthropic import APITimeoutError

from config import get_settings
from llm.prompts import (
    ASSISTANT_SYSTEM_PROMPT,
    DOCUMENT_QA_SYSTEM_PROMPT,
    QUERY_ANALYSIS_PROMPT,
    QUERY_ANALYSIS_SCHEMA,
    QUERY_ANALYSIS_SYSTEM_PROMPT,
)
from llm.service import LLMError
from llm.service import LLMService as LLMClient
from services.embeddings import EmbeddingService
from services.vector_store import RetrievedChunk, VectorStoreService

logger = logging.getLogger(__name__)


# Re-export for backwards compatibility
__all__ = ["RAGService", "RAGError", "LLMError"]


class RAGError(Exception):
    """Raised when RAG pipeline fails."""

    pass


# --- Query Analyzer (internal to RAG) ---


@dataclass
class _QueryAnalysis:
    """Result of query analysis."""

    needs_decomposition: bool
    sub_queries: list[str]
    reasoning: str | None = None
    skip_rag: bool = False


class _QueryAnalyzer:
    """Internal query analyzer for decomposing complex queries."""

    def __init__(self, llm_client: LLMClient, settings: Any) -> None:
        self.llm_client = llm_client
        self.max_sub_queries = settings.max_sub_queries
        self.timeout = settings.query_analysis_timeout
        self.model = settings.query_analysis_model

    async def analyze(
        self,
        question: str,
        doc_count: int,
        document_names: list[str] | None = None,
    ) -> _QueryAnalysis:
        """Analyze a query and determine if decomposition is needed.

        Uses Claude's tool_use feature for guaranteed structured JSON output,
        eliminating brittle string parsing.
        """
        # Fast path: single document doesn't need decomposition
        if doc_count <= 1:
            logger.debug("Skipping decomposition: single document")
            return _QueryAnalysis(
                needs_decomposition=False,
                sub_queries=[],
                reasoning="Single document - no cross-document reasoning needed",
            )

        # Fast path: very short questions are likely simple lookups
        if len(question.split()) < 4:
            logger.debug("Skipping decomposition: short question")
            return _QueryAnalysis(
                needs_decomposition=False,
                sub_queries=[],
                reasoning="Short question - likely simple lookup",
            )

        try:
            doc_names_str = (
                ", ".join(document_names)
                if document_names
                else f"{doc_count} documents"
            )

            # Build prompt from template
            prompt = QUERY_ANALYSIS_PROMPT.format(
                doc_names_str=doc_names_str,
                question=question,
                max_sub_queries=self.max_sub_queries,
            )

            # Use tool_use for guaranteed structured output
            result = await asyncio.wait_for(
                self.llm_client.generate_with_tool(
                    prompt=prompt,
                    system=QUERY_ANALYSIS_SYSTEM_PROMPT,
                    tool_name="analyze_query",
                    tool_schema=QUERY_ANALYSIS_SCHEMA,
                    model=self.model,
                    temperature=0,
                    max_tokens=500,
                ),
                timeout=self.timeout,
            )

            # Result is guaranteed to match schema - no JSON parsing needed!
            skip_rag = result.get("skip_rag", False)
            needs_decomposition = result.get("needs_decomposition", False)
            sub_queries = result.get("sub_queries", [])
            reasoning = result.get("reasoning", "")

            if skip_rag:
                logger.info(
                    "Query classified as general (skip RAG): %s",
                    reasoning[:100] if reasoning else "",
                )
                return _QueryAnalysis(
                    needs_decomposition=False,
                    sub_queries=[],
                    reasoning=reasoning,
                    skip_rag=True,
                )

            # Validate and sanitize sub-queries
            if len(sub_queries) > self.max_sub_queries:
                logger.warning(
                    "Truncating sub-queries from %d to %d",
                    len(sub_queries),
                    self.max_sub_queries,
                )
                sub_queries = sub_queries[: self.max_sub_queries]

            sub_queries = [
                sq.strip()[:500]
                for sq in sub_queries
                if isinstance(sq, str) and sq.strip()
            ]

            if needs_decomposition and not sub_queries:
                logger.warning(
                    "Decomposition requested but no valid sub-queries, falling back"
                )
                needs_decomposition = False

            if needs_decomposition and sub_queries:
                logger.info(
                    "Query decomposition triggered: %d sub-queries generated",
                    len(sub_queries),
                )
                for i, sq in enumerate(sub_queries, 1):
                    logger.debug("  Sub-query %d: %s", i, sq)
            else:
                logger.debug(
                    "Query decomposition skipped: %s",
                    reasoning[:100] if reasoning else "standard retrieval",
                )

            return _QueryAnalysis(
                needs_decomposition=needs_decomposition,
                sub_queries=sub_queries,
                reasoning=reasoning,
            )

        except TimeoutError:
            logger.warning(
                "Query analysis timed out after %.1fs, using standard retrieval",
                self.timeout,
            )
            return _QueryAnalysis(
                needs_decomposition=False,
                sub_queries=[],
                reasoning="Analysis timed out",
            )

        except APITimeoutError as e:
            logger.warning("Anthropic API timeout: %s", e)
            return _QueryAnalysis(
                needs_decomposition=False,
                sub_queries=[],
                reasoning="API timeout",
            )

        except Exception as e:
            logger.warning(
                "Query analysis failed, falling back to standard retrieval: %s", e
            )
            return _QueryAnalysis(
                needs_decomposition=False,
                sub_queries=[],
                reasoning=f"Analysis error: {e}",
            )


# --- RAG Service ---


class RAGService:
    """Service for RAG-based document Q&A.

    This service orchestrates the full RAG pipeline including query analysis,
    retrieval, and generation. Only streaming responses are supported.
    """

    def __init__(
        self,
        embedding_service: EmbeddingService,
        vector_store: VectorStoreService,
    ) -> None:
        """Initialize RAG service.

        Args:
            embedding_service: Service for generating embeddings.
            vector_store: Service for vector similarity search.
        """
        self.settings = get_settings()
        self.embedding_service = embedding_service
        self.vector_store = vector_store

        self._llm_client = LLMClient(self.settings)
        self._query_analyzer = _QueryAnalyzer(self._llm_client, self.settings)

    async def query_stream(
        self,
        question: str,
        session_id: str,
        chat_history: str = "",
        doc_ids: list[str] | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Process a RAG query with streaming response.

        Args:
            question: User's question.
            session_id: Session identifier.
            chat_history: Formatted chat history context string.
            doc_ids: Optional list of document IDs to search.

        Yields:
            Stream chunks with types: 'sources', 'content', 'done', 'error'.
            The 'done' chunk includes 'full_answer' and 'sources' for persistence.

        Raises:
            ValueError: If question or session_id is empty.
            RAGError: If the pipeline fails critically.
        """
        # Step 1: Validate input
        question = self._validate_input(question, session_id)

        try:
            # Step 2: Prepare documents and analyze query
            doc_ids, doc_names, analysis = await self._prepare_query(
                question, session_id, doc_ids
            )

            # Step 3: Handle general questions (skip RAG)
            if analysis.skip_rag:
                logger.info("Streaming: Skipping RAG for general question")
                async for chunk in self._handle_general_question(
                    question, chat_history
                ):
                    yield chunk
                return

            # Step 4: Handle no documents case
            if not doc_ids:
                yield {
                    "type": "content",
                    "content": "No documents have been uploaded yet. Please upload some documents first.",
                }
                yield {"type": "done"}
                return

            # Step 5: Retrieve and filter chunks
            relevant_chunks = await self._retrieve_and_filter(
                question, analysis, session_id, doc_ids
            )

            # Step 6: Handle no relevant chunks
            if relevant_chunks is None:
                yield {
                    "type": "content",
                    "content": "I couldn't find any relevant information in the uploaded documents for your question.",
                }
                yield {"type": "done"}
                return

            # Step 7: Stream RAG response
            async for chunk in self._stream_rag_response(
                question, relevant_chunks, chat_history
            ):
                yield chunk

        except (ValueError, RAGError, LLMError):
            raise
        except Exception as e:
            logger.error("Streaming RAG query failed: %s", e)
            raise RAGError(f"RAG pipeline failed: {e}") from e

    def _validate_input(self, question: str, session_id: str) -> str:
        """Validate and clean input parameters.

        Returns:
            Cleaned question string.

        Raises:
            ValueError: If inputs are invalid.
        """
        if not question or not question.strip():
            raise ValueError("Question cannot be empty")
        if not session_id:
            raise ValueError("Session ID is required")
        return question.strip()

    async def _prepare_query(
        self,
        question: str,
        session_id: str,
        doc_ids: list[str] | None,
    ) -> tuple[list[str], list[str], _QueryAnalysis]:
        """Prepare query by getting documents and analyzing the question.

        Returns:
            Tuple of (doc_ids, doc_names, analysis).
        """
        # Get document IDs from Qdrant if not provided
        if doc_ids is None:
            docs = await self.vector_store.get_session_documents(session_id)
            doc_ids = [d.doc_id for d in docs]

        doc_names = (
            await self._get_document_names(session_id, doc_ids) if doc_ids else []
        )

        # Analyze query to determine strategy
        analysis = await self._query_analyzer.analyze(
            question=question,
            doc_count=len(doc_ids) if doc_ids else 0,
            document_names=doc_names,
        )

        return doc_ids, doc_names, analysis

    async def _retrieve_and_filter(
        self,
        question: str,
        analysis: _QueryAnalysis,
        session_id: str,
        doc_ids: list[str],
    ) -> list[RetrievedChunk] | None:
        """Retrieve chunks and filter by relevance score.

        Returns:
            List of relevant chunks, or None if no chunks pass threshold.
        """
        # Retrieve relevant chunks
        chunks = await self._retrieve_chunks(question, analysis, session_id, doc_ids)

        if not chunks:
            return None

        # Filter by relevance score
        min_score = self.settings.min_relevance_score
        relevant_chunks = [c for c in chunks if c.score >= min_score]

        # Log retrieval quality metrics
        self._log_retrieval_metrics(chunks, relevant_chunks, min_score)

        if not relevant_chunks:
            return None

        logger.info(
            "Streaming: Filtered chunks: %d -> %d (threshold %.2f)",
            len(chunks),
            len(relevant_chunks),
            min_score,
        )

        return relevant_chunks

    def _log_retrieval_metrics(
        self,
        all_chunks: list[RetrievedChunk],
        relevant_chunks: list[RetrievedChunk],
        threshold: float,
    ) -> None:
        """Log metrics about retrieval quality."""
        if all_chunks:
            scores = [c.score for c in all_chunks]
            logger.info(
                "Retrieval metrics: total=%d, relevant=%d (threshold=%.2f), "
                "score_range=[%.3f-%.3f], mean=%.3f",
                len(all_chunks),
                len(relevant_chunks),
                threshold,
                min(scores),
                max(scores),
                sum(scores) / len(scores),
            )

        if not relevant_chunks:
            logger.warning(
                "All %d chunks filtered out (below %.2f threshold) - consider lowering threshold",
                len(all_chunks),
                threshold,
            )

    async def _stream_rag_response(
        self,
        question: str,
        chunks: list[RetrievedChunk],
        chat_history: str = "",
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Stream the RAG response with sources.

        Args:
            question: User's question.
            chunks: Retrieved chunks to use as context.
            chat_history: Formatted chat history context.

        Yields:
            Stream chunks with types: 'sources', 'content', 'done'.
        """
        # Build context and sources
        context = self._build_context(chunks)
        sources = self._chunks_to_source_dicts(chunks)

        # Yield sources first
        yield {"type": "sources", "sources": sources}

        # Stream LLM response
        answer_parts: list[str] = []  # Use list for O(n) instead of O(n²) string concat
        prompt = self._build_rag_prompt(question, context, chat_history)

        async for text_chunk in self._llm_client.stream(
            user_message=prompt,
            system_prompt=DOCUMENT_QA_SYSTEM_PROMPT,
        ):
            answer_parts.append(text_chunk)
            yield {"type": "content", "content": text_chunk}

        # Return full answer for handler to persist
        full_answer = "".join(answer_parts)
        yield {"type": "done", "full_answer": full_answer, "sources": sources}

    async def _handle_general_question(
        self,
        question: str,
        chat_history: str = "",
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Handle a general question that doesn't need RAG.

        Args:
            question: User's question.
            chat_history: Formatted chat history context.

        Yields:
            Stream chunks with types: 'sources', 'content', 'done'.
        """
        yield {"type": "sources", "sources": []}

        answer_parts: list[str] = []
        prompt = self._build_general_prompt(question, chat_history)

        async for text_chunk in self._llm_client.stream(
            user_message=prompt,
            system_prompt=ASSISTANT_SYSTEM_PROMPT,
            temperature=0.7,
        ):
            answer_parts.append(text_chunk)
            yield {"type": "content", "content": text_chunk}

        # Return full answer for handler to persist
        full_answer = "".join(answer_parts)
        yield {"type": "done", "full_answer": full_answer, "sources": []}

    def _build_rag_prompt(
        self,
        question: str,
        context: str,
        chat_history: str = "",
    ) -> str:
        """Build prompt for RAG-based answer generation."""
        history_section = (
            f"CONVERSATION HISTORY:\n{chat_history}\n\n" if chat_history else ""
        )
        return f"""{history_section}Based on the following document excerpts, please answer the question.

DOCUMENT CONTEXT:
{context}

QUESTION: {question}

Please provide a clear, accurate answer based only on the information in the documents above."""

    def _build_general_prompt(self, question: str, chat_history: str = "") -> str:
        """Build prompt for general (non-RAG) questions."""
        history_section = (
            f"CONVERSATION HISTORY:\n{chat_history}\n\n" if chat_history else ""
        )
        return f"{history_section}User question: {question}"

    async def _retrieve_chunks(
        self,
        question: str,
        analysis: _QueryAnalysis,
        session_id: str,
        doc_ids: list[str],
    ) -> list[RetrievedChunk]:
        """Retrieve chunks using standard or decomposed retrieval."""
        if analysis.needs_decomposition and analysis.sub_queries:
            logger.info(
                "Using query decomposition with %d sub-queries",
                len(analysis.sub_queries),
            )
            return await self._retrieve_with_decomposition(
                question, analysis.sub_queries, session_id, doc_ids
            )
        else:
            query_embedding = await self.embedding_service.embed_text(question)
            return await self.vector_store.search(
                query_embedding=query_embedding,
                session_id=session_id,
                doc_ids=doc_ids,
            )

    async def _get_document_names(
        self,
        session_id: str,
        doc_ids: list[str],
    ) -> list[str]:
        """Get document filenames for the given doc IDs."""
        try:
            docs = await self.vector_store.get_session_documents(session_id)
            doc_id_set = set(doc_ids)
            return [d.filename for d in docs if d.doc_id in doc_id_set]
        except Exception as e:
            # Non-critical: log and continue without names
            logger.warning("Failed to get document names: %s", e)
            return []

    async def _retrieve_with_decomposition(
        self,
        original_question: str,
        sub_queries: list[str],
        session_id: str,
        doc_ids: list[str],
    ) -> list[RetrievedChunk]:
        """Retrieve chunks using query decomposition."""
        all_chunks: list[RetrievedChunk] = []
        seen_chunk_ids: set[str] = set()
        top_k_per_query = self.settings.decomposition_top_k

        # Embed all queries at once for efficiency
        queries_to_embed = [original_question] + sub_queries
        embeddings = await self.embedding_service.embed_texts(queries_to_embed)

        for i, (query, embedding) in enumerate(
            zip(queries_to_embed, embeddings, strict=False)
        ):
            query_type = "original" if i == 0 else f"sub-query {i}"
            logger.debug("Retrieving for %s: %s", query_type, query[:50])

            chunks = await self.vector_store.search(
                query_embedding=embedding,
                session_id=session_id,
                doc_ids=doc_ids,
                top_k=top_k_per_query,
            )

            for chunk in chunks:
                chunk_id = f"{chunk.doc_id}_{chunk.chunk_index}"
                if chunk_id not in seen_chunk_ids:
                    seen_chunk_ids.add(chunk_id)
                    all_chunks.append(chunk)

        # Sort by score and limit
        all_chunks.sort(key=lambda x: x.score, reverse=True)
        max_total = self.settings.retrieval_top_k * 2
        logger.info(
            "Decomposition retrieved %d unique chunks (limited to %d)",
            len(all_chunks),
            max_total,
        )
        return all_chunks[:max_total]

    def _build_context(self, chunks: list[RetrievedChunk]) -> str:
        """Build context string from retrieved chunks."""
        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            source_info = f"[Source {i}: {chunk.filename}"
            if chunk.page_number:
                source_info += f", page {chunk.page_number}"
            source_info += "]"
            context_parts.append(f"{source_info}\n{chunk.text}")
        return "\n\n---\n\n".join(context_parts)

    def _chunks_to_source_dicts(
        self,
        chunks: list[RetrievedChunk],
    ) -> list[dict[str, Any]]:
        """Convert chunks to source passage dicts for API response."""
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
