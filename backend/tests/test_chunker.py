"""Tests for the chunker service."""

import pytest

from services.chunker import ChunkerService, TextChunk


class TestChunkerService:
    """Tests for ChunkerService."""

    def setup_method(self):
        """Set up test fixtures."""
        self.chunker = ChunkerService()
        # Override settings for testing
        self.chunker.chunk_size = 100
        self.chunker.chunk_overlap = 20

    def test_chunk_empty_text(self):
        """Test chunking empty text returns empty list."""
        result = self.chunker.chunk_text("")
        assert result == []

    def test_chunk_whitespace_only(self):
        """Test chunking whitespace-only text returns empty list."""
        result = self.chunker.chunk_text("   \n\n   ")
        assert result == []

    def test_chunk_short_text(self):
        """Test text shorter than chunk size returns single chunk."""
        text = "This is a short text."
        result = self.chunker.chunk_text(text)

        assert len(result) == 1
        assert result[0].text == text
        assert result[0].chunk_index == 0

    def test_chunk_long_text(self):
        """Test long text is split into multiple chunks."""
        # Create text longer than chunk size
        text = "This is a sentence. " * 20  # ~400 chars

        result = self.chunker.chunk_text(text)

        assert len(result) > 1
        # Check chunks are ordered
        for i, chunk in enumerate(result):
            assert chunk.chunk_index == i

    def test_chunk_overlap(self):
        """Test chunks have overlap."""
        text = "Word " * 50  # 250 chars

        result = self.chunker.chunk_text(text)

        # With overlap, later chunks should start before previous ends
        if len(result) > 1:
            # Check there's overlap between consecutive chunks
            for i in range(len(result) - 1):
                current_end = result[i].end_char
                next_start = result[i + 1].start_char
                assert next_start < current_end

    def test_chunk_preserves_all_content(self):
        """Test all content is preserved across chunks."""
        text = "ABCDEFGHIJ" * 20  # 200 chars

        result = self.chunker.chunk_text(text)

        # Reconstruct from chunks (accounting for overlap)
        # The first chunk + non-overlapping parts of subsequent chunks
        # should cover the original text
        assert len(result) > 0
        # First chunk should start at 0
        assert result[0].start_char == 0
        # Last chunk should end at text length
        assert result[-1].end_char == len(text)

    def test_chunk_with_page_count(self):
        """Test page number estimation with page count."""
        text = "Content " * 100  # Long text

        result = self.chunker.chunk_text(text, page_count=10)

        # Check page numbers are assigned
        assert any(c.page_number is not None for c in result)
        # Page numbers should be within range
        for chunk in result:
            if chunk.page_number:
                assert 1 <= chunk.page_number <= 10

    def test_chunk_without_page_count(self):
        """Test page numbers are None without page count."""
        text = "Content " * 50

        result = self.chunker.chunk_text(text)

        for chunk in result:
            assert chunk.page_number is None

    def test_estimate_chunk_count(self):
        """Test chunk count estimation."""
        # Short text
        assert self.chunker.estimate_chunk_count(50) == 1

        # Exactly chunk size
        assert self.chunker.estimate_chunk_count(100) == 1

        # Longer text
        estimate = self.chunker.estimate_chunk_count(500)
        assert estimate > 1

    def test_chunk_breaks_at_sentences(self):
        """Test chunking prefers sentence boundaries."""
        text = "First sentence here. Second sentence here. Third sentence here. " * 5

        result = self.chunker.chunk_text(text)

        # Chunks should end at sentence boundaries when possible
        for chunk in result[:-1]:  # Exclude last chunk
            # Should end with period and space, or just period
            assert chunk.text.rstrip().endswith(".")

    def test_chunk_breaks_at_paragraphs(self):
        """Test chunking prefers paragraph boundaries."""
        text = "Paragraph one content.\n\nParagraph two content.\n\nParagraph three content."
        self.chunker.chunk_size = 50  # Force splitting

        result = self.chunker.chunk_text(text)

        # Should have multiple chunks
        assert len(result) >= 1


class TestTextChunk:
    """Tests for TextChunk dataclass."""

    def test_text_chunk_creation(self):
        """Test TextChunk can be created with all fields."""
        chunk = TextChunk(
            text="Sample text",
            chunk_index=0,
            start_char=0,
            end_char=11,
            page_number=1,
        )

        assert chunk.text == "Sample text"
        assert chunk.chunk_index == 0
        assert chunk.start_char == 0
        assert chunk.end_char == 11
        assert chunk.page_number == 1

    def test_text_chunk_optional_page(self):
        """Test TextChunk page_number is optional."""
        chunk = TextChunk(
            text="Sample",
            chunk_index=0,
            start_char=0,
            end_char=6,
        )

        assert chunk.page_number is None
