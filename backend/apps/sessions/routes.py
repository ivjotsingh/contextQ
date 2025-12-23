"""Session routes - registers all session endpoints."""

from fastapi import APIRouter

from apps.sessions.handlers import (
    create_session,
    delete_session,
    list_sessions,
    switch_session,
)
from apps.sessions.handlers.list_sessions import SessionListResponse

router = APIRouter(prefix="/sessions", tags=["Sessions"])

# GET /sessions - List sessions
router.get("", response_model=SessionListResponse)(list_sessions)

# POST /sessions - Create session
router.post("")(create_session)

# PUT /sessions/{target_session_id}/switch - Switch session
router.put("/{target_session_id}/switch")(switch_session)

# DELETE /sessions/{target_session_id} - Delete session
router.delete("/{target_session_id}")(delete_session)
