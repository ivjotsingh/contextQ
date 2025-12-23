"""Main API router that registers all sub-routers.

This module aggregates all domain-specific routers into a single router
that gets mounted in main.py.
"""

from fastapi import APIRouter

from apps.chat import router as chat_router
from apps.documents import router as documents_router
from apps.health import router as health_router
from apps.sessions import router as sessions_router

# Create main API router
router = APIRouter()

# Register all domain routers
router.include_router(health_router)
router.include_router(documents_router)
router.include_router(chat_router)
router.include_router(sessions_router)
