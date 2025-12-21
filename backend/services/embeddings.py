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
        # WARNING: This mutates global state. See module docstring.
        voyageai.api_key = self.settings.voyage_api_key
        self.client = voyageai.Client()
        self.model = self.settings.embedding_model
        self.dimensions = self.settings.embedding_dimensions
        self.batch_size = self.settings.embedding_batch_size

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
        import asyncio

        if texts is None:
            raise ValueError("texts cannot be None")

        if not texts:
            return []

        all_embeddings: list[list[float]] = []

        for i in range(0, len(texts), self.batch_size):
            batch = texts[i : i + self.batch_size]
            # Note: _embed_batch_sync uses time.sleep for retry backoff,
            # which blocks the thread pool thread. See module docstring.
            batch_embeddings = await asyncio.to_thread(
                self._embed_batch_sync, batch, retry_count
            )
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

        embeddings = await self.embed_texts([text], retry_count)
        return embeddings[0]

    def _embed_batch_sync(
        self,
        texts: list[str],
        retry_count: int,
    ) -> list[list[float]]:
        """Generate embeddings for a batch of texts with retry logic.

        Note: Uses time.sleep() for backoff, which blocks the thread.
        This is acceptable since this runs in asyncio.to_thread().
        """
        last_error: Exception | None = None
        backoff_times = [1, 2, 4]

        for attempt in range(retry_count):
            try:
                start_time = time.time()
                result = self.client.embed(
                    texts, model=self.model, input_type="document"
                )
                elapsed = time.time() - start_time
                logger.debug("Generated %d embeddings in %.2fs", len(texts), elapsed)
                return result.embeddings

            except Exception as e:
                last_error = e
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
                            "API error: %s. Retrying in %ds (%d/%d)",
                            e,
                            wait_time,
                            attempt + 1,
                            retry_count,
                        )
                    time.sleep(wait_time)
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
            Dict with model, dimensions, and batch_size.
        """
        return {
            "model": self.model,
            "dimensions": self.dimensions,
            "batch_size": self.batch_size,
        }


# Lazy singleton
_embedding_service: EmbeddingService | None = None


def get_embedding_service() -> EmbeddingService:
    """Get embedding service singleton."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
