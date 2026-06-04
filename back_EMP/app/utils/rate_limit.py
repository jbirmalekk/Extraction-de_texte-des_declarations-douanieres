"""
Simple in-memory rate limiting helpers.
For production multi-instance, replace with Redis-based limiter.
"""
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from threading import Lock

from fastapi import HTTPException, Request, status


@dataclass(frozen=True)
class LimitRule:
    max_requests: int
    per_seconds: int


_events: dict[str, deque[datetime]] = defaultdict(deque)
_failed_logins: dict[str, deque[datetime]] = defaultdict(deque)
_lock = Lock()


def _clean_window(bucket: deque[datetime], window_seconds: int, now: datetime) -> None:
    threshold = now - timedelta(seconds=window_seconds)
    while bucket and bucket[0] < threshold:
        bucket.popleft()


def enforce_rate_limit(request: Request, route_key: str, rule: LimitRule) -> None:
    now = datetime.utcnow()
    client_ip = request.client.host if request.client else "unknown"
    key = f"{route_key}:{client_ip}"
    with _lock:
        bucket = _events[key]
        _clean_window(bucket, rule.per_seconds, now)
        if len(bucket) >= rule.max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many requests on {route_key}. Retry later.",
            )
        bucket.append(now)


def record_failed_login(email: str | None, request: Request) -> int:
    now = datetime.utcnow()
    client_ip = request.client.host if request.client else "unknown"
    normalized = (email or "").strip().lower()
    key = f"{normalized}:{client_ip}"
    with _lock:
        bucket = _failed_logins[key]
        _clean_window(bucket, 900, now)  # 15 minutes
        bucket.append(now)
        return len(bucket)
