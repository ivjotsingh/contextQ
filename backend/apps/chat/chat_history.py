"""Chat history management for conversations.

Handles message persistence, context building, and summary generation.
All methods are resilient - failures are logged but don't block the main flow.
"""

import logging
from typing import Any

from config import Settings
from db import FirestoreService
from llm.service import LLMService as LLMClient

logger = logging.getLogger(__name__)


class ChatHistoryManager:
    """Manages chat history persistence and context building.

    All methods are designed to be resilient - persistence failures
    are logged but don't block the main chat response.
    """

    def __init__(
        self,
        firestore_service: FirestoreService | None,
        llm_client: LLMClient,
        settings: Settings,
    ) -> None:
        """Initialize chat history manager."""
        self.firestore = firestore_service
        self.llm_client = llm_client
        self.settings = settings

    async def get_context(self, session_id: str) -> str:
        """Get formatted chat history context for a session.

        Returns:
            Formatted chat history context string, empty if unavailable.
        """
        if not self.firestore:
            return ""

        try:
            return await self.firestore.build_chat_context(
                session_id,
                max_messages=self.settings.chat_history_max_messages,
            )
        except Exception as e:
            logger.warning("Failed to get chat context for %s: %s", session_id, e)
            return ""  # Continue without history

    async def save_user_message(self, session_id: str, content: str) -> None:
        """Save user message to history.

        Non-blocking - failures are logged but don't raise.
        """
        if not self.firestore:
            return

        try:
            await self.firestore.add_message(
                session_id=session_id,
                role="user",
                content=content,
            )
            await self.firestore.update_session_activity(
                session_id, first_message=content
            )
        except Exception as e:
            logger.warning("Failed to save user message for %s: %s", session_id, e)

    async def save_assistant_message(
        self,
        session_id: str,
        content: str,
        sources: list[dict[str, Any]] | None = None,
    ) -> None:
        """Save assistant message to history.

        Non-blocking - failures are logged but don't raise.
        """
        if not self.firestore:
            return

        try:
            await self.firestore.add_message(
                session_id=session_id,
                role="assistant",
                content=content,
                sources=sources,
            )
        except Exception as e:
            logger.warning("Failed to save assistant message for %s: %s", session_id, e)

    async def maybe_generate_summary(self, session_id: str) -> None:
        """Generate conversation summary if message count exceeds threshold.

        Non-blocking - failures are logged but don't raise.
        """
        if not self.firestore:
            return

        try:
            message_count = await self.firestore.get_message_count(session_id)
            threshold = self.settings.summary_trigger_threshold
            interval = self.settings.summary_trigger_interval

            if message_count > threshold and message_count % interval == 1:
                logger.info(
                    "Generating summary for session %s (%d messages)",
                    session_id,
                    message_count,
                )

                messages = await self.firestore.get_messages(session_id, limit=20)
                if not messages:
                    return

                conversation_text = "\n".join(
                    f"{msg['role'].capitalize()}: {msg['content'][:300]}"
                    for msg in messages
                )

                summary_prompt = f"""Summarize this conversation concisely (2-3 sentences max).

CONVERSATION:
{conversation_text}

SUMMARY:"""

                summary = await self.llm_client.generate(
                    user_message=summary_prompt,
                    system_prompt="You are a helpful assistant that summarizes conversations.",
                    temperature=0.3,
                    max_tokens=200,
                )

                await self.firestore.save_summary(session_id, summary)
                logger.info("Generated summary for session %s", session_id)

        except Exception as e:
            logger.warning("Failed to generate summary for %s: %s", session_id, e)
