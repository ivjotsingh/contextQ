"""Chat history management for RAG conversations.

Handles message persistence, context building, and summary generation.
"""

import logging
from typing import Any

from config import Settings
from db import FirestoreService
from services.llm import LLMClient

logger = logging.getLogger(__name__)


class ChatHistoryManager:
    """Manages chat history persistence and context building."""

    def __init__(
        self,
        firestore_service: FirestoreService | None,
        llm_client: LLMClient,
        settings: Settings,
    ) -> None:
        """Initialize chat history manager.

        Args:
            firestore_service: Firestore service for persistence (can be None).
            llm_client: LLM client for summary generation.
            settings: Application settings.
        """
        self.firestore = firestore_service
        self.llm_client = llm_client
        self.settings = settings

    async def get_context_and_save_user_message(
        self,
        session_id: str,
        question: str,
    ) -> str:
        """Get chat history context and save user message.

        Args:
            session_id: Session identifier.
            question: User's question to save.

        Returns:
            Formatted chat history context string, empty if no history.
        """
        if not self.firestore:
            return ""

        chat_history = await self.firestore.build_chat_context(
            session_id,
            max_messages=self.settings.chat_history_max_messages,
        )
        await self.firestore.add_message(
            session_id=session_id,
            role="user",
            content=question,
        )
        await self.firestore.update_session_activity(session_id, first_message=question)
        return chat_history

    async def save_assistant_message(
        self,
        session_id: str,
        content: str,
        sources: list[dict[str, Any]] | None = None,
    ) -> None:
        """Save assistant message to history.

        Args:
            session_id: Session identifier.
            content: Assistant's response content.
            sources: Optional list of source passages used.
        """
        if not self.firestore:
            return

        await self.firestore.add_message(
            session_id=session_id,
            role="assistant",
            content=content,
            sources=sources,
        )

    async def maybe_generate_summary(self, session_id: str) -> None:
        """Generate conversation summary if message count exceeds threshold.

        Summaries are generated periodically to help with long conversations.

        Args:
            session_id: Session identifier.
        """
        if not self.firestore:
            return

        try:
            message_count = await self.firestore.get_message_count(session_id)
            threshold = self.settings.summary_trigger_threshold
            interval = self.settings.summary_trigger_interval

            # Generate summary after threshold, then every interval messages
            if message_count > threshold and message_count % interval == 1:
                logger.info(
                    "Generating conversation summary for session %s (%d messages)",
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

                summary_prompt = f"""Summarize this conversation concisely, capturing the main topics discussed and key information exchanged. Keep it brief (2-3 sentences max).

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
            # Summary generation is non-critical, log and continue
            logger.warning("Failed to generate summary: %s", e)

