"""Cache service for Redis operations.

Handles:
- Query embedding caching
- Response caching with document context
- Session management
- Cache invalidation on document deletion
"""

import hashlib
import json
import logging
import time
from typing import Any

import redis.asyncio as redis

from app.config import get_settings

logger = logging.getLogger(__name__)


class CacheError(Exception):
    """Raised when cache operations fail."""

    pass


class CacheService:
    """Service for Redis caching operations."""

    def __init__(self) -> None:
        """Initialize cache service with Redis client."""
        self.settings = get_settings()
        self._client: redis.Redis | None = None

    async def _get_client(self) -> redis.Redis:
        """Get or create Redis client.

        Returns:
            Redis client instance
        """
        if self._client is None:
            self._client = redis.from_url(
                self.settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
        return self._client

    def _make_embedding_key(self, text: str) -> str:
        """Create cache key for embedding.

        Args:
            text: Text to embed

        Returns:
            Cache key string
        """
        text_hash = hashlib.sha256(text.encode()).hexdigest()[:16]
        return f"emb:{text_hash}"

    def _make_response_key(self, question: str, doc_ids: list[str]) -> str:
        """Create cache key for response.

        Includes sorted doc_ids to ensure same documents = same key.

        Args:
            question: User question
            doc_ids: List of document IDs

        Returns:
            Cache key string
        """
        sorted_ids = sorted(doc_ids)
        combined = f"{question}:{','.join(sorted_ids)}"
        combined_hash = hashlib.sha256(combined.encode()).hexdigest()[:16]
        return f"resp:{combined_hash}"

    def _make_session_key(self, session_id: str) -> str:
        """Create cache key for session data.

        Args:
            session_id: Session ID

        Returns:
            Cache key string
        """
        return f"session:{session_id}"

    async def get_embedding(self, text: str) -> list[float] | None:
        """Get cached embedding for text.

        Args:
            text: Text that was embedded

        Returns:
            Cached embedding or None if not found
        """
        try:
            client = await self._get_client()
            key = self._make_embedding_key(text)
            cached = await client.get(key)

            if cached:
                logger.debug("Cache hit for embedding: %s", key)
                return json.loads(cached)

            logger.debug("Cache miss for embedding: %s", key)
            return None

        except Exception as e:
            logger.warning("Error getting cached embedding: %s", e)
            return None

    async def set_embedding(
        self,
        text: str,
        embedding: list[float],
    ) -> bool:
        """Cache an embedding.

        Args:
            text: Text that was embedded
            embedding: Embedding vector

        Returns:
            True if cached successfully
        """
        try:
            client = await self._get_client()
            key = self._make_embedding_key(text)
            await client.setex(
                key,
                self.settings.embedding_cache_ttl,
                json.dumps(embedding),
            )
            return True

        except Exception as e:
            logger.warning("Error caching embedding: %s", e)
            return False

    async def get_response(
        self,
        question: str,
        doc_ids: list[str],
    ) -> dict[str, Any] | None:
        """Get cached response for a question.

        Args:
            question: User question
            doc_ids: Document IDs that were searched

        Returns:
            Cached response or None if not found
        """
        try:
            client = await self._get_client()
            key = self._make_response_key(question, doc_ids)
            cached = await client.get(key)

            if cached:
                logger.debug("Cache hit for response: %s", key)
                return json.loads(cached)

            logger.debug("Cache miss for response: %s", key)
            return None

        except Exception as e:
            logger.warning("Error getting cached response: %s", e)
            return None

    async def set_response(
        self,
        question: str,
        doc_ids: list[str],
        response: dict[str, Any],
    ) -> bool:
        """Cache a response.

        Args:
            question: User question
            doc_ids: Document IDs that were searched
            response: Response to cache

        Returns:
            True if cached successfully
        """
        try:
            client = await self._get_client()
            key = self._make_response_key(question, doc_ids)
            await client.setex(
                key,
                self.settings.response_cache_ttl,
                json.dumps(response),
            )
            return True

        except Exception as e:
            logger.warning("Error caching response: %s", e)
            return False

    async def invalidate_document_cache(
        self,
        doc_id: str,
        session_id: str,
    ) -> int:
        """Invalidate all cache entries related to a document.

        Since response keys include doc_ids, we need to track which
        responses include which documents. For simplicity, we use
        a pattern-based approach.

        Args:
            doc_id: Document ID being deleted
            session_id: Session ID

        Returns:
            Number of keys deleted
        """
        try:
            client = await self._get_client()

            # Get all response keys for this session
            session_key = self._make_session_key(session_id)
            response_keys = await client.smembers(f"{session_key}:responses")

            deleted = 0
            for key in response_keys:
                # Check if this response involved the deleted document
                cached = await client.get(key)
                if cached:
                    data = json.loads(cached)
                    if doc_id in data.get("doc_ids", []):
                        await client.delete(key)
                        deleted += 1

            logger.info(
                "Invalidated %d cache entries for doc %s",
                deleted,
                doc_id,
            )
            return deleted

        except Exception as e:
            logger.warning("Error invalidating cache: %s", e)
            return 0

    async def get_session(self, session_id: str) -> dict[str, Any] | None:
        """Get session data.

        Args:
            session_id: Session ID

        Returns:
            Session data or None if not found
        """
        try:
            client = await self._get_client()
            key = self._make_session_key(session_id)
            cached = await client.get(key)

            if cached:
                # Refresh TTL on access
                await client.expire(key, self.settings.session_ttl)
                return json.loads(cached)

            return None

        except Exception as e:
            logger.warning("Error getting session: %s", e)
            return None

    async def set_session(
        self,
        session_id: str,
        data: dict[str, Any],
    ) -> bool:
        """Set or update session data.

        Args:
            session_id: Session ID
            data: Session data to store

        Returns:
            True if stored successfully
        """
        try:
            client = await self._get_client()
            key = self._make_session_key(session_id)
            await client.setex(
                key,
                self.settings.session_ttl,
                json.dumps(data),
            )
            return True

        except Exception as e:
            logger.warning("Error setting session: %s", e)
            return False

    async def add_document_to_session(
        self,
        session_id: str,
        doc_id: str,
    ) -> bool:
        """Add a document ID to the session's document list.

        Args:
            session_id: Session ID
            doc_id: Document ID to add

        Returns:
            True if added successfully
        """
        try:
            client = await self._get_client()
            key = f"{self._make_session_key(session_id)}:docs"
            await client.sadd(key, doc_id)
            await client.expire(key, self.settings.session_ttl)
            return True

        except Exception as e:
            logger.warning("Error adding doc to session: %s", e)
            return False

    async def remove_document_from_session(
        self,
        session_id: str,
        doc_id: str,
    ) -> bool:
        """Remove a document ID from the session's document list.

        Args:
            session_id: Session ID
            doc_id: Document ID to remove

        Returns:
            True if removed successfully
        """
        try:
            client = await self._get_client()
            key = f"{self._make_session_key(session_id)}:docs"
            await client.srem(key, doc_id)
            return True

        except Exception as e:
            logger.warning("Error removing doc from session: %s", e)
            return False

    async def get_session_doc_ids(self, session_id: str) -> list[str]:
        """Get all document IDs for a session.

        Args:
            session_id: Session ID

        Returns:
            List of document IDs
        """
        try:
            client = await self._get_client()
            key = f"{self._make_session_key(session_id)}:docs"
            doc_ids = await client.smembers(key)
            return list(doc_ids)

        except Exception as e:
            logger.warning("Error getting session docs: %s", e)
            return []

    async def health_check(self) -> dict[str, Any]:
        """Check cache health.

        Returns:
            Health status dictionary
        """
        try:
            client = await self._get_client()
            start_time = time.time()
            await client.ping()
            latency = (time.time() - start_time) * 1000

            return {
                "status": "healthy",
                "latency_ms": round(latency, 2),
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
            }

    async def close(self) -> None:
        """Close the Redis connection."""
        if self._client:
            await self._client.close()
            self._client = None

