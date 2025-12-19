"""Document parsing service for PDF, Word, and text files.

Handles:
- File validation (MIME type, size, structure)
- Text extraction from PDF (PyMuPDF), DOCX (python-docx), and TXT files
- Filename sanitization for security
- Content hashing for idempotency
"""

import hashlib
import logging
import re
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF
from docx import Document as DocxDocument

from app.config import get_settings

logger = logging.getLogger(__name__)

# Supported file types and their MIME types
SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt"}
MIME_TYPE_MAP = {
    ".pdf": ["application/pdf"],
    ".docx": [
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ],
    ".txt": ["text/plain"],
}


class DocumentParseError(Exception):
    """Raised when document parsing fails."""

    pass


class UnsupportedFileTypeError(Exception):
    """Raised when file type is not supported."""

    pass


class FileTooLargeError(Exception):
    """Raised when file exceeds size limit."""

    pass


class EmptyDocumentError(Exception):
    """Raised when document contains no extractable text."""

    pass


class DocumentService:
    """Service for parsing and processing documents."""

    def __init__(self) -> None:
        """Initialize document service."""
        self.settings = get_settings()

    def sanitize_filename(self, filename: str) -> str:
        """Sanitize filename to prevent path traversal and other issues.

        Args:
            filename: Original filename

        Returns:
            Sanitized filename safe for storage
        """
        # Remove path separators
        filename = Path(filename).name

        # Remove or replace dangerous characters
        filename = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", filename)

        # Limit length
        max_length = 255
        if len(filename) > max_length:
            name, ext = Path(filename).stem, Path(filename).suffix
            filename = name[: max_length - len(ext)] + ext

        # Ensure not empty
        if not filename or filename.startswith("."):
            filename = "document" + Path(filename).suffix

        return filename

    def validate_file(
        self, filename: str, file_size: int, content_type: str | None = None
    ) -> str:
        """Validate uploaded file.

        Args:
            filename: Original filename
            file_size: File size in bytes
            content_type: MIME type from upload

        Returns:
            File extension (lowercase with dot)

        Raises:
            UnsupportedFileTypeError: If file type not supported
            FileTooLargeError: If file exceeds size limit
        """
        # Check file size
        if file_size > self.settings.max_file_size_bytes:
            raise FileTooLargeError(
                f"File size {file_size} exceeds limit of "
                f"{self.settings.max_file_size_mb}MB"
            )

        # Get and validate extension
        ext = Path(filename).suffix.lower()
        if ext not in SUPPORTED_EXTENSIONS:
            raise UnsupportedFileTypeError(
                f"File type '{ext}' not supported. "
                f"Supported: {', '.join(SUPPORTED_EXTENSIONS)}"
            )

        return ext

    def compute_content_hash(self, text: str) -> str:
        """Compute SHA256 hash of normalized text content.

        Args:
            text: Extracted text content

        Returns:
            SHA256 hash as hex string
        """
        # Normalize: lowercase, remove extra whitespace
        normalized = " ".join(text.lower().split())
        return hashlib.sha256(normalized.encode()).hexdigest()

    async def parse_file(
        self, file_path: str, filename: str
    ) -> dict[str, Any]:
        """Parse a document file and extract text content.

        Args:
            file_path: Path to the uploaded file
            filename: Original filename for metadata

        Returns:
            Dictionary with:
            - text: Extracted text content
            - page_count: Number of pages (if applicable)
            - metadata: Additional file metadata
            - content_hash: SHA256 hash of content

        Raises:
            DocumentParseError: If parsing fails
            EmptyDocumentError: If no text could be extracted
        """
        ext = Path(filename).suffix.lower()

        try:
            if ext == ".pdf":
                result = await self._parse_pdf(file_path)
            elif ext == ".docx":
                result = await self._parse_docx(file_path)
            elif ext == ".txt":
                result = await self._parse_txt(file_path)
            else:
                raise UnsupportedFileTypeError(f"Unsupported file type: {ext}")

            # Validate we got content
            text = result.get("text", "").strip()
            if not text:
                raise EmptyDocumentError("Document contains no extractable text")

            # Normalize whitespace
            text = self._normalize_text(text)
            result["text"] = text

            # Compute content hash
            result["content_hash"] = self.compute_content_hash(text)

            # Add filename to metadata
            result["metadata"]["filename"] = self.sanitize_filename(filename)
            result["metadata"]["document_type"] = ext.lstrip(".")

            return result

        except (EmptyDocumentError, UnsupportedFileTypeError):
            raise
        except Exception as e:
            logger.exception("Failed to parse document: %s", filename)
            raise DocumentParseError(f"Failed to parse document: {e}") from e

    def _normalize_text(self, text: str) -> str:
        """Normalize text by cleaning up whitespace.

        Args:
            text: Raw extracted text

        Returns:
            Normalized text with cleaned whitespace
        """
        # Replace multiple newlines with double newline
        text = re.sub(r"\n{3,}", "\n\n", text)
        # Replace multiple spaces with single space
        text = re.sub(r" {2,}", " ", text)
        # Strip lines
        lines = [line.strip() for line in text.split("\n")]
        return "\n".join(lines).strip()

    async def _parse_pdf(self, file_path: str) -> dict[str, Any]:
        """Parse PDF file using PyMuPDF.

        Args:
            file_path: Path to PDF file

        Returns:
            Parsed content with text, page_count, and metadata
        """
        try:
            doc = fitz.open(file_path)
            text_parts = []
            page_count = len(doc)

            for page_num, page in enumerate(doc, start=1):
                try:
                    page_text = page.get_text()
                    if page_text:
                        text_parts.append(page_text)
                except Exception as e:
                    logger.warning(
                        "Failed to extract text from page %d: %s", page_num, e
                    )

            # Extract metadata
            metadata = {}
            if doc.metadata:
                metadata = {
                    "title": doc.metadata.get("title", ""),
                    "author": doc.metadata.get("author", ""),
                    "subject": doc.metadata.get("subject", ""),
                    "creator": doc.metadata.get("creator", ""),
                }

            doc.close()

            return {
                "text": "\n\n".join(text_parts),
                "page_count": page_count,
                "metadata": metadata,
            }

        except Exception as e:
            raise DocumentParseError(f"Failed to parse PDF: {e}") from e

    async def _parse_docx(self, file_path: str) -> dict[str, Any]:
        """Parse Word document using python-docx.

        Args:
            file_path: Path to DOCX file

        Returns:
            Parsed content with text and metadata
        """
        try:
            doc = DocxDocument(file_path)
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]

            # Extract core properties as metadata
            metadata = {}
            if doc.core_properties:
                props = doc.core_properties
                metadata = {
                    "title": props.title or "",
                    "author": props.author or "",
                    "subject": props.subject or "",
                }

            return {
                "text": "\n\n".join(paragraphs),
                "page_count": None,  # DOCX doesn't have fixed pages
                "metadata": metadata,
            }

        except Exception as e:
            raise DocumentParseError(f"Failed to parse DOCX: {e}") from e

    async def _parse_txt(self, file_path: str) -> dict[str, Any]:
        """Parse plain text file.

        Args:
            file_path: Path to TXT file

        Returns:
            Parsed content with text and metadata
        """
        try:
            # Try UTF-8 first, fall back to latin-1
            try:
                with open(file_path, encoding="utf-8") as f:
                    text = f.read()
            except UnicodeDecodeError:
                with open(file_path, encoding="latin-1") as f:
                    text = f.read()

            return {
                "text": text,
                "page_count": None,
                "metadata": {},
            }

        except Exception as e:
            raise DocumentParseError(f"Failed to parse TXT: {e}") from e

