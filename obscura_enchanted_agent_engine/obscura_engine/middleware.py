"""Middleware stack for the Obscura HTTP API server.

Includes:
- Request timing (adds X-Process-Time-Ms header)
- API key authentication (X-API-Key header or ?api_key= query param)
- In-memory sliding window rate limiter (per session / per IP)
"""

from __future__ import annotations

import asyncio
import collections
import logging
import os
import time
from typing import Callable, Deque, Dict, Optional

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

logger = logging.getLogger("obscura_engine.middleware")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_RATE_LIMIT_MAX_REQUESTS: int = 100     # requests
_RATE_LIMIT_WINDOW_SECS: float = 60.0  # per 60-second window
_SKIP_AUTH_PATHS: frozenset = frozenset({"/health", "/docs", "/redoc", "/openapi.json"})


# ---------------------------------------------------------------------------
# Sliding-window rate limiter (in-memory, per key)
# ---------------------------------------------------------------------------

class SlidingWindowRateLimiter:
    """Thread/async-safe sliding window counter using deques of timestamps."""

    def __init__(
        self,
        max_requests: int = _RATE_LIMIT_MAX_REQUESTS,
        window_seconds: float = _RATE_LIMIT_WINDOW_SECS,
    ) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._windows: Dict[str, Deque[float]] = collections.defaultdict(collections.deque)
        self._lock = asyncio.Lock()

    async def is_allowed(self, key: str) -> tuple[bool, int]:
        """Return (allowed, requests_remaining) for *key* right now.

        Prunes expired timestamps atomically, then checks the count.
        """
        async with self._lock:
            now = time.monotonic()
            cutoff = now - self.window_seconds
            window = self._windows[key]

            # Evict timestamps outside the window
            while window and window[0] <= cutoff:
                window.popleft()

            count = len(window)
            if count >= self.max_requests:
                return False, 0

            window.append(now)
            return True, self.max_requests - count - 1

    async def reset(self, key: str) -> None:
        async with self._lock:
            self._windows.pop(key, None)


# Singleton shared across all middleware instances
_global_rate_limiter = SlidingWindowRateLimiter()


def get_rate_limiter() -> SlidingWindowRateLimiter:
    return _global_rate_limiter


# ---------------------------------------------------------------------------
# Request-timing middleware
# ---------------------------------------------------------------------------

class TimingMiddleware(BaseHTTPMiddleware):
    """Injects X-Process-Time-Ms into every response."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        response.headers["X-Process-Time-Ms"] = str(elapsed_ms)
        logger.debug(
            "%s %s → %s (%.2f ms)",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )
        return response


# ---------------------------------------------------------------------------
# API-key auth middleware
# ---------------------------------------------------------------------------

class ApiKeyMiddleware(BaseHTTPMiddleware):
    """Checks X-API-Key header or ?api_key= query param.

    Skipped entirely when ``OBSCURA_API_KEY`` env var is not set,
    so local dev works out of the box.
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        self._required_key: Optional[str] = os.getenv("OBSCURA_API_KEY")
        if self._required_key:
            logger.info("API key authentication ENABLED.")
        else:
            logger.info("OBSCURA_API_KEY not set — API key auth DISABLED.")

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Auth disabled
        if not self._required_key:
            return await call_next(request)

        # Always allow health / docs
        if request.url.path in _SKIP_AUTH_PATHS:
            return await call_next(request)

        # Check header first, then query param
        api_key = (
            request.headers.get("X-API-Key")
            or request.query_params.get("api_key")
        )

        if api_key != self._required_key:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "error": "Unauthorized",
                    "detail": "Valid X-API-Key header or ?api_key= query param required.",
                },
            )

        return await call_next(request)


# ---------------------------------------------------------------------------
# Rate-limiting middleware
# ---------------------------------------------------------------------------

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Per-session (or per-IP) sliding window rate limiter.

    Rate-limit key priority:
      1. X-Session-Id header
      2. ?session_id= query param
      3. client host IP
    """

    def __init__(
        self,
        app: ASGIApp,
        limiter: Optional[SlidingWindowRateLimiter] = None,
    ) -> None:
        super().__init__(app)
        self._limiter = limiter or _global_rate_limiter

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Health / docs are exempt
        if request.url.path in _SKIP_AUTH_PATHS:
            return await call_next(request)

        key = (
            request.headers.get("X-Session-Id")
            or request.query_params.get("session_id")
            or (request.client.host if request.client else "unknown")
        )

        allowed, remaining = await self._limiter.is_allowed(key)

        if not allowed:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Too Many Requests",
                    "detail": (
                        f"Rate limit of {_RATE_LIMIT_MAX_REQUESTS} req/"
                        f"{int(_RATE_LIMIT_WINDOW_SECS)}s exceeded for key '{key}'."
                    ),
                },
                headers={
                    "Retry-After": str(int(_RATE_LIMIT_WINDOW_SECS)),
                    "X-RateLimit-Limit": str(_RATE_LIMIT_MAX_REQUESTS),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Window": str(int(_RATE_LIMIT_WINDOW_SECS)),
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(_RATE_LIMIT_MAX_REQUESTS)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Window"] = str(int(_RATE_LIMIT_WINDOW_SECS))
        return response
