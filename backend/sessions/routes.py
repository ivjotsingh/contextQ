"""Session routes - registers all session endpoints."""

from fastapi import APIRouter

from sessions.handlers import list_sessions, create_session, switch_session, delete_session
from sessions.handlers.list_sessions import SessionListResponse

router = APIRouter(prefix="/sessions", tags=["Sessions"])

# GET /sessions - List sessions
router.get("", response_model=SessionListResponse)(list_sessions)

# POST /sessions - Create session
router.post("")(create_session)

# PUT /sessions/{target_session_id}/switch - Switch session
router.put("/{target_session_id}/switch")(switch_session)

# DELETE /sessions/{target_session_id} - Delete session
router.delete("/{target_session_id}")(delete_session)
