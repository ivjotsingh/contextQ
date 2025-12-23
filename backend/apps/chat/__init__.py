"""Chat module - message handling and history."""

from apps.chat.chat_history import ChatHistoryManager
from apps.chat.routes import router

__all__ = ["router", "ChatHistoryManager"]
