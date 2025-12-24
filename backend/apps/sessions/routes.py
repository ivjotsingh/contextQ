"""Chat routes - now handles chats within a session."""

from fastapi import APIRouter

from apps.sessions.handlers.create_session import create_chat
from apps.sessions.handlers.delete_session import delete_chat
from apps.sessions.handlers.list_sessions import ChatListResponse, list_chats

router = APIRouter(prefix="/chats", tags=["Chats"])

# GET /chats - List chats for session
router.get("", response_model=ChatListResponse)(list_chats)

# POST /chats - Create new chat
router.post("")(create_chat)

# DELETE /chats/{chat_id} - Delete chat
router.delete("/{chat_id}")(delete_chat)
