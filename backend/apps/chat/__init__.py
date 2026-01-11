"""Chat module - handles all chat-related endpoints.

Endpoints:
- POST /chat - Stream response (SSE)
- GET /chat/history - Get chat history
- DELETE /chat/history - Clear chat history
- GET /chats - List chats for session
- POST /chats - Create new chat
- DELETE /chats/{chat_id} - Delete chat
"""

from apps.chat.routes import router

__all__ = ["router"]
