# Backend Development Notes

## Removed Features

### Redis Cache Service (Removed)

**What it was:** Redis service for caching session→doc_ids mapping and response caching.

**Why removed:**

1. **Response caching was overkill:**
   - Each user has their own unique documents
   - Questions are rarely exactly identical
   - Cache hit rate would be near zero in practice

2. **Session→doc_ids mapping was redundant:**
   - Every chunk in Qdrant already has `session_id` in payload
   - Filtering by `session_id` alone is sufficient for vector search
   - No need to maintain a separate doc_ids list

3. **Simplified architecture:**
   - One less service to deploy and manage
   - Qdrant is the single source of truth
   - Fewer moving parts = fewer failure modes

---

### Potential Redis Use Cases (Future)

If Redis is needed later, here are valuable use cases:

| Use Case | Value | Complexity |
|----------|-------|------------|
| **Rate limiting** | Prevent abuse (X requests/min per session) | Low |
| **Query deduplication** | Ignore duplicate requests within 2s window | Low |
| **Real-time features** | Pub/Sub for multi-tab sync, typing indicators | Medium |
| **Session state** | Store temp UI state (selected docs, filters) | Low |
| **Analytics** | Count queries per session, popular questions | Low |

**Rate limiting example:**
```python
async def check_rate_limit(session_id: str) -> bool:
    key = f"rate:{session_id}"
    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, 60)  # 1 minute window
    return count <= 10  # 10 requests/minute
```

---

## Architecture Decisions

### Document Ownership via session_id

Documents are stored in Qdrant with `session_id` in the payload. Vector search filters by `session_id` to ensure users only see their own documents. This is both a security boundary and a relevance filter.

### Embedding Caching (Not Implemented)

Voyage AI charges per token. Caching embeddings could save costs for repeated text chunks. Currently not implemented - add if API costs become significant.
