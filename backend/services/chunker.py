"""Text chunking for RAG document processing.

Implements recursive text splitting with overlap for context preservation.
Splits at natural boundaries in priority order:
1. Double newlines (paragraphs)
2. Single newlines
3. Sentence endings (. ! ?)
4. Words (spaces)
5. Characters (fallback)

This is the "Recursive Text Splitter" pattern, widely used in production RAG systems.
"""

import logging

from config import get_settings
from services.types import TextChunk

logger = logging.getLogger(__name__)


# Separators in priority order - try to split at most meaningful boundary first
SEPARATORS = [
    "\n\n",  # Paragraphs
    "\n",  # Lines
    ". ",  # Sentences (with space after)
    "! ",  # Exclamations
    "? ",  # Questions
    "; ",  # Semicolons
    ", ",  # Clauses
    " ",  # Words
    "",  # Characters (fallback)
]


class Chunker:
    """Chunks text using recursive splitting at natural boundaries.

    This implementation follows the "Recursive Text Splitter" pattern:
    1. Try to split at the most meaningful separator (paragraphs first)
    2. If chunks are still too large, recursively split with next separator
    3. Merge small chunks back together to hit target size
    4. Add overlap between chunks for context preservation
    """

    def __init__(self) -> None:
        """Initialize chunker with settings."""
        settings = get_settings()
        self.chunk_size = settings.chunk_size
        self.chunk_overlap = settings.chunk_overlap
        self.separators = SEPARATORS

    def chunk_text(
        self,
        text: str,
        page_count: int | None = None,
    ) -> list[TextChunk]:
        """Split text into overlapping chunks at natural boundaries.

        Args:
            text: Full document text to chunk.
            page_count: Optional page count for page estimation.

        Returns:
            List of TextChunk objects with position metadata.
        """
        if not text or not text.strip():
            return []

        text = text.strip()
        text_length = len(text)

        # Recursively split the text
        raw_chunks = self._split_text(text, self.separators)

        # Merge small chunks and add overlap
        merged_chunks = self._merge_with_overlap(raw_chunks)

        # Convert to TextChunk objects with metadata
        chunks: list[TextChunk] = []
        current_pos = 0

        for chunk_index, chunk_text in enumerate(merged_chunks):
            if not chunk_text.strip():
                continue

            # Find actual position in original text
            start = text.find(chunk_text[:50], current_pos)  # Use prefix to find
            if start == -1:
                start = current_pos
            end = start + len(chunk_text)
            current_pos = max(current_pos, end - self.chunk_overlap)

            # Estimate page number
            page_number = None
            if page_count and page_count > 0:
                chunk_midpoint = (start + end) / 2
                position_ratio = chunk_midpoint / text_length
                estimated_page = int(position_ratio * page_count) + 1
                page_number = max(1, min(estimated_page, page_count))

            chunks.append(
                TextChunk(
                    text=chunk_text.strip(),
                    chunk_index=chunk_index,
                    start_char=start,
                    end_char=end,
                    page_number=page_number,
                )
            )

        logger.info(
            "Chunking complete: %d chars -> %d chunks (target size: %d, overlap: %d)",
            text_length,
            len(chunks),
            self.chunk_size,
            self.chunk_overlap,
        )

        return chunks

    def _split_text(self, text: str, separators: list[str]) -> list[str]:
        """Recursively split text using separators in priority order.

        Args:
            text: Text to split.
            separators: List of separators to try, in order of preference.

        Returns:
            List of text chunks.
        """
        if not text:
            return []

        # Base case: text is small enough
        if len(text) <= self.chunk_size:
            return [text]

        # Try each separator in order
        for i, separator in enumerate(separators):
            if separator == "":
                # Fallback: character-level split
                return self._split_by_chars(text)

            if separator not in text:
                continue

            # Split by this separator
            parts = text.split(separator)

            # Add separator back to each part (except last)
            parts = [p + separator for p in parts[:-1]] + [parts[-1]]

            # Recursively split any parts that are still too large
            result = []
            remaining_separators = separators[i + 1 :]

            for part in parts:
                if len(part) <= self.chunk_size:
                    result.append(part)
                else:
                    # Part is too large, split with finer separators
                    result.extend(self._split_text(part, remaining_separators))

            return result

        # No separator worked, fall back to character split
        return self._split_by_chars(text)

    def _split_by_chars(self, text: str) -> list[str]:
        """Split text by characters as fallback.

        Tries to split at word boundaries when possible.
        """
        chunks = []
        start = 0

        while start < len(text):
            end = min(start + self.chunk_size, len(text))

            # Try to end at a word boundary
            if end < len(text):
                # Look for last space within chunk
                last_space = text.rfind(" ", start, end)
                if last_space > start + self.chunk_size // 2:
                    end = last_space + 1

            chunks.append(text[start:end])
            start = end

        return chunks

    def _merge_with_overlap(self, chunks: list[str]) -> list[str]:
        """Merge small chunks and add overlap between chunks.

        Args:
            chunks: List of raw text chunks.

        Returns:
            List of chunks with overlap applied.
        """
        if not chunks:
            return []

        # First, merge adjacent small chunks
        merged = []
        current = ""

        for chunk in chunks:
            if not chunk.strip():
                continue

            if len(current) + len(chunk) <= self.chunk_size:
                current += chunk
            else:
                if current:
                    merged.append(current)
                current = chunk

        if current:
            merged.append(current)

        # Now add overlap between chunks
        if self.chunk_overlap <= 0 or len(merged) <= 1:
            return merged

        result = [merged[0]]

        for i in range(1, len(merged)):
            prev_chunk = merged[i - 1]
            curr_chunk = merged[i]

            # Get overlap from end of previous chunk
            overlap_text = (
                prev_chunk[-self.chunk_overlap :]
                if len(prev_chunk) > self.chunk_overlap
                else prev_chunk
            )

            # Try to start overlap at a word boundary
            space_idx = overlap_text.find(" ")
            if space_idx > 0:
                overlap_text = overlap_text[space_idx + 1 :]

            result.append(overlap_text + curr_chunk)

        return result

    def estimate_chunk_count(self, text_length: int) -> int:
        """Estimate number of chunks for a given text length.

        Args:
            text_length: Length of text in characters.

        Returns:
            Estimated number of chunks.
        """
        if text_length <= 0:
            return 0

        effective_step = self.chunk_size - self.chunk_overlap
        if effective_step <= 0:
            effective_step = self.chunk_size // 2

        return max(1, (text_length - self.chunk_overlap) // effective_step + 1)
