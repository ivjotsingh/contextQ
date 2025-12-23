"""GET /health - Check health of all services."""

from datetime import UTC, datetime

from pydantic import BaseModel, Field

from config import get_settings
from services import get_vector_store

# --- Response Schemas ---


class ServiceStatus(BaseModel):
    """Status of an individual service."""

    name: str
    status: str = Field(..., description="healthy, degraded, or unhealthy")
    latency_ms: float | None = Field(None, description="Response time in ms")
    error: str | None = Field(None, description="Error message if unhealthy")


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Overall status: healthy, degraded, unhealthy")
    version: str = Field(..., description="Application version")
    environment: str = Field(..., description="Environment name")
    services: list[ServiceStatus] = Field(
        ..., description="Individual service statuses"
    )
    timestamp: datetime


# --- Handler ---


async def check_health() -> HealthResponse:
    """Check health of all services."""
    settings = get_settings()
    vector_store = get_vector_store()

    qdrant_health = await vector_store.health_check()

    services = [
        ServiceStatus(
            name="qdrant",
            status=qdrant_health["status"],
            latency_ms=qdrant_health.get("latency_ms"),
            error=qdrant_health.get("error"),
        ),
    ]

    statuses = [s.status for s in services]
    if all(s == "healthy" for s in statuses):
        overall = "healthy"
    elif any(s == "unhealthy" for s in statuses):
        overall = "unhealthy"
    else:
        overall = "degraded"

    return HealthResponse(
        status=overall,
        version="0.1.0",
        environment=settings.environment,
        services=services,
        timestamp=datetime.now(UTC),
    )
