"""Configuration and settings for ContextQ application.

Uses Pydantic Settings for fail-fast validation on startup.
All required environment variables are validated at import time.
"""

from functools import lru_cache
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Raises ValidationError on startup if required variables are missing.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # API Keys (required)
    anthropic_api_key: str = Field(..., description="Anthropic API key for Claude")
    voyage_api_key: str = Field(..., description="Voyage AI API key for embeddings")

    # Qdrant Configuration (required)
    qdrant_url: str = Field(..., description="Qdrant Cloud URL")
    qdrant_api_key: str = Field(..., description="Qdrant API key")
    qdrant_collection: str = Field(
        default="documents", description="Qdrant collection name"
    )

    # Redis Configuration (required)
    redis_url: str = Field(..., description="Upstash Redis URL")

    # Application Settings
    environment: str = Field(default="development", description="Environment name")
    debug: bool = Field(default=False, description="Debug mode")

    # Document Processing Limits
    max_file_size_mb: int = Field(default=10, description="Max upload size in MB")
    max_chunks_per_doc: int = Field(default=500, description="Max chunks per document")
    chunk_size: int = Field(default=1500, description="Target chunk size in chars")
    chunk_overlap: int = Field(default=200, description="Chunk overlap in chars")

    # RAG Settings
    embedding_model: str = Field(
        default="voyage-3-lite", description="Voyage AI embedding model"
    )
    embedding_dimensions: int = Field(
        default=512, description="Embedding vector dimensions (voyage-3-lite: 512)"
    )
    llm_model: str = Field(
        default="claude-sonnet-4-20250514", description="Claude model for generation"
    )
    retrieval_top_k: int = Field(default=5, description="Number of chunks to retrieve")
    llm_temperature: float = Field(
        default=0.2, description="LLM temperature for factual responses"
    )
    llm_max_tokens: int = Field(default=2048, description="Max tokens for generation")

    # Cache TTLs (in seconds)
    embedding_cache_ttl: int = Field(
        default=86400, description="Embedding cache TTL (24h)"
    )
    response_cache_ttl: int = Field(
        default=3600, description="Response cache TTL (1h)"
    )
    session_ttl: int = Field(default=86400, description="Session TTL (24h)")

    # Embedding Batch Settings
    embedding_batch_size: int = Field(
        default=64, description="Batch size for embedding API calls"
    )

    @field_validator("anthropic_api_key", "voyage_api_key", "qdrant_api_key")
    @classmethod
    def validate_api_key_not_empty(cls, v: str, info) -> str:
        """Ensure API keys are not empty strings."""
        if not v or not v.strip():
            raise ValueError(f"{info.field_name} cannot be empty")
        return v.strip()

    @property
    def max_file_size_bytes(self) -> int:
        """Get max file size in bytes."""
        return self.max_file_size_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.

    Uses lru_cache to ensure settings are only loaded once.
    """
    return Settings()


# CORS Configuration
CORS_CONFIG: dict[str, Any] = {
    "allow_origins": [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    "allow_credentials": True,
    "allow_methods": ["GET", "POST", "DELETE", "OPTIONS"],
    "allow_headers": ["*"],
    "expose_headers": ["*"],
    "max_age": 600,
}

# FastAPI App Configuration
APP_CONFIG: dict[str, Any] = {
    "title": "ContextQ",
    "description": (
        "RAG-powered document chat system with transparent source attribution. "
        "Upload documents and ask questions with grounded answers."
    ),
    "version": "0.1.0",
    "docs_url": "/api/docs",
    "redoc_url": "/api/redoc",
    "openapi_url": "/api/openapi.json",
    "openapi_tags": [
        {
            "name": "Health",
            "description": "Health check and service status",
        },
        {
            "name": "Documents",
            "description": "Document upload and management",
        },
        {
            "name": "Chat",
            "description": "RAG-powered document Q&A",
        },
    ],
}


def get_app_config() -> dict[str, Any]:
    """Get FastAPI application configuration."""
    return APP_CONFIG.copy()


def get_cors_config() -> dict[str, Any]:
    """Get CORS middleware configuration."""
    return CORS_CONFIG.copy()

