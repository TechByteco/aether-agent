"""Structured JSON logging configuration for the Obscura Enchanted Agent Engine.

Provides setup_logging() for global log configuration and StructuredLogger
for context-rich, schema-consistent log emission in both JSON and
human-readable "pretty" modes.

Environment variables
---------------------
OBSCURA_LOG_LEVEL  : default INFO  (DEBUG / INFO / WARNING / ERROR / CRITICAL)
OBSCURA_LOG_FORMAT : default json  (json / pretty)
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from typing import Any, Dict, Optional


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_ENV_LEVEL = "OBSCURA_LOG_LEVEL"
_ENV_FORMAT = "OBSCURA_LOG_FORMAT"
_VERSION = "1.0.0"


# ---------------------------------------------------------------------------
# JSON formatter
# ---------------------------------------------------------------------------

class _JsonFormatter(logging.Formatter):
    """Formats every log record as a single-line JSON object."""

    def format(self, record: logging.LogRecord) -> str:  # type: ignore[override]
        payload: Dict[str, Any] = {
            "timestamp": self.formatTime(record, datefmt=None),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Merge any extra context fields injected by StructuredLogger
        for key, value in getattr(record, "_context", {}).items():
            payload[key] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


# ---------------------------------------------------------------------------
# Pretty formatter
# ---------------------------------------------------------------------------

class _PrettyFormatter(logging.Formatter):
    """Human-readable coloured log line for local development."""

    _COLOURS = {
        "DEBUG":    "\033[36m",   # cyan
        "INFO":     "\033[32m",   # green
        "WARNING":  "\033[33m",   # yellow
        "ERROR":    "\033[31m",   # red
        "CRITICAL": "\033[35m",   # magenta
    }
    _RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:  # type: ignore[override]
        colour = self._COLOURS.get(record.levelname, "")
        ts = self.formatTime(record, datefmt="%H:%M:%S")
        ctx = getattr(record, "_context", {})
        ctx_str = " ".join(f"{k}={v}" for k, v in ctx.items()) if ctx else ""
        base = (
            f"{colour}[{record.levelname:<8}]{self._RESET} "
            f"{ts} {record.name} — {record.getMessage()}"
        )
        if ctx_str:
            base += f"  ({ctx_str})"
        if record.exc_info:
            base += "\n" + self.formatException(record.exc_info)
        return base


# ---------------------------------------------------------------------------
# Public setup function
# ---------------------------------------------------------------------------

def setup_logging(
    level: str = "INFO",
    format: str = "json",  # noqa: A002  (shadows builtin but matches API spec)
    stream=None,
) -> None:
    """Configure root logging for the Obscura engine.

    Parameters
    ----------
    level:
        Log verbosity level string (DEBUG / INFO / WARNING / ERROR / CRITICAL).
        Overridden by the ``OBSCURA_LOG_LEVEL`` environment variable if set.
    format:
        Output format.  ``"json"`` emits newline-delimited JSON (production);
        ``"pretty"`` emits human-readable coloured lines (development).
        Overridden by ``OBSCURA_LOG_FORMAT`` if set.
    stream:
        Output stream.  Defaults to ``sys.stdout``.
    """
    effective_level = os.environ.get(_ENV_LEVEL, level).upper()
    effective_format = os.environ.get(_ENV_FORMAT, format).lower()

    if stream is None:
        stream = sys.stdout

    handler = logging.StreamHandler(stream)

    if effective_format == "pretty":
        handler.setFormatter(_PrettyFormatter())
    else:
        handler.setFormatter(_JsonFormatter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(getattr(logging, effective_level, logging.INFO))

    # Silence noisy third-party libraries at WARNING unless DEBUG mode
    if effective_level != "DEBUG":
        for noisy in ("httpx", "httpcore", "urllib3", "asyncio"):
            logging.getLogger(noisy).setLevel(logging.WARNING)


# ---------------------------------------------------------------------------
# StructuredLogger
# ---------------------------------------------------------------------------

class StructuredLogger:
    """Context-rich logger that ensures a consistent field schema on every record.

    Every emitted record always contains::

        timestamp, level, logger, message

    Optional context fields are merged in per call::

        session_id, url, action, tokens_saved, latency_ms

    Usage::

        from obscura_engine.logging_config import StructuredLogger
        log = StructuredLogger("obscura_engine.client")
        log.log_navigation("https://example.com", "ok", latency_ms=142.3, tokens_saved=1800)
    """

    def __init__(self, name: str) -> None:
        self._logger = logging.getLogger(name)

    # ------------------------------------------------------------------
    # Low-level emit
    # ------------------------------------------------------------------

    def _emit(
        self,
        level: int,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        exc_info: bool = False,
    ) -> None:
        """Emit a log record injecting *context* fields into the record."""
        if not self._logger.isEnabledFor(level):
            return
        extra = {"_context": context or {}}
        self._logger.log(level, message, extra=extra, exc_info=exc_info)

    # ------------------------------------------------------------------
    # Generic severity helpers
    # ------------------------------------------------------------------

    def debug(self, message: str, **ctx: Any) -> None:
        self._emit(logging.DEBUG, message, ctx)

    def info(self, message: str, **ctx: Any) -> None:
        self._emit(logging.INFO, message, ctx)

    def warning(self, message: str, **ctx: Any) -> None:
        self._emit(logging.WARNING, message, ctx)

    def error(self, message: str, exc_info: bool = False, **ctx: Any) -> None:
        self._emit(logging.ERROR, message, ctx, exc_info=exc_info)

    def critical(self, message: str, exc_info: bool = False, **ctx: Any) -> None:
        self._emit(logging.CRITICAL, message, ctx, exc_info=exc_info)

    # ------------------------------------------------------------------
    # Domain-specific helpers
    # ------------------------------------------------------------------

    def log_navigation(
        self,
        url: str,
        status: str,
        latency_ms: float,
        tokens_saved: Optional[int] = None,
        session_id: Optional[str] = None,
    ) -> None:
        """Emit a structured navigation event record.

        Parameters
        ----------
        url:
            The navigated URL.
        status:
            Outcome string: ``"ok"``, ``"error"``, ``"redirect"``, etc.
        latency_ms:
            Round-trip navigation latency in milliseconds.
        tokens_saved:
            Absolute number of tokens saved by distillation (optional).
        session_id:
            Active tab / session identifier (optional).
        """
        ctx: Dict[str, Any] = {
            "event": "navigation",
            "url": url,
            "status": status,
            "latency_ms": round(latency_ms, 2),
        }
        if tokens_saved is not None:
            ctx["tokens_saved"] = tokens_saved
        if session_id:
            ctx["session_id"] = session_id

        level = logging.INFO if status == "ok" else logging.WARNING
        self._emit(level, f"navigate {status} {url}", ctx)

    def log_action(
        self,
        session_id: str,
        action_type: str,
        ref: Optional[str],
        success: bool,
        latency_ms: Optional[float] = None,
    ) -> None:
        """Emit a structured browser action event record.

        Parameters
        ----------
        session_id:
            Active tab / session identifier.
        action_type:
            One of click / type / select / hover / scroll / press_key.
        ref:
            Element reference ID from the distilled snapshot (e.g. ``"12"``).
        success:
            Whether the action completed successfully.
        latency_ms:
            Action execution latency in milliseconds (optional).
        """
        ctx: Dict[str, Any] = {
            "event": "action",
            "session_id": session_id,
            "action": action_type,
            "ref": ref,
            "success": success,
        }
        if latency_ms is not None:
            ctx["latency_ms"] = round(latency_ms, 2)

        level = logging.INFO if success else logging.WARNING
        status_str = "ok" if success else "failed"
        self._emit(level, f"action {action_type} ref={ref} {status_str}", ctx)

    def log_error(
        self,
        error_type: str,
        message: str,
        session_id: Optional[str] = None,
        url: Optional[str] = None,
        exc_info: bool = False,
    ) -> None:
        """Emit a structured error record.

        Parameters
        ----------
        error_type:
            Short machine-readable error category (e.g. ``"NavigationError"``,
            ``"TimeoutError"``, ``"AuthError"``).
        message:
            Human-readable error description.
        session_id:
            Active tab / session identifier (optional).
        url:
            URL being accessed when the error occurred (optional).
        exc_info:
            If ``True``, attach current exception traceback.
        """
        ctx: Dict[str, Any] = {
            "event": "error",
            "error_type": error_type,
        }
        if session_id:
            ctx["session_id"] = session_id
        if url:
            ctx["url"] = url

        self._emit(logging.ERROR, f"{error_type}: {message}", ctx, exc_info=exc_info)

    def log_cache_event(
        self,
        url: str,
        hit: bool,
        tokens_saved: Optional[int] = None,
    ) -> None:
        """Emit a cache hit/miss record."""
        ctx: Dict[str, Any] = {
            "event": "cache",
            "url": url,
            "cache_hit": hit,
        }
        if tokens_saved is not None:
            ctx["tokens_saved"] = tokens_saved
        self._emit(logging.DEBUG, f"cache {'hit' if hit else 'miss'} {url}", ctx)


# ---------------------------------------------------------------------------
# Module-level convenience logger
# ---------------------------------------------------------------------------

#: Pre-built logger for engine-internal use.
engine_logger = StructuredLogger("obscura_engine")
