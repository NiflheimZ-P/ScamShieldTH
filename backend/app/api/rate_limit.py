"""In-memory rate limit for the endpoints that spend the class-proxy quota (one process, so no Redis needed).

Two sliding windows: per client (first X-Forwarded-For hop — Render and Vercel both set it) and one global cap.
The header can be spoofed, so the global cap is what actually bounds a public deploy's spend.
"""

import math
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

from app.config import get_settings


class SlidingWindow:
    def __init__(self, limit: int, seconds: float) -> None:
        self.limit, self.seconds = limit, seconds
        self.hits: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str, now: float) -> float:
        """Record a hit and return 0, or return the seconds to wait if the key is over the limit."""
        q = self.hits[key]
        while q and q[0] <= now - self.seconds:
            q.popleft()
        if len(q) >= self.limit:
            return q[0] + self.seconds - now
        q.append(now)
        return 0.0


_settings = get_settings()
_per_client = SlidingWindow(_settings.rate_limit_per_minute, 60)
_global = SlidingWindow(_settings.rate_limit_per_hour, 3600)


def client_key(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def rate_limit(request: Request) -> None:
    if _settings.rate_limit_per_minute <= 0:  # 0 disables (local dev, eval)
        return
    now = time.monotonic()
    wait = _per_client.check(client_key(request), now) or _global.check("*", now)
    if wait:
        raise HTTPException(
            status_code=429,
            detail="ใช้งานถี่เกินไป กรุณารอสักครู่แล้วลองใหม่",
            headers={"Retry-After": str(math.ceil(wait))},
        )
