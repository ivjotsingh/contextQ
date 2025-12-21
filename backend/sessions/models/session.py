"""Session model for Firestore storage."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class FirestoreSession(BaseModel):
    """Schema for a session stored in Firestore."""

    id: str = Field(..., description="Unique session ID")
    title: str = Field(default="New Chat", description="Session title")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    last_activity: datetime | None = Field(None, description="Last activity timestamp")
    message_count: int = Field(default=0, description="Number of messages in session")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for Firestore."""
        data = self.model_dump(mode="json")
        data["created_at"] = self.created_at.isoformat()
        if self.last_activity:
            data["last_activity"] = self.last_activity.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FirestoreSession":
        """Create from Firestore dictionary."""
        if "created_at" in data and isinstance(data["created_at"], str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if "last_activity" in data and isinstance(data["last_activity"], str):
            data["last_activity"] = datetime.fromisoformat(data["last_activity"])
        return cls(**data)

