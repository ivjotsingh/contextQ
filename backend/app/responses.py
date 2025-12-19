"""Standardized response infrastructure for all API endpoints.

Provides consistent response format across all endpoints with:
- Structured response codes
- Centralized message management
- Type-safe response models
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ResponseCode(str, Enum):
    """4-digit hexadecimal response codes for all API responses.

    Code ranges:
    - 0xxx: Success codes
    - 1xxx: Client error codes
    - 2xxx: Server error codes
    - 3xxx: External service errors
    """

    # Success codes (0xxx)
    SUCCESS = "0000"
    HEALTH_CHECK_OK = "0001"
    DOCUMENT_UPLOADED = "0002"
    DOCUMENT_DELETED = "0003"
    DOCUMENTS_LISTED = "0004"
    CHAT_RESPONSE_GENERATED = "0005"

    # Client error codes (1xxx)
    VALIDATION_ERROR = "1000"
    UNSUPPORTED_FILE_TYPE = "1001"
    FILE_TOO_LARGE = "1002"
    DOCUMENT_NOT_FOUND = "1003"
    EMPTY_DOCUMENT = "1004"
    CORRUPTED_FILE = "1005"
    DUPLICATE_DOCUMENT = "1006"
    TOO_MANY_CHUNKS = "1007"
    INVALID_SESSION = "1008"
    MISSING_QUESTION = "1009"

    # Server error codes (2xxx)
    INTERNAL_ERROR = "2000"
    EMBEDDING_FAILED = "2001"
    VECTOR_STORE_ERROR = "2002"
    CACHE_ERROR = "2003"
    DOCUMENT_PARSE_ERROR = "2004"

    # External service errors (3xxx)
    LLM_ERROR = "3000"
    LLM_RATE_LIMIT = "3001"
    OPENAI_ERROR = "3002"
    QDRANT_ERROR = "3003"
    REDIS_ERROR = "3004"


class ResponseMessage:
    """Centralized response messages mapped to response codes."""

    MESSAGES: dict[ResponseCode, str] = {
        # Success messages
        ResponseCode.SUCCESS: "Operation completed successfully",
        ResponseCode.HEALTH_CHECK_OK: "Service is healthy and operational",
        ResponseCode.DOCUMENT_UPLOADED: "Document uploaded and processed successfully",
        ResponseCode.DOCUMENT_DELETED: "Document deleted successfully",
        ResponseCode.DOCUMENTS_LISTED: "Documents retrieved successfully",
        ResponseCode.CHAT_RESPONSE_GENERATED: "Response generated successfully",
        # Client error messages
        ResponseCode.VALIDATION_ERROR: "Request validation failed",
        ResponseCode.UNSUPPORTED_FILE_TYPE: (
            "Unsupported file type. Supported formats: PDF, DOCX, TXT"
        ),
        ResponseCode.FILE_TOO_LARGE: "File exceeds maximum allowed size",
        ResponseCode.DOCUMENT_NOT_FOUND: "Document not found",
        ResponseCode.EMPTY_DOCUMENT: "Document contains no extractable text",
        ResponseCode.CORRUPTED_FILE: (
            "File appears corrupted. Try re-saving from original application"
        ),
        ResponseCode.DUPLICATE_DOCUMENT: "Document already processed",
        ResponseCode.TOO_MANY_CHUNKS: "Document exceeds maximum chunk limit",
        ResponseCode.INVALID_SESSION: "Invalid or expired session",
        ResponseCode.MISSING_QUESTION: "Question is required",
        # Server error messages
        ResponseCode.INTERNAL_ERROR: "An internal error occurred",
        ResponseCode.EMBEDDING_FAILED: "Failed to generate embeddings",
        ResponseCode.VECTOR_STORE_ERROR: "Vector store operation failed",
        ResponseCode.CACHE_ERROR: "Cache operation failed",
        ResponseCode.DOCUMENT_PARSE_ERROR: "Failed to parse document",
        # External service error messages
        ResponseCode.LLM_ERROR: "LLM service error. Please try again",
        ResponseCode.LLM_RATE_LIMIT: "Rate limit exceeded. Please wait and retry",
        ResponseCode.OPENAI_ERROR: "OpenAI API error",
        ResponseCode.QDRANT_ERROR: "Vector database error",
        ResponseCode.REDIS_ERROR: "Cache service error",
    }

    @classmethod
    def get_message(cls, code: ResponseCode) -> str:
        """Get the message for a given response code."""
        return cls.MESSAGES.get(code, "Unknown error")


class StandardResponse(BaseModel):
    """Base standardized response model for all API endpoints."""

    code: str = Field(..., description="4-digit hexadecimal response code")
    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Human-readable response message")
    timestamp: str = Field(..., description="ISO timestamp of the response")
    request_id: str | None = Field(None, description="Request ID for tracing")


class SuccessResponse(StandardResponse):
    """Standardized success response with optional data payload."""

    success: bool = Field(default=True, description="Always true for success responses")
    data: Any = Field(None, description="Response data payload")


class ErrorResponse(StandardResponse):
    """Standardized error response with optional error details."""

    success: bool = Field(default=False, description="Always false for error responses")
    error_details: dict[str, Any] | None = Field(
        None, description="Additional error context"
    )


def create_success_response(
    code: ResponseCode,
    data: Any = None,
    custom_message: str | None = None,
    request_id: str | None = None,
) -> dict[str, Any]:
    """Create a standardized success response.

    Args:
        code: Response code from ResponseCode enum
        data: Optional data payload
        custom_message: Optional custom message (overrides default)
        request_id: Optional request ID for tracing

    Returns:
        Dictionary with standardized success response structure
    """
    return {
        "code": code.value,
        "success": True,
        "message": custom_message or ResponseMessage.get_message(code),
        "timestamp": datetime.now(UTC).isoformat(),
        "request_id": request_id,
        "data": data,
    }


def create_error_response(
    code: ResponseCode,
    custom_message: str | None = None,
    error_details: dict[str, Any] | None = None,
    request_id: str | None = None,
) -> dict[str, Any]:
    """Create a standardized error response.

    Args:
        code: Response code from ResponseCode enum
        custom_message: Optional custom message (overrides default)
        error_details: Optional additional error context
        request_id: Optional request ID for tracing

    Returns:
        Dictionary with standardized error response structure
    """
    return {
        "code": code.value,
        "success": False,
        "message": custom_message or ResponseMessage.get_message(code),
        "timestamp": datetime.now(UTC).isoformat(),
        "request_id": request_id,
        "error_details": error_details,
    }


# HTTP status code mapping for response codes
HTTP_STATUS_MAP: dict[ResponseCode, int] = {
    # Success codes -> 200
    ResponseCode.SUCCESS: 200,
    ResponseCode.HEALTH_CHECK_OK: 200,
    ResponseCode.DOCUMENT_UPLOADED: 201,
    ResponseCode.DOCUMENT_DELETED: 200,
    ResponseCode.DOCUMENTS_LISTED: 200,
    ResponseCode.CHAT_RESPONSE_GENERATED: 200,
    # Client errors -> 4xx
    ResponseCode.VALIDATION_ERROR: 422,
    ResponseCode.UNSUPPORTED_FILE_TYPE: 400,
    ResponseCode.FILE_TOO_LARGE: 413,
    ResponseCode.DOCUMENT_NOT_FOUND: 404,
    ResponseCode.EMPTY_DOCUMENT: 400,
    ResponseCode.CORRUPTED_FILE: 400,
    ResponseCode.DUPLICATE_DOCUMENT: 200,  # Idempotent success
    ResponseCode.TOO_MANY_CHUNKS: 413,
    ResponseCode.INVALID_SESSION: 401,
    ResponseCode.MISSING_QUESTION: 400,
    # Server errors -> 5xx
    ResponseCode.INTERNAL_ERROR: 500,
    ResponseCode.EMBEDDING_FAILED: 500,
    ResponseCode.VECTOR_STORE_ERROR: 500,
    ResponseCode.CACHE_ERROR: 500,
    ResponseCode.DOCUMENT_PARSE_ERROR: 500,
    # External service errors -> 5xx
    ResponseCode.LLM_ERROR: 503,
    ResponseCode.LLM_RATE_LIMIT: 429,
    ResponseCode.OPENAI_ERROR: 502,
    ResponseCode.QDRANT_ERROR: 502,
    ResponseCode.REDIS_ERROR: 502,
}


def get_http_status(code: ResponseCode) -> int:
    """Get HTTP status code for a response code."""
    return HTTP_STATUS_MAP.get(code, 500)

