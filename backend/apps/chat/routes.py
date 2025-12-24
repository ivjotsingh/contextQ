"""Chat routes - registers all chat endpoints."""

from fastapi import APIRouter

from apps.chat.handlers import clear_chat_history, get_chat_history, stream_response
from apps.chat.handlers.get_chat_history import ChatHistoryResponse

router = APIRouter(prefix="/chat", tags=["Chat"])

# POST /chat - Stream response
router.post("")(stream_response)

# GET /chat/history - Get chat history
router.get("/history", response_model=ChatHistoryResponse)(get_chat_history)

# DELETE /chat/history - Clear chat history
router.delete("/history")(clear_chat_history)
