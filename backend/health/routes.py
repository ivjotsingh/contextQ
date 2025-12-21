"""Health routes - registers all health endpoints."""

from fastapi import APIRouter

from health.handlers import check_health
from health.handlers.check_health import HealthResponse

router = APIRouter(prefix="/health", tags=["Health"])

# GET /health - Health check
router.get("", response_model=HealthResponse)(check_health)
