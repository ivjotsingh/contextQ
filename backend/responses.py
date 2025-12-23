"""Standardized response infrastructure for API endpoints.

Provides consistent response format with structured codes and messages.
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from fastapi.responses import JSONResponse


class ResponseCode(str, Enum):
    """Response codes for API responses.

    Ranges: 0xxx=Success, 1xxx=Client Error, 2xxx=Server Error, 3xxx=External Service
    """

    # Success codes
    SUCCESS = "0000"
    DOCUMENT_UPLOADED = "0002"
    DOCUMENT_DELETED = "0003"

    # Client errors
    VALIDATION_ERROR = "1000"
    UNSUPPORTED_FILE_TYPE = "1001"
    FILE_TOO_LARGE = "1002"
    DOCUMENT_NOT_FOUND = "1003"
    EMPTY_DOCUMENT = "1004"
    CORRUPTED_FILE = "1005"
    DUPLICATE_DOCUMENT = "1006"

    # Server errors
    INTERNAL_ERROR = "2000"
    EMBEDDING_FAILED = "2001"
    VECTOR_STORE_ERROR = "2002"

    # External service errors
    LLM_RATE_LIMIT = "3001"


# Response messages mapped to codes
RESPONSE_MESSAGES: dict[ResponseCode, str] = {
    ResponseCode.SUCCESS: "Operation completed successfully",
    ResponseCode.DOCUMENT_UPLOADED: "Document uploaded and processed successfully",
    ResponseCode.DOCUMENT_DELETED: "Document deleted successfully",
    ResponseCode.VALIDATION_ERROR: "Request validation failed",
    ResponseCode.UNSUPPORTED_FILE_TYPE: "Unsupported file type. Supported: PDF, DOCX, TXT",
    ResponseCode.FILE_TOO_LARGE: "File exceeds maximum allowed size",
    ResponseCode.DOCUMENT_NOT_FOUND: "Document not found",
    ResponseCode.EMPTY_DOCUMENT: "Document contains no extractable text",
    ResponseCode.CORRUPTED_FILE: "File appears corrupted",
    ResponseCode.DUPLICATE_DOCUMENT: "Document already processed",
    ResponseCode.INTERNAL_ERROR: "An internal error occurred",
    ResponseCode.EMBEDDING_FAILED: "Failed to generate embeddings",
    ResponseCode.VECTOR_STORE_ERROR: "Vector store operation failed",
    ResponseCode.LLM_RATE_LIMIT: "Rate limit exceeded. Please wait and retry",
}

# HTTP status codes for each response code
HTTP_STATUS_MAP: dict[ResponseCode, int] = {
    ResponseCode.SUCCESS: 200,
    ResponseCode.DOCUMENT_UPLOADED: 201,
    ResponseCode.DOCUMENT_DELETED: 200,
    ResponseCode.VALIDATION_ERROR: 422,
    ResponseCode.UNSUPPORTED_FILE_TYPE: 400,
    ResponseCode.FILE_TOO_LARGE: 413,
    ResponseCode.DOCUMENT_NOT_FOUND: 404,
    ResponseCode.EMPTY_DOCUMENT: 400,
    ResponseCode.CORRUPTED_FILE: 400,
    ResponseCode.DUPLICATE_DOCUMENT: 200,  # Idempotent success
    ResponseCode.INTERNAL_ERROR: 500,
    ResponseCode.EMBEDDING_FAILED: 500,
    ResponseCode.VECTOR_STORE_ERROR: 500,
    ResponseCode.LLM_RATE_LIMIT: 429,
}


def get_message(code: ResponseCode) -> str:
    """Get the message for a response code."""
    return RESPONSE_MESSAGES.get(code, "Unknown error")


def get_http_status(code: ResponseCode) -> int:
    """Get HTTP status code for a response code."""
    return HTTP_STATUS_MAP.get(code, 500)


def success_dict(
    code: ResponseCode,
    data: Any = None,
    custom_message: str | None = None,
    request_id: str | None = None,
) -> dict[str, Any]:
    """Build a standardized success response dictionary."""
    return {
        "code": code.value,
        "success": True,
        "message": custom_message or get_message(code),
        "timestamp": datetime.now(UTC).isoformat(),
        "request_id": request_id,
        "data": data,
    }


def error_dict(
    code: ResponseCode,
    custom_message: str | None = None,
    error_details: dict[str, Any] | None = None,
    request_id: str | None = None,
) -> dict[str, Any]:
    """Build a standardized error response dictionary."""
    return {
        "code": code.value,
        "success": False,
        "message": custom_message or get_message(code),
        "timestamp": datetime.now(UTC).isoformat(),
        "request_id": request_id,
        "error_details": error_details,
    }


# --- JSONResponse helpers ---


def success_response(
    code: ResponseCode,
    data: Any = None,
    request_id: str | None = None,
) -> JSONResponse:
    """Create a JSONResponse with success format."""
    return JSONResponse(
        content=success_dict(code, data, request_id=request_id),
        status_code=get_http_status(code),
    )


def error_response(
    code: ResponseCode,
    custom_message: str | None = None,
    request_id: str | None = None,
) -> JSONResponse:
    """Create a JSONResponse with error format."""
    return JSONResponse(
        content=error_dict(code, custom_message, request_id=request_id),
        status_code=get_http_status(code),
    )
