"""Firestore service for chat history persistence.

Stores chat messages in Firestore with session-based subcollections.
Implements summarization for conversations exceeding 10 messages.
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
    """Load Firebase credentials from JSON string, file path, or base64.

    Args:
        creds_value: Either a JSON string, file path, or base64-encoded JSON

    Returns:
        Parsed credentials dictionary
    """
    import base64

    # Check if it's a file path
    if os.path.isfile(creds_value):
        logger.info("Loading Firebase credentials from file: %s", creds_value)
        with open(creds_value) as f:
            return json.load(f)

    # Try to parse as JSON string
    try:
        return json.loads(creds_value)
    except json.JSONDecodeError:
        pass

    # Try to decode as base64
    try:
        decoded = base64.b64decode(creds_value).decode("utf-8")
        return json.loads(decoded)
    except Exception:
        pass

    raise ValueError(
        "FIREBASE_CREDENTIALS is not valid JSON, file path, or base64-encoded JSON"
    )


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
            # Load credentials
            creds_dict = _load_firebase_credentials(settings.firebase_credentials)

            # Initialize firebase_admin if not already done
            if not firebase_admin._apps:
                cred = credentials.Certificate(creds_dict)
                firebase_admin.initialize_app(cred)

            # Create google-auth credentials for AsyncClient
            gcp_credentials = service_account.Credentials.from_service_account_info(
                creds_dict
            )

            # Create AsyncClient with explicit credentials and project
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

    async def add_message(
        self,
        session_id: str,
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
                self.db.collection("sessions")
                .document(session_id)
                .collection("messages")
                .document()
            )

            await doc_ref.set(message_data)
            logger.debug("Added message to session %s", session_id)
            return doc_ref.id

        except Exception as e:
            logger.error("Failed to add message: %s", e)
            raise

    async def get_messages(
        self, session_id: str, limit: int = 10
    ) -> list[dict[str, Any]]:
        """Get recent messages from chat history."""
        try:
            messages_ref = (
                self.db.collection("sessions")
                .document(session_id)
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
            raise  # Don't swallow errors

    async def get_message_count(self, session_id: str) -> int:
        """Get total message count for a session."""
        try:
            messages_ref = (
                self.db.collection("sessions")
                .document(session_id)
                .collection("messages")
            )
            count_query = messages_ref.count()
            result = await count_query.get()
            return result[0][0].value if result else 0

        except Exception as e:
            logger.error("Failed to get message count: %s", e)
            raise  # Don't swallow errors

    async def get_or_create_summary(self, session_id: str) -> str | None:
        """Get existing summary for a session."""
        try:
            session_ref = self.db.collection("sessions").document(session_id)
            doc = await session_ref.get()

            if doc.exists:
                data = doc.to_dict()
                return data.get("summary")

            return None

        except Exception as e:
            logger.error("Failed to get summary: %s", e)
            raise  # Don't swallow errors

    async def save_summary(self, session_id: str, summary: str) -> None:
        """Save a conversation summary."""
        try:
            session_ref = self.db.collection("sessions").document(session_id)
            await session_ref.set(
                {"summary": summary, "summary_updated_at": datetime.now(UTC)},
                merge=True,
            )
            logger.info("Saved summary for session %s", session_id)

        except Exception as e:
            logger.error("Failed to save summary: %s", e)
            raise

    async def clear_history(self, session_id: str) -> int:
        """Clear all messages for a session."""
        try:
            messages_ref = (
                self.db.collection("sessions")
                .document(session_id)
                .collection("messages")
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

            session_ref = self.db.collection("sessions").document(session_id)
            await session_ref.set(
                {"summary": None, "summary_updated_at": None}, merge=True
            )

            logger.info("Cleared %d messages for session %s", deleted_count, session_id)
            return deleted_count

        except Exception as e:
            logger.error("Failed to clear history: %s", e)
            raise

    async def build_chat_context(self, session_id: str, max_messages: int = 10) -> str:
        """Build chat context for LLM from history."""
        try:
            message_count = await self.get_message_count(session_id)

            if message_count == 0:
                return ""

            messages = await self.get_messages(session_id, limit=max_messages)

            if message_count <= max_messages:
                return self._format_messages_for_context(messages)

            summary = await self.get_or_create_summary(session_id)

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
            raise  # Don't swallow errors

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

    async def get_sessions(self, limit: int = 20) -> list[dict[str, Any]]:
        """Get all sessions with their metadata."""
        try:
            sessions_ref = (
                self.db.collection("sessions")
                .order_by("last_activity", direction=firestore.Query.DESCENDING)
                .limit(limit)
            )

            docs = await sessions_ref.get()
            sessions = []

            for doc in docs:
                data = doc.to_dict()
                session = {
                    "id": doc.id,
                    "title": data.get("title", "New Chat"),
                    "last_activity": data.get("last_activity"),
                    "message_count": data.get("message_count", 0),
                }
                if session["last_activity"]:
                    session["last_activity"] = session["last_activity"].isoformat()
                sessions.append(session)

            return sessions

        except Exception as e:
            logger.error("Failed to get sessions: %s", e)
            raise  # Don't swallow errors

    async def create_session(
        self, session_id: str, title: str = "New Chat"
    ) -> dict[str, Any]:
        """Create a new session."""
        try:
            session_ref = self.db.collection("sessions").document(session_id)
            session_data = {
                "title": title,
                "created_at": datetime.now(UTC),
                "last_activity": datetime.now(UTC),
                "message_count": 0,
            }
            await session_ref.set(session_data, merge=True)

            return {
                "id": session_id,
                "title": title,
                "last_activity": session_data["last_activity"].isoformat(),
                "message_count": 0,
            }

        except Exception as e:
            logger.error("Failed to create session: %s", e)
            raise

    async def update_session_activity(
        self, session_id: str, first_message: str | None = None
    ) -> None:
        """Update session's last activity and optionally set title from first message."""
        try:
            session_ref = self.db.collection("sessions").document(session_id)
            update_data: dict[str, Any] = {"last_activity": datetime.now(UTC)}

            doc = await session_ref.get()
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

            await session_ref.set(update_data, merge=True)

        except Exception as e:
            logger.error("Failed to update session activity: %s", e)
            raise  # Don't swallow errors

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session and all its messages."""
        try:
            await self.clear_history(session_id)
            session_ref = self.db.collection("sessions").document(session_id)
            await session_ref.delete()

            logger.info("Deleted session %s", session_id)
            return True

        except Exception as e:
            logger.error("Failed to delete session: %s", e)
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
    """Get Firestore service singleton.

    FirestoreService already implements singleton pattern internally.
    """
    return FirestoreService()
