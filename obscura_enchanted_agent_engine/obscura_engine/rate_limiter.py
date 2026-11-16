"""
obscura_engine/rate_limiter.py
==============================
Distributed-ready async rate limiters for the Obscura Enchanted Agent Engine.

Provides
--------
* ``SlidingWindowRateLimiter`` – per-domain HTTP request throttle.
* ``AgentRateLimiter``         – per-agent MCP tool call limiter.

Both use a sliding-window algorithm backed by ``asyncio.Lock`` and
``collections.deque`` so they are safe for concurrent async access in a single
process and straightforward to extend to a shared backing store (e.g. Redis)
for multi-process deployments.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Deque, Dict, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Shared sliding-window bookkeeping
# ---------------------------------------------------------------------------

@dataclass
class _Window:
    """Timestamps (monotonic, seconds) of recent requests inside a single window."""
    timestamps: Deque[float] = field(default_factory=deque)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


def _prune(window: _Window, now: float, window_size: float) -> None:
    """Remove timestamps older than *now - window_size* from *window*."""
    cutoff = now - window_size
    while window.timestamps and window.timestamps[0] < cutoff:
        window.timestamps.popleft()


# ---------------------------------------------------------------------------
# SlidingWindowRateLimiter
# ---------------------------------------------------------------------------

class SlidingWindowRateLimiter:
    """Per-domain HTTP-request rate limiter with two overlapping windows.

    Enforces **both**:

    * A short per-second window (default: 2 requests / second).
    * A per-minute window (default: 60 requests / minute).

    A request is allowed only when it fits within *both* windows.

    Parameters
    ----------
    requests_per_second:
        Maximum requests per 1-second window per domain.
    requests_per_minute:
        Maximum requests per 60-second window per domain.
    """

    def __init__(
        self,
        requests_per_second: int = 2,
        requests_per_minute: int = 60,
    ) -> None:
        self._rps = requests_per_second
        self._rpm = requests_per_minute
        # Separate deques for each time window to avoid double-pruning artefacts
        self._second_windows: Dict[str, _Window] = defaultdict(_Window)
        self._minute_windows: Dict[str, _Window] = defaultdict(_Window)

    # ------------------------------------------------------------------
    @staticmethod
    def _domain(key: str) -> str:
        """Extract the netloc from a URL or return *key* unchanged (bare domain)."""
        parsed = urlparse(key)
        return parsed.netloc.lower() if parsed.netloc else key.lower()

    # ------------------------------------------------------------------
    async def check_and_consume(self, key: str) -> bool:
        """Check whether a request is allowed and, if so, record it.

        Parameters
        ----------
        key:
            A URL or bare domain name.

        Returns
        -------
        bool
            ``True`` if the request is within rate limits (and has been
            recorded); ``False`` if it would exceed either window.
        """
        domain = self._domain(key)
        sw = self._second_windows[domain]
        mw = self._minute_windows[domain]

        # Acquire both locks (always in domain-alphabetical order to prevent deadlock)
        async with sw.lock:
            async with mw.lock:
                now = time.monotonic()
                _prune(sw, now, 1.0)
                _prune(mw, now, 60.0)

                if len(sw.timestamps) >= self._rps or len(mw.timestamps) >= self._rpm:
                    logger.debug(
                        "SlidingWindowRateLimiter: domain=%s denied (s=%d/%d, m=%d/%d)",
                        domain, len(sw.timestamps), self._rps,
                        len(mw.timestamps), self._rpm,
                    )
                    return False

                sw.timestamps.append(now)
                mw.timestamps.append(now)
                return True

    async def wait_until_allowed(self, key: str, poll_interval: float = 0.05) -> None:
        """Block asynchronously until the request is within rate limits.

        Parameters
        ----------
        key:
            A URL or bare domain name.
        poll_interval:
            Seconds to sleep between retry checks (default: 50 ms).
        """
        while not await self.check_and_consume(key):
            await asyncio.sleep(poll_interval)

    def get_stats(self, key: Optional[str] = None) -> Dict[str, object]:
        """Return current window sizes.

        When *key* is given, stats are returned for that domain only.
        Otherwise, an aggregate over all tracked domains is returned.
        """
        if key:
            domain = self._domain(key)
            now = time.monotonic()
            sw = self._second_windows.get(domain)
            mw = self._minute_windows.get(domain)
            s_count = len(sw.timestamps) if sw else 0
            m_count = len(mw.timestamps) if mw else 0
            return {
                "limiter": "SlidingWindowRateLimiter",
                "domain": domain,
                "requests_last_second": s_count,
                "requests_last_minute": m_count,
                "limit_per_second": self._rps,
                "limit_per_minute": self._rpm,
            }
        return {
            "limiter": "SlidingWindowRateLimiter",
            "tracked_domains": len(self._second_windows),
            "limit_per_second": self._rps,
            "limit_per_minute": self._rpm,
        }


# ---------------------------------------------------------------------------
# AgentRateLimiter
# ---------------------------------------------------------------------------

class AgentRateLimiter:
    """Per-agent MCP tool call limiter.

    Enforces a rolling 60-second cap (default: 100 calls / minute) per
    ``agent_id``.  Uses the same sliding-window approach as
    :class:`SlidingWindowRateLimiter`.

    Parameters
    ----------
    calls_per_minute:
        Maximum tool calls per 60-second window per agent.
    """

    def __init__(self, calls_per_minute: int = 100) -> None:
        self._cpm = calls_per_minute
        self._windows: Dict[str, _Window] = defaultdict(_Window)

    # ------------------------------------------------------------------
    async def check_and_consume(self, key: str) -> bool:
        """Check whether a tool call is within the agent's rate limit.

        Parameters
        ----------
        key:
            The ``agent_id`` string.

        Returns
        -------
        bool
            ``True`` if allowed (and recorded); ``False`` if the cap is
            exceeded.
        """
        window = self._windows[key]
        async with window.lock:
            now = time.monotonic()
            _prune(window, now, 60.0)
            if len(window.timestamps) >= self._cpm:
                logger.debug(
                    "AgentRateLimiter: agent=%s denied (%d/%d calls/min)",
                    key, len(window.timestamps), self._cpm,
                )
                return False
            window.timestamps.append(now)
            return True

    async def wait_until_allowed(self, key: str, poll_interval: float = 0.1) -> None:
        """Block asynchronously until the agent's call quota has headroom.

        Parameters
        ----------
        key:
            The ``agent_id`` string.
        poll_interval:
            Seconds to sleep between checks (default: 100 ms).
        """
        while not await self.check_and_consume(key):
            await asyncio.sleep(poll_interval)

    def calls_remaining(self, key: str) -> int:
        """Return the number of calls the agent can still make this minute."""
        window = self._windows.get(key)
        if window is None:
            return self._cpm
        now = time.monotonic()
        _prune(window, now, 60.0)
        return max(0, self._cpm - len(window.timestamps))

    def get_stats(self, key: Optional[str] = None) -> Dict[str, object]:
        """Return current usage statistics.

        When *key* is provided, returns stats for that agent only; otherwise
        returns aggregate info.
        """
        if key:
            remaining = self.calls_remaining(key)
            w = self._windows.get(key)
            used = len(w.timestamps) if w else 0
            return {
                "limiter": "AgentRateLimiter",
                "agent_id": key,
                "calls_this_minute": used,
                "calls_remaining": remaining,
                "limit_per_minute": self._cpm,
            }
        return {
            "limiter": "AgentRateLimiter",
            "tracked_agents": len(self._windows),
            "limit_per_minute": self._cpm,
        }
