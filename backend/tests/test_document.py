"""Tests for the document parsing service."""

import os
import tempfile

import pytest

from services.document import (
    DocumentService,
    EmptyDocumentError,
    FileTooLargeError,
    UnsupportedFileTypeError,
)


class TestDocumentService:
    """Tests for DocumentService."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = DocumentService()

    def test_sanitize_filename_basic(self):
        """Test basic filename sanitization."""
        result = self.service.sanitize_filename("document.pdf")
        assert result == "document.pdf"

    def test_sanitize_filename_path_traversal(self):
        """Test path traversal prevention."""
        result = self.service.sanitize_filename("../../../etc/passwd")
        assert "/" not in result
        assert ".." not in result

    def test_sanitize_filename_special_chars(self):
        """Test special character removal."""
        result = self.service.sanitize_filename('doc<>:"/\\|?*.pdf')
        assert "<" not in result
        assert ">" not in result
        assert ":" not in result

    def test_sanitize_filename_long_name(self):
        """Test long filename truncation."""
        long_name = "a" * 300 + ".pdf"
        result = self.service.sanitize_filename(long_name)
        assert len(result) <= 255
        assert result.endswith(".pdf")

    def test_sanitize_filename_empty(self):
        """Test empty filename handling."""
        result = self.service.sanitize_filename("")
        assert result.startswith("document")

    def test_sanitize_filename_dot_start(self):
        """Test dot-starting filename handling."""
        result = self.service.sanitize_filename(".hidden")
        assert not result.startswith(".")

    def test_validate_file_supported_types(self):
        """Test validation of supported file types."""
        # PDF
        ext = self.service.validate_file("doc.pdf", 1000)
        assert ext == ".pdf"

        # DOCX
        ext = self.service.validate_file("doc.docx", 1000)
        assert ext == ".docx"

        # TXT
        ext = self.service.validate_file("doc.txt", 1000)
        assert ext == ".txt"

    def test_validate_file_unsupported_type(self):
        """Test rejection of unsupported file types."""
        with pytest.raises(UnsupportedFileTypeError):
            self.service.validate_file("doc.exe", 1000)

        with pytest.raises(UnsupportedFileTypeError):
            self.service.validate_file("doc.jpg", 1000)

    def test_validate_file_too_large(self):
        """Test rejection of files exceeding size limit."""
        large_size = 100 * 1024 * 1024  # 100MB
        with pytest.raises(FileTooLargeError):
            self.service.validate_file("doc.pdf", large_size)

    def test_validate_file_case_insensitive(self):
        """Test file extension is case insensitive."""
        ext = self.service.validate_file("DOC.PDF", 1000)
        assert ext == ".pdf"

        ext = self.service.validate_file("Doc.DOCX", 1000)
        assert ext == ".docx"

    def test_compute_content_hash(self):
        """Test content hash computation."""
        text = "Sample document content"
        hash1 = self.service.compute_content_hash(text)

        # Same text should produce same hash
        hash2 = self.service.compute_content_hash(text)
        assert hash1 == hash2

        # Different text should produce different hash
        hash3 = self.service.compute_content_hash("Different content")
        assert hash1 != hash3

    def test_compute_content_hash_normalized(self):
        """Test hash is normalized (case, whitespace)."""
        hash1 = self.service.compute_content_hash("Hello World")
        hash2 = self.service.compute_content_hash("hello   world")

        # Should be same after normalization
        assert hash1 == hash2

    @pytest.mark.asyncio
    async def test_parse_txt_file(self):
        """Test parsing plain text file."""
        # Create temp file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("This is test content.\n\nSecond paragraph.")
            temp_path = f.name

        try:
            result = await self.service.parse_file(temp_path, "test.txt")

            assert "text" in result
            assert "This is test content" in result["text"]
            assert "content_hash" in result
            assert result["metadata"]["document_type"] == "txt"
        finally:
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_parse_empty_txt_file(self):
        """Test parsing empty text file raises error."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("")
            temp_path = f.name

        try:
            with pytest.raises(EmptyDocumentError):
                await self.service.parse_file(temp_path, "empty.txt")
        finally:
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_parse_whitespace_txt_file(self):
        """Test parsing whitespace-only file raises error."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("   \n\n   ")
            temp_path = f.name

        try:
            with pytest.raises(EmptyDocumentError):
                await self.service.parse_file(temp_path, "whitespace.txt")
        finally:
            os.unlink(temp_path)

    def test_normalize_text(self):
        """Test text normalization."""
        text = "Line one\n\n\n\nLine two   with   spaces"
        result = self.service._normalize_text(text)

        # Multiple newlines reduced to double
        assert "\n\n\n" not in result
        # Multiple spaces reduced to single
        assert "   " not in result
