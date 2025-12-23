"""Health routes - registers all health endpoints."""

from fastapi import APIRouter

from apps.health.handlers import check_health
from apps.health.handlers.check_health import HealthResponse

router = APIRouter(prefix="/health", tags=["Health"])

# GET /health - Health check
router.get("", response_model=HealthResponse)(check_health)
