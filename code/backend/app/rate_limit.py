"""Per-IP token-bucket rate limiting backed by Redis/Valkey, with in-memory fallback.

Used by the FastAPI middleware for all public endpoints and reused by the alert
job to throttle outgoing sends.
"""
from __future__ import annotations

import time
from collections import defaultdict

import redis

from .config import settings

_redis: redis.Redis | None = None
try:
    _redis = redis.Redis.from_url(settings.redis_url, socket_connect_timeout=1)
    _redis.ping()
except Exception:
    _redis = None


class RateLimiter:
    def __init__(self, limit: int = 60, window: int = 60):
        self.limit = limit
        self.window = window
        self._mem: dict[str, list[float]] = defaultdict(list)

    def check(self, key: str):
        now = time.time()
        bucket = int(now // self.window)
        rkey = f"rl:{key}:{bucket}"

        if _redis is not None:
            try:
                n = _redis.incr(rkey)
                if n == 1:
                    _redis.expire(rkey, self.window)
                remaining = max(0, self.limit - n)
                allowed = n <= self.limit
                return allowed, remaining, self.limit, self.window
            except Exception:
                pass

        # in-memory fallback
        lst = self._mem[key]
        lst[:] = [t for t in lst if t > now - self.window]
        lst.append(now)
        remaining = max(0, self.limit - len(lst))
        allowed = len(lst) <= self.limit
        return allowed, remaining, self.limit, self.window


# Public API endpoints: 60 requests / minute per IP.
public_limiter = RateLimiter(limit=60, window=60)
# Auth endpoints (login/register/OTP): tighter bucket to blunt credential
# brute-force and SMS-bombing (see rate_limit_middleware in main.py).
auth_limiter = RateLimiter(limit=10, window=60)
# Alert job: 30 sends / minute (applied per send).
alert_limiter = RateLimiter(limit=30, window=60)
