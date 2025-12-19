"""Text chunking service for RAG document processing.

Implements simple character-based chunking with overlap for context preservation.
Chunks are split at natural boundaries (paragraphs, sentences) when possible.
"""

import logging
import re
from dataclasses import dataclass

from app.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class TextChunk:
    """A chunk of text with metadata."""

    text: str
    chunk_index: int
    start_char: int
    end_char: int
    page_number: int | None = None


class ChunkerService:
    """Service for chunking text into overlapping segments."""

    def __init__(self) -> None:
        """Initialize chunker with settings."""
        self.settings = get_settings()
        self.chunk_size = self.settings.chunk_size
        self.chunk_overlap = self.settings.chunk_overlap

    def chunk_text(
        self,
        text: str,
        page_count: int | None = None,
    ) -> list[TextChunk]:
        """Split text into overlapping chunks.

        Uses simple character-based chunking with overlap.
        Tries to split at natural boundaries when possible.

        Args:
            text: Full text content to chunk
            page_count: Optional page count for page number estimation

        Returns:
            List of TextChunk objects
        """
        if not text or not text.strip():
            return []

        chunks: list[TextChunk] = []
        text_length = len(text)
        start = 0
        chunk_index = 0

        while start < text_length:
            # Calculate end position
            end = min(start + self.chunk_size, text_length)

            # If not at the end, try to find a good break point
            if end < text_length:
                end = self._find_break_point(text, start, end)

            # Extract chunk text
            chunk_text = text[start:end].strip()

            if chunk_text:
                # Estimate page number if we have page count
                page_number = None
                if page_count and page_count > 0:
                    # Rough estimation based on position in text
                    position_ratio = (start + end) / 2 / text_length
                    page_number = max(1, int(position_ratio * page_count) + 1)

                chunks.append(
                    TextChunk(
                        text=chunk_text,
                        chunk_index=chunk_index,
                        start_char=start,
                        end_char=end,
                        page_number=page_number,
                    )
                )
                chunk_index += 1

            # Move start position with overlap
            start = end - self.chunk_overlap

            # Ensure we make progress
            if start <= chunks[-1].start_char if chunks else 0:
                start = end

        logger.debug(
            "Created %d chunks from %d characters", len(chunks), text_length
        )
        return chunks

    def _find_break_point(self, text: str, start: int, end: int) -> int:
        """Find a natural break point near the end position.

        Looks for breaks in this priority order:
        1. Double newline (paragraph break)
        2. Single newline
        3. Period followed by space (sentence end)
        4. Other sentence-ending punctuation
        5. Comma or semicolon
        6. Space

        Args:
            text: Full text
            start: Chunk start position
            end: Target end position

        Returns:
            Adjusted end position at a natural break
        """
        # Define search window (look back from end)
        search_start = max(start, end - 200)
        search_text = text[search_start:end]

        # Try to find breaks in priority order
        break_patterns = [
            r"\n\n",  # Paragraph break
            r"\n",  # Line break
            r"\. ",  # Period + space
            r"[!?] ",  # Other sentence endings
            r"[,;] ",  # Clause breaks
            r" ",  # Any space
        ]

        for pattern in break_patterns:
            matches = list(re.finditer(pattern, search_text))
            if matches:
                # Use the last match (closest to end)
                last_match = matches[-1]
                # Return position after the break
                return search_start + last_match.end()

        # No good break found, use original end
        return end

    def estimate_chunk_count(self, text_length: int) -> int:
        """Estimate the number of chunks that will be created.

        Useful for validation before processing.

        Args:
            text_length: Length of text in characters

        Returns:
            Estimated number of chunks
        """
        if text_length <= 0:
            return 0

        if text_length <= self.chunk_size:
            return 1

        # Account for overlap
        effective_step = self.chunk_size - self.chunk_overlap
        if effective_step <= 0:
            effective_step = self.chunk_size // 2

        return max(1, (text_length - self.chunk_overlap) // effective_step + 1)

