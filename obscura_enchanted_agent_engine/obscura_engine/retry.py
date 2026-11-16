"""
obscura_engine/retry.py
=======================
Resilient async retry logic for the Obscura Enchanted Agent Engine.

Provides
--------
* ``RetryPolicy``      – dataclass that describes backoff/jitter strategy.
* ``NavigationError``  – rich exception carrying request metadata.
* ``with_retry``       – async helper that wraps any coroutine with retry logic.

Handled conditions
------------------
* ``httpx.TimeoutException``  – transient network timeout
* ``httpx.ConnectError``      – DNS / TCP connection failures
* HTTP 429 – honouring the ``Retry-After`` response header
* HTTP 502 / 503 – gateway / service-unavailable transients
"""

from __future__ import annotations

import asyncio
import logging
import random
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine, Optional, Sequence, Tuple, Type

import httpx

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# NavigationError
# ---------------------------------------------------------------------------

class NavigationError(Exception):
    """Raised when a navigation / HTTP action exhausts all retry attempts.

    Attributes
    ----------
    url:
        The target URL that could not be reached.
    status_code:
        HTTP status code of the last failure (0 for network-level errors).
    attempt:
        1-based attempt number at which the error was recorded.
    message:
        Human-readable description of the failure.
    retry_after:
        Seconds suggested by a ``Retry-After`` header (if present).
    """

    def __init__(
        self,
        url: str,
        message: str,
        *,
        status_code: int = 0,
        attempt: int = 1,
        retry_after: Optional[float] = None,
    ) -> None:
        super().__init__(message)
        self.url = url
        self.status_code = status_code
        self.attempt = attempt
        self.message = message
        self.retry_after = retry_after

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"NavigationError(url={self.url!r}, status_code={self.status_code}, "
            f"attempt={self.attempt}, message={self.message!r})"
        )


# ---------------------------------------------------------------------------
# RetryPolicy
# ---------------------------------------------------------------------------

@dataclass
class RetryPolicy:
    """Configuration for exponential-backoff retry behaviour.

    Parameters
    ----------
    max_attempts:
        Total number of attempts (1 means no retries).
    base_delay:
        Initial delay between attempts in seconds.
    max_delay:
        Upper bound for any computed delay in seconds.
    exponential_base:
        Multiplier applied to the delay on each successive attempt.
    jitter:
        When *True*, add uniform random jitter in ``[0, base_delay)`` to
        each delay to prevent thundering-herd scenarios.
    retryable_status_codes:
        HTTP status codes that are considered transient and eligible for retry.
    """

    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    exponential_base: float = 2.0
    jitter: bool = True
    retryable_status_codes: Tuple[int, ...] = (429, 502, 503)

    def compute_delay(self, attempt: int, retry_after: Optional[float] = None) -> float:
        """Return the sleep duration (seconds) before *attempt* number *attempt*.

        Parameters
        ----------
        attempt:
            0-based retry index (0 → first retry, 1 → second, …).
        retry_after:
            Explicit wait time from a ``Retry-After`` header; takes precedence
            when greater than the computed backoff.
        """
        backoff = min(self.base_delay * (self.exponential_base ** attempt), self.max_delay)
        if self.jitter:
            backoff += random.uniform(0, self.base_delay)
            backoff = min(backoff, self.max_delay)
        if retry_after is not None and retry_after > 0:
            backoff = max(backoff, retry_after)
        return backoff


# ---------------------------------------------------------------------------
# Default retryable exceptions
# ---------------------------------------------------------------------------

DEFAULT_RETRYABLE_EXCEPTIONS: Tuple[Type[Exception], ...] = (
    httpx.TimeoutException,
    httpx.ConnectError,
    httpx.RemoteProtocolError,
)


# ---------------------------------------------------------------------------
# with_retry
# ---------------------------------------------------------------------------

async def with_retry(
    func: Callable[..., Coroutine[Any, Any, Any]],
    policy: Optional[RetryPolicy] = None,
    retryable_exceptions: Sequence[Type[Exception]] = DEFAULT_RETRYABLE_EXCEPTIONS,
    *,
    url: str = "",
    **kwargs: Any,
) -> Any:
    """Execute *func* with exponential-backoff retry semantics.

    Parameters
    ----------
    func:
        An **async** callable.  It is called as ``await func(**kwargs)`` on
        each attempt.
    policy:
        A :class:`RetryPolicy` instance; defaults to ``RetryPolicy()`` when
        *None*.
    retryable_exceptions:
        Exception types (beyond the HTTP status codes in the policy) that
        trigger a retry instead of an immediate raise.
    url:
        The URL being fetched; embedded in :class:`NavigationError` on
        exhaustion.
    **kwargs:
        Forwarded to *func* on every attempt.

    Returns
    -------
    Any
        The return value of *func* on success.

    Raises
    ------
    NavigationError
        When all attempts are exhausted.
    """
    if policy is None:
        policy = RetryPolicy()

    last_exc: Optional[Exception] = None
    last_status: int = 0
    last_retry_after: Optional[float] = None

    for attempt in range(1, policy.max_attempts + 1):
        try:
            result = await func(**kwargs)
            # Support httpx.Response-like objects with .status_code
            status = getattr(result, "status_code", None)
            if status is not None and status in policy.retryable_status_codes:
                last_status = status
                retry_after = _parse_retry_after(result)
                if attempt < policy.max_attempts:
                    delay = policy.compute_delay(attempt - 1, retry_after)
                    logger.warning(
                        "Retryable HTTP %d on %s (attempt %d/%d); sleeping %.2fs",
                        status, url, attempt, policy.max_attempts, delay,
                    )
                    await asyncio.sleep(delay)
                    continue
                raise NavigationError(
                    url,
                    f"HTTP {status} after {attempt} attempt(s)",
                    status_code=status,
                    attempt=attempt,
                    retry_after=retry_after,
                )
            return result

        except tuple(retryable_exceptions) as exc:  # type: ignore[misc]
            last_exc = exc
            if attempt < policy.max_attempts:
                delay = policy.compute_delay(attempt - 1, last_retry_after)
                logger.warning(
                    "%s on %s (attempt %d/%d); retrying in %.2fs — %s",
                    type(exc).__name__, url, attempt, policy.max_attempts, delay, exc,
                )
                await asyncio.sleep(delay)
            else:
                raise NavigationError(
                    url,
                    f"{type(exc).__name__}: {exc}",
                    status_code=last_status,
                    attempt=attempt,
                ) from exc

        except Exception:
            # Non-retryable — propagate immediately
            raise

    # Should not be reachable
    raise NavigationError(url, "Retry loop exhausted unexpectedly", attempt=policy.max_attempts)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_retry_after(response: Any) -> Optional[float]:
    """Extract the ``Retry-After`` value (seconds) from an httpx-like response."""
    headers: Any = getattr(response, "headers", {})
    raw = headers.get("retry-after") if headers else None
    if raw is None:
        return None
    try:
        return float(raw)
    except ValueError:
        # Could be an HTTP-date string; fall back to a fixed 5s
        return 5.0
