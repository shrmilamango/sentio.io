"""
Small in-memory rate limiter (no extra packages).

Counts hits per key in a sliding time window. Good enough for one server
process, which is what the free Render plan runs. With several workers or
servers, move this to Redis.
"""
import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request


class RateLimiter:
    def __init__(self, limit: int, window_seconds: int):
        self.limit, self.window = limit, window_seconds
        self._hits: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()

    def _prune(self, q: deque, now: float) -> None:
        while q and q[0] <= now - self.window:
            q.popleft()

    def blocked(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            q = self._hits[key]
            self._prune(q, now)
            return len(q) >= self.limit

    def hit(self, key: str) -> None:
        with self._lock:
            self._hits[key].append(time.monotonic())

    def check_and_hit(self, key: str) -> None:
        """Count one request; raise 429 once the limit is reached."""
        if self.blocked(key):
            raise too_many(self.window)
        self.hit(key)

    def reset(self, key: str) -> None:
        with self._lock:
            self._hits.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._hits.clear()


def too_many(retry_after: int) -> HTTPException:
    return HTTPException(status_code=429, detail="Too many attempts. Please wait a few minutes and try again.",
                         headers={"Retry-After": str(retry_after)})


def client_ip(request: Request) -> str:
    # Behind Render's proxy, uvicorn's --proxy-headers puts the real IP here.
    return request.client.host if request.client else "unknown"


# Limits
login_failures = RateLimiter(limit=10, window_seconds=15 * 60)   # per IP and per username
register_limit = RateLimiter(limit=5, window_seconds=60 * 60)    # new accounts per IP per hour
analyze_limit = RateLimiter(limit=30, window_seconds=60)         # analyses per IP per minute
feedback_limit = RateLimiter(limit=30, window_seconds=60)        # feedback clicks per IP per minute
