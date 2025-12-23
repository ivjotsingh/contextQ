"""Chat routes - registers all chat endpoints."""

from fastapi import APIRouter

from apps.chat.handlers import clear_chat_history, get_chat_history, send_message
from apps.chat.handlers.get_chat_history import ChatHistoryResponse

router = APIRouter(prefix="/chat", tags=["Chat"])

# POST /chat - Send message (streaming)
router.post("")(send_message)

# GET /chat/history - Get chat history
router.get("/history", response_model=ChatHistoryResponse)(get_chat_history)

# DELETE /chat/history - Clear chat history
router.delete("/history")(clear_chat_history)
