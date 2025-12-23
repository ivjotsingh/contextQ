"""Rate limiting middleware for FastAPI.

Protects LLM endpoints from abuse and cost attacks.
Uses a simple in-memory sliding window approach.
"""

import logging
import time
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""

    requests_per_minute: int = 20
    requests_per_hour: int = 200
    burst_limit: int = 5  # Max requests in 10 seconds


class RateLimiter:
    """Simple in-memory rate limiter using sliding window."""

    def __init__(self, config: RateLimitConfig | None = None) -> None:
        self.config = config or RateLimitConfig()
        # Track request timestamps per client
        self._requests: dict[str, list[float]] = defaultdict(list)

    def _get_client_id(self, request: Request) -> str:
        """Extract client identifier from request."""
        # Try session cookie first
        session_id = request.cookies.get("session_id")
        if session_id:
            return f"session:{session_id}"

        # Fall back to IP address
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return f"ip:{forwarded.split(',')[0].strip()}"

        client = request.client
        if client:
            return f"ip:{client.host}"

        return "unknown"

    def _cleanup_old_requests(self, client_id: str, now: float) -> None:
        """Remove requests older than 1 hour."""
        hour_ago = now - 3600
        self._requests[client_id] = [
            ts for ts in self._requests[client_id] if ts > hour_ago
        ]

    def check_rate_limit(self, request: Request) -> tuple[bool, str | None, dict]:
        """Check if request is within rate limits.

        Returns:
            Tuple of (allowed, error_message, headers).
        """
        client_id = self._get_client_id(request)
        now = time.time()

        self._cleanup_old_requests(client_id, now)
        requests = self._requests[client_id]

        # Check burst limit (last 10 seconds)
        ten_sec_ago = now - 10
        recent_requests = sum(1 for ts in requests if ts > ten_sec_ago)
        if recent_requests >= self.config.burst_limit:
            return (
                False,
                "Too many requests. Please slow down.",
                {
                    "X-RateLimit-Limit": str(self.config.burst_limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(ten_sec_ago + 10)),
                    "Retry-After": "10",
                },
            )

        # Check per-minute limit
        minute_ago = now - 60
        minute_requests = sum(1 for ts in requests if ts > minute_ago)
        if minute_requests >= self.config.requests_per_minute:
            return (
                False,
                "Rate limit exceeded. Please wait a moment.",
                {
                    "X-RateLimit-Limit": str(self.config.requests_per_minute),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(minute_ago + 60)),
                    "Retry-After": "60",
                },
            )

        # Check per-hour limit
        hour_requests = len(requests)
        if hour_requests >= self.config.requests_per_hour:
            return (
                False,
                "Hourly rate limit exceeded.",
                {
                    "X-RateLimit-Limit": str(self.config.requests_per_hour),
                    "X-RateLimit-Remaining": "0",
                    "Retry-After": "3600",
                },
            )

        # Request allowed - record it
        self._requests[client_id].append(now)

        return (
            True,
            None,
            {
                "X-RateLimit-Limit": str(self.config.requests_per_minute),
                "X-RateLimit-Remaining": str(
                    self.config.requests_per_minute - minute_requests - 1
                ),
            },
        )


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to apply rate limiting to specific paths."""

    # Paths that need rate limiting (LLM-heavy endpoints)
    RATE_LIMITED_PATHS = {
        "/api/chat",
        "/api/documents/upload",
    }

    def __init__(self, app, config: RateLimitConfig | None = None) -> None:
        super().__init__(app)
        self.limiter = RateLimiter(config)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with rate limiting."""
        # Only rate limit specific paths
        if request.url.path not in self.RATE_LIMITED_PATHS:
            return await call_next(request)

        # Check rate limit
        allowed, error_message, headers = self.limiter.check_rate_limit(request)

        if not allowed:
            logger.warning(
                "Rate limit exceeded for %s on %s",
                self.limiter._get_client_id(request),
                request.url.path,
            )
            response = JSONResponse(
                status_code=429,
                content={
                    "success": False,
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": error_message,
                    },
                },
            )
            for key, value in headers.items():
                response.headers[key] = value
            return response

        # Process request
        response = await call_next(request)

        # Add rate limit headers to successful responses
        for key, value in headers.items():
            response.headers[key] = value

        return response
