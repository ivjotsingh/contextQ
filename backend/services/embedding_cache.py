"""Embedding cache for reducing API calls and costs.

Caches embeddings by content hash to avoid re-computing identical text.
"""

import hashlib
import logging

logger = logging.getLogger(__name__)


class EmbeddingCache:
    """Simple in-memory cache for embeddings."""

    def __init__(self, max_size: int = 10000):
        """Initialize cache with max size limit."""
        self._cache: dict[str, list[float]] = {}
        self.max_size = max_size
        self.hits = 0
        self.misses = 0

    def _get_key(self, text: str) -> str:
        """Generate cache key from text content."""
        return hashlib.sha256(text.encode()).hexdigest()

    def get(self, text: str) -> list[float] | None:
        """Get embedding from cache if exists."""
        key = self._get_key(text)
        if key in self._cache:
            self.hits += 1
            logger.debug(
                "Embedding cache hit (total: %d hits, %d misses)",
                self.hits,
                self.misses,
            )
            return self._cache[key]
        self.misses += 1
        return None

    def set(self, text: str, embedding: list[float]) -> None:
        """Store embedding in cache."""
        if len(self._cache) >= self.max_size:
            # Simple eviction: remove oldest (first) entry
            first_key = next(iter(self._cache))
            del self._cache[first_key]
            logger.debug("Cache full, evicted oldest entry")

        key = self._get_key(text)
        self._cache[key] = embedding

    def get_stats(self) -> dict:
        """Get cache statistics."""
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": f"{hit_rate:.1f}%",
        }
