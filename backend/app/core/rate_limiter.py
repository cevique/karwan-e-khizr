import time
from collections import defaultdict

from fastapi import HTTPException, Request, status


class RateLimiter:
    """In-memory sliding window rate limiter.

    Sufficient for single-instance deployment. Provider-agnostic interface
    for future replacement with Redis-backed implementation.
    """

    def __init__(self, max_requests: int, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)

    def _cleanup(self, key: str, now: float) -> None:
        cutoff = now - self.window_seconds
        self._requests[key] = [t for t in self._requests[key] if t > cutoff]

    def check(self, key: str) -> bool:
        """Returns True if request is allowed, False if rate limited."""
        now = time.monotonic()
        self._cleanup(key, now)
        if len(self._requests[key]) >= self.max_requests:
            return False
        self._requests[key].append(now)
        return True

    def reset(self, key: str) -> None:
        """Reset the counter for a given key."""
        self._requests.pop(key, None)

    def reset_all(self) -> None:
        """Clear all tracked request counters. Intended for test isolation."""
        self._requests.clear()

    def remaining(self, key: str) -> int:
        """Return remaining allowed requests for a key."""
        now = time.monotonic()
        self._cleanup(key, now)
        return max(0, self.max_requests - len(self._requests[key]))


def rate_limit_dependency(max_requests: int, window_seconds: int = 60, key_func=None):
    """Create a FastAPI dependency that enforces rate limiting.

    Args:
        max_requests: Maximum number of requests allowed in the window.
        window_seconds: Time window in seconds (default: 60).
        key_func: Optional callable that takes a Request and returns a string key.
                  Defaults to using the client IP address.
    """
    limiter = RateLimiter(max_requests=max_requests, window_seconds=window_seconds)

    async def dependency(request: Request):
        if key_func:
            key = key_func(request)
        else:
            forwarded = request.headers.get("X-Forwarded-For")
            if forwarded:
                key = forwarded.split(",")[0].strip()
            else:
                key = request.client.host if request.client else "unknown"

        if not limiter.check(key):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later.",
            )

    return dependency, limiter
