"""Text chunking for RAG document processing.

Implements character-based chunking with overlap for context preservation.
Chunks are split at natural boundaries (paragraphs, sentences) when possible.
"""

import logging
import re
from dataclasses import dataclass

from config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class TextChunk:
    """A chunk of text with position metadata."""

    text: str
    chunk_index: int
    start_char: int
    end_char: int
    page_number: int | None = None


class Chunker:
    """Chunks text into overlapping segments for RAG retrieval."""

    def __init__(self) -> None:
        """Initialize chunker with settings."""
        self.settings = get_settings()
        self.chunk_size = self.settings.chunk_size
        self.chunk_overlap = self.settings.chunk_overlap

    def chunk_text(self, text: str, page_count: int | None = None) -> list[TextChunk]:
        """Split text into overlapping chunks."""
        if text is None:
            raise ValueError("Text cannot be None")

        if not text or not text.strip():
            return []

        chunks: list[TextChunk] = []
        text_length = len(text)
        start = 0
        chunk_index = 0

        while start < text_length:
            end = min(start + self.chunk_size, text_length)

            if end < text_length:
                end = self._find_break_point(text, start, end)

            chunk_text = text[start:end].strip()

            if chunk_text:
                page_number = None
                if page_count and page_count > 0:
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

            start = end - self.chunk_overlap

            if chunks and start <= chunks[-1].start_char:
                start = end

        logger.debug("Created %d chunks from %d characters", len(chunks), text_length)
        return chunks

    def _find_break_point(self, text: str, start: int, end: int) -> int:
        """Find a natural break point near the end position."""
        search_start = max(start, end - 200)
        search_text = text[search_start:end]

        break_patterns = [
            r"\n\n",
            r"\n",
            r"\. ",
            r"[!?] ",
            r"[,;] ",
            r" ",
        ]

        for pattern in break_patterns:
            matches = list(re.finditer(pattern, search_text))
            if matches:
                last_match = matches[-1]
                return search_start + last_match.end()

        return end

    def estimate_chunk_count(self, text_length: int) -> int:
        """Estimate the number of chunks that will be created."""
        if text_length <= 0:
            return 0

        if text_length <= self.chunk_size:
            return 1

        effective_step = self.chunk_size - self.chunk_overlap
        if effective_step <= 0:
            effective_step = self.chunk_size // 2

        return max(1, (text_length - self.chunk_overlap) // effective_step + 1)


# Lazy singleton
_chunker: Chunker | None = None


def get_chunker_service() -> Chunker:
    """Get chunker service singleton."""
    global _chunker
    if _chunker is None:
        _chunker = Chunker()
    return _chunker

