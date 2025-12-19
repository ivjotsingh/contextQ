"""Embedding service for generating vector embeddings via Voyage AI.

Features:
- Batch processing for efficiency
- Automatic retry with exponential backoff
- Integration with cache service
- Free tier: 200M tokens
"""

import logging
import time
from typing import Any

try:
    import voyageai
except ImportError:
    voyageai = None  # Will raise error on init if not installed

from app.config import get_settings

logger = logging.getLogger(__name__)


class EmbeddingError(Exception):
    """Raised when embedding generation fails."""

    pass


class EmbeddingService:
    """Service for generating embeddings using Voyage AI API.

    Voyage AI offers:
    - Free tier: 200M tokens
    - Superior performance vs OpenAI embeddings
    - Lower cost and latency
    """

    def __init__(self) -> None:
        """Initialize embedding service with Voyage AI client."""
        if voyageai is None:
            raise ImportError(
                "voyageai package not installed. Install with: pip install voyageai"
            )
        
        self.settings = get_settings()
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

        Processes texts in batches for efficiency.
        Note: Voyage AI SDK is synchronous, so we run it in executor.

        Args:
            texts: List of text strings to embed
            retry_count: Number of retries on failure

        Returns:
            List of embedding vectors (same order as input)

        Raises:
            EmbeddingError: If embedding generation fails after retries
        """
        import asyncio

        if not texts:
            return []

        all_embeddings: list[list[float]] = []

        # Process in batches
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i : i + self.batch_size]
            # Run synchronous Voyage AI call in executor
            batch_embeddings = await asyncio.to_thread(
                self._embed_batch_sync, batch, retry_count
            )
            all_embeddings.extend(batch_embeddings)

        return all_embeddings

    async def embed_text(self, text: str, retry_count: int = 3) -> list[float]:
        """Generate embedding for a single text.

        Args:
            text: Text string to embed
            retry_count: Number of retries on failure

        Returns:
            Embedding vector

        Raises:
            EmbeddingError: If embedding generation fails
        """
        embeddings = await self.embed_texts([text], retry_count)
        return embeddings[0]

    def _embed_batch_sync(
        self,
        texts: list[str],
        retry_count: int,
    ) -> list[list[float]]:
        """Generate embeddings for a batch of texts with retry logic (synchronous).

        Args:
            texts: Batch of texts to embed
            retry_count: Remaining retry attempts

        Returns:
            List of embedding vectors

        Raises:
            EmbeddingError: If all retries fail
        """
        last_error: Exception | None = None
        backoff_times = [1, 2, 4]  # Exponential backoff in seconds

        for attempt in range(retry_count):
            try:
                start_time = time.time()

                # Voyage AI embedding call (synchronous)
                result = self.client.embed(
                    texts,
                    model=self.model,
                    input_type="document",  # For document chunks
                )

                elapsed = time.time() - start_time
                logger.debug(
                    "Generated %d embeddings in %.2fs",
                    len(texts),
                    elapsed,
                )

                # Voyage AI returns embeddings directly
                embeddings = result.embeddings
                return embeddings

            except Exception as e:
                # Check if it's a rate limit error
                error_str = str(e).lower()
                if "rate limit" in error_str or "429" in error_str:
                    last_error = e
                    wait_time = backoff_times[min(attempt, len(backoff_times) - 1)]
                    logger.warning(
                        "Rate limit hit, waiting %ds before retry %d/%d",
                        wait_time,
                        attempt + 1,
                        retry_count,
                    )
                    time.sleep(wait_time)
                elif attempt < retry_count - 1:
                    last_error = e
                    wait_time = backoff_times[min(attempt, len(backoff_times) - 1)]
                    logger.warning(
                        "API error: %s. Retrying in %ds (%d/%d)",
                        e,
                        wait_time,
                        attempt + 1,
                        retry_count,
                    )
                    time.sleep(wait_time)
                else:
                    last_error = e
                    logger.exception("Unexpected error during embedding generation")
                    break

        raise EmbeddingError(
            f"Failed to generate embeddings after {retry_count} attempts: {last_error}"
        )

    def get_embedding_info(self) -> dict[str, Any]:
        """Get information about the embedding configuration.

        Returns:
            Dictionary with model name, dimensions, and batch size
        """
        return {
            "model": self.model,
            "dimensions": self.dimensions,
            "batch_size": self.batch_size,
        }

