"""Chat routes - registers all chat endpoints."""

from fastapi import APIRouter

from chat.handlers import send_message, get_chat_history, clear_chat_history
from chat.handlers.get_chat_history import ChatHistoryResponse

router = APIRouter(prefix="/chat", tags=["Chat"])

# POST /chat - Send message (streaming)
router.post("")(send_message)

# GET /chat/history - Get chat history
router.get("/history", response_model=ChatHistoryResponse)(get_chat_history)

# DELETE /chat/history - Clear chat history
router.delete("/history")(clear_chat_history)

