"""Vector store service for Qdrant operations.

Handles:
- Collection management
- Vector upsert with metadata
- Similarity search with filtering
- Document deletion
"""

import logging
import time
from dataclasses import dataclass
from uuid import uuid4

from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models as qdrant_models

from config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class RetrievedChunk:
    """A chunk retrieved from vector search with relevance score."""

    text: str
    filename: str
    page_number: int | None
    chunk_index: int
    doc_id: str
    score: float


@dataclass
class DocumentInfo:
    """Document metadata from vector store."""

    doc_id: str
    filename: str
    document_type: str
    content_hash: str
    upload_timestamp: str
    total_chunks: int


class VectorStoreError(Exception):
    """Raised when vector store operations fail."""

    pass


class VectorStoreService:
    """Service for Qdrant vector database operations."""

    def __init__(self) -> None:
        """Initialize vector store with Qdrant client."""
        self.settings = get_settings()
        self.client = AsyncQdrantClient(
            url=self.settings.qdrant_url,
            api_key=self.settings.qdrant_api_key,
        )
        self.collection_name = self.settings.qdrant_collection
        self.vector_size = self.settings.embedding_dimensions
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize collection if it doesn't exist."""
        if self._initialized:
            return

        try:
            collections = await self.client.get_collections()
            collection_names = [c.name for c in collections.collections]

            if self.collection_name not in collection_names:
                logger.info("Creating Qdrant collection: %s", self.collection_name)
                await self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=qdrant_models.VectorParams(
                        size=self.vector_size,
                        distance=qdrant_models.Distance.COSINE,
                    ),
                )

                await self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name="session_id",
                    field_schema=qdrant_models.PayloadSchemaType.KEYWORD,
                )
                await self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name="doc_id",
                    field_schema=qdrant_models.PayloadSchemaType.KEYWORD,
                )
                await self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name="content_hash",
                    field_schema=qdrant_models.PayloadSchemaType.KEYWORD,
                )

                logger.info("Collection created with payload indexes")

            self._initialized = True

        except Exception as e:
            logger.error("Failed to initialize Qdrant collection: %s", e)
            raise VectorStoreError(f"Failed to initialize vector store: {e}") from e

    async def check_hash_exists(
        self,
        content_hash: str,
        session_id: str,
    ) -> str | None:
        """Check if a document with this content hash already exists.

        Args:
            content_hash: SHA256 hash of document content.
            session_id: Session identifier.

        Returns:
            Document ID if exists, None otherwise.

        Raises:
            VectorStoreError: If the check fails due to a database error.
        """
        if not content_hash or not session_id:
            raise ValueError("content_hash and session_id are required")

        try:
            await self.initialize()

            results = await self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=qdrant_models.Filter(
                    must=[
                        qdrant_models.FieldCondition(
                            key="session_id",
                            match=qdrant_models.MatchValue(value=session_id),
                        ),
                        qdrant_models.FieldCondition(
                            key="content_hash",
                            match=qdrant_models.MatchValue(value=content_hash),
                        ),
                    ]
                ),
                limit=1,
            )

            if results[0]:
                return results[0][0].payload.get("doc_id")
            return None

        except Exception as e:
            logger.error("Error checking hash existence: %s", e)
            raise VectorStoreError(f"Failed to check document hash: {e}") from e

    async def upsert_chunks(
        self,
        chunks: list[dict[str, object]],
        embeddings: list[list[float]],
        doc_id: str,
        session_id: str,
        metadata: dict[str, str],
    ) -> int:
        """Upsert document chunks with their embeddings.

        Args:
            chunks: List of chunk dicts with text, chunk_index, page_number.
            embeddings: List of embedding vectors.
            doc_id: Document identifier.
            session_id: Session identifier.
            metadata: Document metadata (filename, document_type, etc).

        Returns:
            Number of chunks upserted.

        Raises:
            ValueError: If chunks and embeddings have different lengths.
            VectorStoreError: If upsert fails.
        """
        await self.initialize()

        if len(chunks) != len(embeddings):
            raise ValueError(
                f"Chunks ({len(chunks)}) and embeddings ({len(embeddings)}) must have same length"
            )

        if not chunks:
            return 0

        try:
            start_time = time.time()

            points = []
            for i, (chunk, embedding) in enumerate(
                zip(chunks, embeddings, strict=False)
            ):
                point_id = str(uuid4())
                payload = {
                    "doc_id": doc_id,
                    "session_id": session_id,
                    "chunk_index": chunk.get("chunk_index", i),
                    "text": chunk.get("text", ""),
                    "page_number": chunk.get("page_number"),
                    "filename": metadata.get("filename", ""),
                    "document_type": metadata.get("document_type", ""),
                    "content_hash": metadata.get("content_hash", ""),
                    "upload_timestamp": metadata.get("upload_timestamp", ""),
                }

                points.append(
                    qdrant_models.PointStruct(
                        id=point_id, vector=embedding, payload=payload
                    )
                )

            batch_size = self.settings.vector_store_batch_size
            for i in range(0, len(points), batch_size):
                batch = points[i : i + batch_size]
                await self.client.upsert(
                    collection_name=self.collection_name, points=batch
                )

            elapsed = time.time() - start_time
            logger.info(
                "Upserted %d chunks for doc %s in %.2fs", len(points), doc_id, elapsed
            )

            return len(points)

        except Exception as e:
            logger.error("Failed to upsert chunks for doc %s: %s", doc_id, e)
            raise VectorStoreError(f"Failed to upsert chunks: {e}") from e

    async def search(
        self,
        query_embedding: list[float],
        session_id: str,
        doc_ids: list[str] | None = None,
        top_k: int | None = None,
    ) -> list[RetrievedChunk]:
        """Search for similar chunks.

        Args:
            query_embedding: Query vector.
            session_id: Session identifier.
            doc_ids: Optional list of document IDs to filter by.
            top_k: Number of results to return (defaults to settings.retrieval_top_k).

        Returns:
            List of RetrievedChunk objects sorted by relevance.

        Raises:
            ValueError: If session_id is empty.
            VectorStoreError: If search fails.
        """
        if not session_id:
            raise ValueError("session_id is required")

        await self.initialize()

        if top_k is None:
            top_k = self.settings.retrieval_top_k

        try:
            start_time = time.time()

            must_conditions = [
                qdrant_models.FieldCondition(
                    key="session_id",
                    match=qdrant_models.MatchValue(value=session_id),
                )
            ]

            if doc_ids:
                must_conditions.append(
                    qdrant_models.FieldCondition(
                        key="doc_id",
                        match=qdrant_models.MatchAny(any=doc_ids),
                    )
                )

            results = await self.client.query_points(
                collection_name=self.collection_name,
                query=query_embedding,
                query_filter=qdrant_models.Filter(must=must_conditions),
                limit=top_k,
                with_payload=True,
            )

            elapsed = time.time() - start_time
            logger.debug(
                "Search returned %d results in %.3fs", len(results.points), elapsed
            )

            return [
                RetrievedChunk(
                    text=point.payload.get("text", ""),
                    filename=point.payload.get("filename", ""),
                    page_number=point.payload.get("page_number"),
                    chunk_index=point.payload.get("chunk_index", 0),
                    doc_id=point.payload.get("doc_id", ""),
                    score=point.score,
                )
                for point in results.points
            ]

        except Exception as e:
            logger.error("Search failed: %s", e)
            raise VectorStoreError(f"Search failed: {e}") from e

    async def delete_document(self, doc_id: str, session_id: str) -> int:
        """Delete all chunks for a document.

        Args:
            doc_id: Document identifier.
            session_id: Session identifier.

        Returns:
            Number of chunks deleted.

        Raises:
            ValueError: If doc_id or session_id is empty.
            VectorStoreError: If deletion fails.
        """
        if not doc_id or not session_id:
            raise ValueError("doc_id and session_id are required")

        await self.initialize()

        try:
            scroll_limit = self.settings.vector_store_scroll_limit
            results = await self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=qdrant_models.Filter(
                    must=[
                        qdrant_models.FieldCondition(
                            key="session_id",
                            match=qdrant_models.MatchValue(value=session_id),
                        ),
                        qdrant_models.FieldCondition(
                            key="doc_id",
                            match=qdrant_models.MatchValue(value=doc_id),
                        ),
                    ]
                ),
                limit=scroll_limit,
            )
            count = len(results[0])

            await self.client.delete(
                collection_name=self.collection_name,
                points_selector=qdrant_models.FilterSelector(
                    filter=qdrant_models.Filter(
                        must=[
                            qdrant_models.FieldCondition(
                                key="session_id",
                                match=qdrant_models.MatchValue(value=session_id),
                            ),
                            qdrant_models.FieldCondition(
                                key="doc_id",
                                match=qdrant_models.MatchValue(value=doc_id),
                            ),
                        ]
                    )
                ),
            )

            logger.info("Deleted %d chunks for doc %s", count, doc_id)
            return count

        except Exception as e:
            logger.error("Failed to delete document %s: %s", doc_id, e)
            raise VectorStoreError(f"Failed to delete document: {e}") from e

    async def get_session_documents(self, session_id: str) -> list[DocumentInfo]:
        """Get all unique documents for a session.

        Args:
            session_id: Session identifier.

        Returns:
            List of DocumentInfo objects.

        Raises:
            ValueError: If session_id is empty.
            VectorStoreError: If query fails.
        """
        if not session_id:
            raise ValueError("session_id is required")

        await self.initialize()

        try:
            scroll_limit = self.settings.vector_store_scroll_limit
            results = await self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=qdrant_models.Filter(
                    must=[
                        qdrant_models.FieldCondition(
                            key="session_id",
                            match=qdrant_models.MatchValue(value=session_id),
                        ),
                    ]
                ),
                limit=scroll_limit,
            )

            docs: dict[str, DocumentInfo] = {}
            for point in results[0]:
                doc_id = point.payload.get("doc_id")
                if doc_id not in docs:
                    docs[doc_id] = DocumentInfo(
                        doc_id=doc_id,
                        filename=point.payload.get("filename", ""),
                        document_type=point.payload.get("document_type", ""),
                        content_hash=point.payload.get("content_hash", ""),
                        upload_timestamp=point.payload.get("upload_timestamp", ""),
                        total_chunks=0,
                    )
                docs[doc_id].total_chunks += 1

            return list(docs.values())

        except Exception as e:
            logger.error("Failed to get session documents: %s", e)
            raise VectorStoreError(f"Failed to get documents: {e}") from e

    async def health_check(self) -> dict[str, object]:
        """Check vector store health.

        Returns:
            Dict with status, latency_ms, and collections count.
        """
        try:
            start_time = time.time()
            collections = await self.client.get_collections()
            latency = (time.time() - start_time) * 1000

            return {
                "status": "healthy",
                "latency_ms": round(latency, 2),
                "collections": len(collections.collections),
            }

        except Exception as e:
            logger.warning("Vector store health check failed: %s", e)
            return {"status": "unhealthy", "error": str(e)}
