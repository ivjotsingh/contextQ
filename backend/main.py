"""Main FastAPI application for ContextQ.

Entry point for the application. Configures:
- FastAPI app with settings
- CORS middleware
- Exception handlers
- Route registration
- Static file serving for frontend
"""

import logging
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from config import get_app_config, get_cors_config, get_settings, setup_logging
from dependencies import (
    get_embedding_service,
    get_firestore_service,
    get_vector_store,
)
from middleware import RateLimitMiddleware
from responses import ResponseCode, error_dict
from router import router as api_router

# Path to frontend build
FRONTEND_DIR = Path(__file__).parent.parent / "frontend" / "dist"

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


# =============================================================================
# Lifespan Management
# =============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan - startup and shutdown."""
    # Startup
    logger.info("Starting ContextQ...")

    try:
        settings = get_settings()
        logger.info("Environment: %s", settings.environment)
        logger.info("LLM Model: %s", settings.llm_model)
        logger.info("Embedding Model: %s", settings.embedding_model)

        # Validate critical services
        logger.info("Validating services...")

        # Test vector store connection
        vector_store = get_vector_store()
        vector_health = await vector_store.health_check()
        if vector_health.get("status") != "healthy":
            logger.error("Vector store unhealthy: %s", vector_health)
            raise RuntimeError(f"Vector store health check failed: {vector_health}")
        logger.info(
            "✓ Vector store connected (latency: %sms)", vector_health.get("latency_ms")
        )

        # Test Firestore connection
        firestore = get_firestore_service()
        firestore_health = await firestore.health_check()
        if firestore_health.get("status") != "healthy":
            logger.error("Firestore unhealthy: %s", firestore_health)
            raise RuntimeError(f"Firestore health check failed: {firestore_health}")
        logger.info(
            "✓ Firestore connected (latency: %sms)", firestore_health.get("latency_ms")
        )

        # Test embedding service (validates API key)
        embedding_service = get_embedding_service()
        try:
            await embedding_service.embed_text("test")
            logger.info("✓ Embedding service validated")
        except Exception as e:
            logger.error("Embedding service validation failed: %s", e)
            raise RuntimeError(f"Embedding service validation failed: {e}")

        logger.info("ContextQ started successfully")

    except Exception as e:
        logger.error("Startup validation failed: %s", e)
        raise

    yield

    # Shutdown
    logger.info("Shutting down ContextQ...")


# Create FastAPI app with lifespan
app_config = get_app_config()
app = FastAPI(lifespan=lifespan, **app_config)

# Add CORS middleware
cors_config = get_cors_config()
app.add_middleware(CORSMiddleware, **cors_config)

# Add rate limiting middleware (protects LLM endpoints)
app.add_middleware(RateLimitMiddleware)


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

    first_error = exc.errors()[0] if exc.errors() else {}
    field_name = first_error.get("loc", ["unknown"])[-1]

    error_response = error_dict(
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

    if isinstance(exc.detail, dict) and "code" in exc.detail:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)

    code_map = {
        404: ResponseCode.DOCUMENT_NOT_FOUND,
        405: ResponseCode.VALIDATION_ERROR,
        413: ResponseCode.FILE_TOO_LARGE,
        429: ResponseCode.LLM_RATE_LIMIT,
    }

    response_code = code_map.get(exc.status_code, ResponseCode.INTERNAL_ERROR)

    error_response = error_dict(
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

    error_response = error_dict(
        code=ResponseCode.INTERNAL_ERROR,
        custom_message="An unexpected error occurred",
        error_details={"exception_type": type(exc).__name__},
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
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_frontend(full_path: str):
        """Serve frontend SPA."""
        if full_path.startswith("api/"):
            raise StarletteHTTPException(status_code=404)

        file_path = FRONTEND_DIR / full_path
        if file_path.is_file():
            return FileResponse(file_path)

        return FileResponse(FRONTEND_DIR / "index.html")
else:

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
# Development Server
# =============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
