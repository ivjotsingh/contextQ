#!/usr/bin/env python3
"""Reset Qdrant collection to match new embedding dimensions.

Run this script when switching embedding providers or dimensions.

Usage:
    cd backend
    python scripts/reset_qdrant.py
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import get_settings
from services.vector_store import VectorStoreService


async def reset_collection():
    """Delete and recreate the Qdrant collection."""
    settings = get_settings()
    vector_store = VectorStoreService()

    print(f"🔄 Resetting Qdrant collection: {settings.qdrant_collection}")
    print(f"📏 New dimensions: {settings.embedding_dimensions}")
    print(f"🤖 Embedding model: {settings.embedding_model}")

    try:
        # Try to delete existing collection
        print("\n🗑️  Deleting old collection...")
        await vector_store.client.delete_collection(settings.qdrant_collection)
        print("✅ Old collection deleted")
    except Exception as e:
        print(f"ℹ️  Collection doesn't exist or couldn't be deleted: {e}")

    # Initialize (creates new collection)
    print("\n🏗️  Creating new collection...")
    await vector_store.initialize()
    print(f"✅ Collection created with {settings.embedding_dimensions} dimensions")

    print("\n✨ Reset complete! You can now upload documents.")


if __name__ == "__main__":
    asyncio.run(reset_collection())
