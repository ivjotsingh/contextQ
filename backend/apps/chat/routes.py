"""Chat routes - registers all chat endpoints."""

from fastapi import APIRouter

from apps.chat.handlers import (
    clear_chat_history,
    create_chat,
    delete_chat,
    get_chat_history,
    list_chats,
    stream_response,
)
from apps.chat.handlers.get_chat_history import ChatHistoryResponse
from apps.chat.handlers.list_chats import ChatListResponse

# Single router for all chat-related endpoints
router = APIRouter(tags=["Chat"])

# === /chat endpoints (streaming & history) ===

# POST /chat - Stream response
router.post("/chat")(stream_response)

# GET /chat/history - Get chat history
router.get("/chat/history", response_model=ChatHistoryResponse)(get_chat_history)

# DELETE /chat/history - Clear chat history
router.delete("/chat/history")(clear_chat_history)

# === /chats endpoints (CRUD for chat sessions) ===

# GET /chats - List chats for session
router.get("/chats", response_model=ChatListResponse)(list_chats)

# POST /chats - Create new chat
router.post("/chats")(create_chat)

# DELETE /chats/{chat_id} - Delete chat
router.delete("/chats/{chat_id}")(delete_chat)
