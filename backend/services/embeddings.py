"""Embedding service for generating vector embeddings via Voyage AI.

Features:
- Batch processing for efficiency
- Automatic retry with exponential backoff
- Free tier: 200M tokens

KNOWN LIMITATIONS:
- The Voyage AI client uses global state for the API key (voyageai.api_key).
  This means only one API key can be used per process. If you need multi-tenant
  support with different API keys, you'll need to use separate processes.
- Retry logic uses time.sleep() inside asyncio.to_thread(), which ties up a
  thread pool thread during backoff. With many concurrent requests hitting
  rate limits, this could exhaust the default thread pool. Consider increasing
  the thread pool size if this becomes an issue.
"""

import logging
import time

try:
    import voyageai
except ImportError:
    voyageai = None

from config import get_settings
from services.embedding_cache import EmbeddingCache

logger = logging.getLogger(__name__)


class EmbeddingError(Exception):
    """Raised when embedding generation fails."""

    pass


class EmbeddingService:
    """Service for generating embeddings using Voyage AI API.

    Note: This service mutates global state (voyageai.api_key) on initialization.
    See module docstring for limitations.
    """

    def __init__(self) -> None:
        """Initialize embedding service with Voyage AI client.

        Raises:
            ImportError: If voyageai package is not installed.
        """
        if voyageai is None:
            raise ImportError(
                "voyageai package not installed. Install with: pip install voyageai"
            )

        self.settings = get_settings()
        # Pass API key directly to client instead of mutating global state
        self.client = voyageai.Client(api_key=self.settings.voyage_api_key)
        self.model = self.settings.embedding_model
        self.dimensions = self.settings.embedding_dimensions
        self.batch_size = self.settings.embedding_batch_size

        # Initialize cache
        self._cache = EmbeddingCache(max_size=10000)
        logger.info("Embedding cache initialized (max_size=10000)")

    async def embed_texts(
        self,
        texts: list[str],
        retry_count: int = 3,
    ) -> list[list[float]]:
        """Generate embeddings for a list of texts.

        Args:
            texts: List of text strings to embed.
            retry_count: Number of retry attempts on failure.

        Returns:
            List of embedding vectors (list of floats).

        Raises:
            EmbeddingError: If embedding generation fails after retries.
            ValueError: If texts is None.
        """

        if texts is None:
            raise ValueError("texts cannot be None")

        if not texts:
            return []

        all_embeddings: list[list[float]] = []

        for i in range(0, len(texts), self.batch_size):
            batch = texts[i : i + self.batch_size]
            batch_embeddings = await self._embed_batch_async(batch, retry_count)
            all_embeddings.extend(batch_embeddings)

        return all_embeddings

    async def embed_text(self, text: str, retry_count: int = 3) -> list[float]:
        """Generate embedding for a single text.

        Args:
            text: Text string to embed.
            retry_count: Number of retry attempts on failure.

        Returns:
            Embedding vector (list of floats).

        Raises:
            EmbeddingError: If embedding generation fails.
            ValueError: If text is None or empty.
        """
        if not text:
            raise ValueError("text cannot be empty")

        # Check cache first
        cached = self._cache.get(text)
        if cached is not None:
            return cached

        embeddings = await self.embed_texts([text], retry_count)
        embedding = embeddings[0]

        # Cache the result
        self._cache.set(text, embedding)

        return embedding

    async def _embed_batch_async(
        self,
        texts: list[str],
        retry_count: int,
    ) -> list[list[float]]:
        """Generate embeddings for a batch of texts with async retry logic.

        Uses asyncio.sleep() for non-blocking backoff instead of time.sleep().
        """
        import asyncio

        last_error: Exception | None = None
        backoff_times = [1, 2, 4]

        for attempt in range(retry_count):
            try:
                start_time = time.time()
                # Run blocking API call in thread pool
                result = await asyncio.to_thread(
                    self.client.embed,
                    texts,
                    model=self.model,
                    input_type="document",
                )
                elapsed = time.time() - start_time
                logger.debug("Generated %d embeddings in %.2fs", len(texts), elapsed)
                return result.embeddings

            except Exception as e:
                last_error = e
                # Sanitize error message to avoid leaking API keys
                error_msg = str(e)
                if "api" in error_msg.lower() or "key" in error_msg.lower():
                    error_msg = f"{type(e).__name__}: [redacted - may contain API key]"

                error_str = str(e).lower()
                is_rate_limit = "rate limit" in error_str or "429" in error_str

                if attempt < retry_count - 1:
                    wait_time = backoff_times[min(attempt, len(backoff_times) - 1)]
                    if is_rate_limit:
                        logger.warning(
                            "Rate limit hit, waiting %ds before retry %d/%d",
                            wait_time,
                            attempt + 1,
                            retry_count,
                        )
                    else:
                        logger.warning(
                            "Embedding API error: %s. Retrying in %ds (%d/%d)",
                            error_msg,  # Use sanitized message
                            wait_time,
                            attempt + 1,
                            retry_count,
                        )
                    # Use async sleep instead of blocking time.sleep()
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(
                        "Embedding generation failed after %d attempts: %s",
                        retry_count,
                        e,
                    )

        raise EmbeddingError(
            f"Failed to generate embeddings after {retry_count} attempts: {last_error}"
        )

    def get_embedding_info(self) -> dict[str, int | str]:
        """Get information about the embedding configuration.

        Returns:
            Dict with model, dimensions, batch_size, and cache stats.
        """
        return {
            "model": self.model,
            "dimensions": self.dimensions,
            "batch_size": self.batch_size,
            "cache": self._cache.get_stats(),
        }
