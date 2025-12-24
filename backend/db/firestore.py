"""Firestore service for chat history persistence.

Stores chat messages in Firestore with chat-based subcollections.
- `chats/{chat_id}/messages/...` - Chat history per conversation
- session_id is used only for document filtering in Qdrant, not here
"""

import json
import logging
import os
from datetime import UTC, datetime
from typing import Any

import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1 import AsyncClient
from google.oauth2 import service_account

from config import get_settings

logger = logging.getLogger(__name__)


def _load_firebase_credentials(creds_value: str) -> dict:
    """Load Firebase credentials from JSON string, file path, or base64."""
    import base64

    if os.path.isfile(creds_value):
        with open(creds_value) as f:
            return json.load(f)

    try:
        return json.loads(creds_value)
    except json.JSONDecodeError:
        pass

    try:
        decoded = base64.b64decode(creds_value).decode("utf-8")
        return json.loads(decoded)
    except Exception:
        pass

    raise ValueError("FIREBASE_CREDENTIALS is not valid JSON, file path, or base64")


class FirestoreService:
    """Service for managing chat history in Firestore."""

    _initialized: bool = False
    _db: AsyncClient | None = None

    def __init__(self) -> None:
        """Initialize Firestore client (singleton pattern)."""
        if FirestoreService._initialized:
            self.db = FirestoreService._db
            return

        settings = get_settings()

        try:
            creds_dict = _load_firebase_credentials(settings.firebase_credentials)

            if not firebase_admin._apps:
                cred = credentials.Certificate(creds_dict)
                firebase_admin.initialize_app(cred)

            gcp_credentials = service_account.Credentials.from_service_account_info(
                creds_dict
            )

            FirestoreService._db = AsyncClient(
                project=creds_dict.get("project_id"),
                credentials=gcp_credentials,
            )
            self.db = FirestoreService._db

            FirestoreService._initialized = True
            logger.info("Firestore client initialized successfully")
        except Exception as e:
            logger.error("Failed to initialize Firestore: %s", e)
            raise

    # --- Chat Message Methods (use chat_id) ---

    async def add_message(
        self,
        chat_id: str,
        role: str,
        content: str,
        sources: list[dict[str, Any]] | None = None,
    ) -> str:
        """Add a message to chat history."""
        try:
            message_data = {
                "role": role,
                "content": content,
                "timestamp": datetime.now(UTC),
                "sources": sources or [],
            }

            doc_ref = (
                self.db.collection("chats")
                .document(chat_id)
                .collection("messages")
                .document()
            )

            await doc_ref.set(message_data)
            logger.debug("Added message to chat %s", chat_id)
            return doc_ref.id

        except Exception as e:
            logger.error("Failed to add message: %s", e)
            raise

    async def get_messages(self, chat_id: str, limit: int = 10) -> list[dict[str, Any]]:
        """Get recent messages from chat history."""
        try:
            messages_ref = (
                self.db.collection("chats")
                .document(chat_id)
                .collection("messages")
                .order_by("timestamp", direction=firestore.Query.DESCENDING)
                .limit(limit)
            )

            docs = await messages_ref.get()
            messages = []

            for doc in docs:
                data = doc.to_dict()
                data["id"] = doc.id
                if data.get("timestamp"):
                    data["timestamp"] = data["timestamp"].isoformat()
                messages.append(data)

            messages.reverse()
            return messages

        except Exception as e:
            logger.error("Failed to get messages: %s", e)
            raise

    async def get_message_count(self, chat_id: str) -> int:
        """Get total message count for a chat."""
        try:
            messages_ref = (
                self.db.collection("chats").document(chat_id).collection("messages")
            )
            count_query = messages_ref.count()
            result = await count_query.get()
            return result[0][0].value if result else 0

        except Exception as e:
            logger.error("Failed to get message count: %s", e)
            raise

    async def get_or_create_summary(self, chat_id: str) -> str | None:
        """Get existing summary for a chat."""
        try:
            chat_ref = self.db.collection("chats").document(chat_id)
            doc = await chat_ref.get()

            if doc.exists:
                data = doc.to_dict()
                return data.get("summary")

            return None

        except Exception as e:
            logger.error("Failed to get summary: %s", e)
            raise

    async def save_summary(self, chat_id: str, summary: str) -> None:
        """Save a conversation summary."""
        try:
            chat_ref = self.db.collection("chats").document(chat_id)
            await chat_ref.set(
                {"summary": summary, "summary_updated_at": datetime.now(UTC)},
                merge=True,
            )
            logger.info("Saved summary for chat %s", chat_id)

        except Exception as e:
            logger.error("Failed to save summary: %s", e)
            raise

    async def clear_history(self, chat_id: str) -> int:
        """Clear all messages for a chat."""
        try:
            messages_ref = (
                self.db.collection("chats").document(chat_id).collection("messages")
            )
            docs = await messages_ref.get()
            deleted_count = 0

            batch = self.db.batch()
            for doc in docs:
                batch.delete(doc.reference)
                deleted_count += 1

                if deleted_count % 500 == 0:
                    await batch.commit()
                    batch = self.db.batch()

            if deleted_count % 500 != 0:
                await batch.commit()

            chat_ref = self.db.collection("chats").document(chat_id)
            await chat_ref.set(
                {"summary": None, "summary_updated_at": None}, merge=True
            )

            logger.info("Cleared %d messages for chat %s", deleted_count, chat_id)
            return deleted_count

        except Exception as e:
            logger.error("Failed to clear history: %s", e)
            raise

    async def build_chat_context(self, chat_id: str, max_messages: int = 10) -> str:
        """Build chat context for LLM from history."""
        try:
            message_count = await self.get_message_count(chat_id)

            if message_count == 0:
                return ""

            messages = await self.get_messages(chat_id, limit=max_messages)

            if message_count <= max_messages:
                return self._format_messages_for_context(messages)

            summary = await self.get_or_create_summary(chat_id)

            context_parts = []
            if summary:
                context_parts.append(f"[Previous conversation summary]\n{summary}")

            context_parts.append(
                f"[Recent messages ({len(messages)} of {message_count} total)]"
            )
            context_parts.append(self._format_messages_for_context(messages))

            return "\n\n".join(context_parts)

        except Exception as e:
            logger.error("Failed to build chat context: %s", e)
            raise

    def _format_messages_for_context(self, messages: list[dict[str, Any]]) -> str:
        """Format messages into a context string."""
        formatted = []
        for msg in messages:
            role = "User" if msg["role"] == "user" else "Assistant"
            content = msg["content"]
            if len(content) > 500:
                content = content[:500] + "..."
            formatted.append(f"{role}: {content}")

        return "\n".join(formatted)

    # --- Chat Management Methods ---

    async def get_chats(self, session_id: str, limit: int = 20) -> list[dict[str, Any]]:
        """Get all chats for a session (browser)."""
        try:
            chats_ref = (
                self.db.collection("chats")
                .where("session_id", "==", session_id)
                .order_by("last_activity", direction=firestore.Query.DESCENDING)
                .limit(limit)
            )

            docs = await chats_ref.get()
            chats = []

            for doc in docs:
                data = doc.to_dict()
                chat = {
                    "id": doc.id,
                    "title": data.get("title", "New Chat"),
                    "last_activity": data.get("last_activity"),
                    "message_count": data.get("message_count", 0),
                }
                if chat["last_activity"]:
                    chat["last_activity"] = chat["last_activity"].isoformat()
                chats.append(chat)

            return chats

        except Exception as e:
            logger.error("Failed to get chats: %s", e)
            raise

    async def create_chat(
        self, chat_id: str, session_id: str, title: str = "New Chat"
    ) -> dict[str, Any]:
        """Create a new chat for a session."""
        try:
            chat_ref = self.db.collection("chats").document(chat_id)
            chat_data = {
                "session_id": session_id,
                "title": title,
                "created_at": datetime.now(UTC),
                "last_activity": datetime.now(UTC),
                "message_count": 0,
            }
            await chat_ref.set(chat_data, merge=True)

            return {
                "id": chat_id,
                "title": title,
                "last_activity": chat_data["last_activity"].isoformat(),
                "message_count": 0,
            }

        except Exception as e:
            logger.error("Failed to create chat: %s", e)
            raise

    async def update_chat_activity(
        self, chat_id: str, first_message: str | None = None
    ) -> None:
        """Update chat's last activity and optionally set title."""
        try:
            chat_ref = self.db.collection("chats").document(chat_id)
            update_data: dict[str, Any] = {"last_activity": datetime.now(UTC)}

            doc = await chat_ref.get()
            if doc.exists:
                data = doc.to_dict()
                update_data["message_count"] = (data.get("message_count", 0) or 0) + 1

                if first_message and data.get("title") == "New Chat":
                    title = first_message[:50]
                    if len(first_message) > 50:
                        title += "..."
                    update_data["title"] = title
            else:
                update_data["message_count"] = 1
                if first_message:
                    title = first_message[:50]
                    if len(first_message) > 50:
                        title += "..."
                    update_data["title"] = title

            await chat_ref.set(update_data, merge=True)

        except Exception as e:
            logger.error("Failed to update chat activity: %s", e)
            raise

    async def delete_chat(self, chat_id: str) -> bool:
        """Delete a chat and all its messages."""
        try:
            await self.clear_history(chat_id)
            chat_ref = self.db.collection("chats").document(chat_id)
            await chat_ref.delete()

            logger.info("Deleted chat %s", chat_id)
            return True

        except Exception as e:
            logger.error("Failed to delete chat: %s", e)
            return False

    async def health_check(self) -> dict[str, Any]:
        """Check Firestore connection health."""
        import time

        start = time.time()
        try:
            test_ref = self.db.collection("_health_check").document("test")
            await test_ref.set({"timestamp": datetime.now(UTC)})
            await test_ref.get()

            latency = (time.time() - start) * 1000
            return {"status": "healthy", "latency_ms": round(latency, 2)}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}


def get_firestore_service() -> FirestoreService:
    """Get Firestore service singleton."""
    return FirestoreService()
