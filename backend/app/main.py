"""Main FastAPI application for ContextQ.

Entry point for the application. Configures:
- FastAPI app with settings
- CORS middleware
- Exception handlers
- Route registration
- Static file serving for frontend
"""

import logging
import os
import uuid
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.routes import router as api_router
from app.config import get_app_config, get_cors_config, get_settings
from app.responses import ResponseCode, create_error_response
from app.utils.helpers import setup_logging

# Path to frontend build
FRONTEND_DIR = Path(__file__).parent.parent.parent / "frontend" / "dist"

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Create FastAPI app
app_config = get_app_config()
app = FastAPI(**app_config)

# Add CORS middleware
cors_config = get_cors_config()
app.add_middleware(CORSMiddleware, **cors_config)


# =============================================================================
# Middleware
# =============================================================================


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Add request ID to all requests for tracing."""
    request_id = str(uuid.uuid4())[:8]
    request.state.request_id = request_id

    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id

    return response


# =============================================================================
# Exception Handlers
# =============================================================================


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Handle Pydantic validation errors."""
    request_id = getattr(request.state, "request_id", None)

    # Extract first error for cleaner message
    first_error = exc.errors()[0] if exc.errors() else {}
    field_name = first_error.get("loc", ["unknown"])[-1]

    error_response = create_error_response(
        code=ResponseCode.VALIDATION_ERROR,
        custom_message=f"Validation failed for field '{field_name}'",
        error_details={"validation_errors": exc.errors()},
        request_id=request_id,
    )

    return JSONResponse(status_code=422, content=error_response)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    """Handle HTTP exceptions."""
    request_id = getattr(request.state, "request_id", None)

    # If detail is already a standardized response, return as-is
    if isinstance(exc.detail, dict) and "code" in exc.detail:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)

    # Map status codes to response codes
    code_map = {
        404: ResponseCode.DOCUMENT_NOT_FOUND,
        405: ResponseCode.VALIDATION_ERROR,
        413: ResponseCode.FILE_TOO_LARGE,
        429: ResponseCode.LLM_RATE_LIMIT,
    }

    response_code = code_map.get(exc.status_code, ResponseCode.INTERNAL_ERROR)

    error_response = create_error_response(
        code=response_code,
        custom_message=str(exc.detail),
        request_id=request_id,
    )

    return JSONResponse(status_code=exc.status_code, content=error_response)


@app.exception_handler(Exception)
async def general_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Handle unhandled exceptions."""
    request_id = getattr(request.state, "request_id", None)

    logger.exception("Unhandled exception: %s", exc)

    error_response = create_error_response(
        code=ResponseCode.INTERNAL_ERROR,
        custom_message="An unexpected error occurred",
        error_details={
            "exception_type": type(exc).__name__,
        },
        request_id=request_id,
    )

    return JSONResponse(status_code=500, content=error_response)


# =============================================================================
# Routes
# =============================================================================

# Include API routes
app.include_router(api_router, prefix="/api")


# Serve frontend static files if available
if FRONTEND_DIR.exists():
    # Mount static assets
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="assets")
    
    # Serve index.html for all non-API routes (SPA routing)
    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_frontend(full_path: str):
        """Serve frontend SPA."""
        # Don't serve for API routes
        if full_path.startswith("api/"):
            raise StarletteHTTPException(status_code=404)
        
        # Try to serve the exact file
        file_path = FRONTEND_DIR / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        
        # Fall back to index.html for SPA routing
        return FileResponse(FRONTEND_DIR / "index.html")
else:
    # Development mode - just show API info
    @app.get("/", include_in_schema=False)
    async def root():
        """Root endpoint - shows API info in development."""
        return {
            "name": "ContextQ",
            "description": "RAG-powered document chat system",
            "docs": "/api/docs",
            "health": "/api/health",
            "note": "Frontend not built. Run 'npm run build' in frontend directory.",
        }


# =============================================================================
# Startup/Shutdown
# =============================================================================


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    logger.info("Starting ContextQ...")

    # Validate settings (will raise if missing required env vars)
    try:
        settings = get_settings()
        logger.info("Environment: %s", settings.environment)
        logger.info("LLM Model: %s", settings.llm_model)
        logger.info("Embedding Model: %s", settings.embedding_model)
    except Exception as e:
        logger.error("Configuration error: %s", e)
        raise

    logger.info("ContextQ started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down ContextQ...")


# =============================================================================
# Development Server
# =============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )

