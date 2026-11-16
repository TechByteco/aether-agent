"""
obscura_engine/cache.py
=======================
Intelligent multi-tier caching system for the Obscura Enchanted Agent Engine.

Tiers
-----
* SnapshotCache   – LRU cache for distilled page snapshots (URL + content-hash key).
* RobotsTxtCache  – Per-domain robots.txt rules with crawl-delay enforcement.
* ResponseCache   – HTTP response cache that honours Cache-Control directives;
                    payloads stored gzip-compressed.
"""

from __future__ import annotations

import gzip
import hashlib
import logging
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from http import HTTPStatus
from typing import Any, Dict, Optional
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Shared data containers
# ---------------------------------------------------------------------------

@dataclass
class CachedEntry:
    """A single cached value with metadata."""

    key: str
    content: bytes                      # may be gzip-compressed (check is_compressed)
    headers: Dict[str, str] = field(default_factory=dict)
    created_at: float = field(default_factory=time.monotonic)
    expires_at: float = 0.0             # 0 means no expiry set by caller
    is_compressed: bool = False
    extra: Dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------
    def is_expired(self) -> bool:
        """Return True when the entry has passed its TTL."""
        if self.expires_at == 0.0:
            return False
        return time.monotonic() > self.expires_at

    def decompress(self) -> bytes:
        """Return raw (uncompressed) content."""
        if self.is_compressed:
            return gzip.decompress(self.content)
        return self.content


# ---------------------------------------------------------------------------
# SnapshotCache
# ---------------------------------------------------------------------------

class SnapshotCache:
    """LRU cache for distilled page snapshots.

    Key   : ``"{url}::{content_hash}"`` (SHA-256 of raw HTML / snapshot text)
    Limit : 200 entries
    TTL   : 600 seconds (10 minutes)
    """

    MAX_SIZE: int = 200
    DEFAULT_TTL: float = 600.0  # seconds

    def __init__(self, max_size: int = MAX_SIZE, ttl: float = DEFAULT_TTL) -> None:
        self._max_size = max_size
        self._ttl = ttl
        self._store: OrderedDict[str, CachedEntry] = OrderedDict()
        self._hits: int = 0
        self._misses: int = 0

    # ------------------------------------------------------------------
    @staticmethod
    def make_key(url: str, content: bytes | str) -> str:
        """Build a cache key from a URL and the page's raw content."""
        raw = content if isinstance(content, bytes) else content.encode()
        digest = hashlib.sha256(raw).hexdigest()[:16]
        return f"{url}::{digest}"

    # ------------------------------------------------------------------
    def get(self, url: str, content: bytes | str = b"") -> Optional[CachedEntry]:
        """Return a cached snapshot or *None* on miss / expiry.

        Parameters
        ----------
        url:
            The page URL.
        content:
            The page content used for key derivation; pass the same value as
            was used in :meth:`set`.
        """
        key = self.make_key(url, content)
        entry = self._store.get(key)
        if entry is None:
            self._misses += 1
            return None
        if entry.is_expired():
            del self._store[key]
            self._misses += 1
            return None
        # LRU: move to end
        self._store.move_to_end(key)
        self._hits += 1
        return entry

    def set(self, url: str, content: bytes | str, headers: Optional[Dict[str, str]] = None) -> str:
        """Store a snapshot; evict LRU entry if at capacity.

        Returns the cache key used.
        """
        raw = content if isinstance(content, bytes) else content.encode()
        key = self.make_key(url, raw)
        entry = CachedEntry(
            key=key,
            content=raw,
            headers=headers or {},
            expires_at=time.monotonic() + self._ttl,
        )
        if key in self._store:
            self._store.move_to_end(key)
        self._store[key] = entry
        if len(self._store) > self._max_size:
            evicted_key, _ = self._store.popitem(last=False)
            logger.debug("SnapshotCache evicted LRU entry: %s", evicted_key)
        return key

    def invalidate(self, url: str) -> int:
        """Remove all snapshot entries for *url* (any content hash). Returns count removed."""
        prefix = f"{url}::"
        to_delete = [k for k in self._store if k.startswith(prefix)]
        for k in to_delete:
            del self._store[k]
        return len(to_delete)

    def get_stats(self) -> Dict[str, Any]:
        """Return hit rate and size statistics."""
        total = self._hits + self._misses
        return {
            "cache": "SnapshotCache",
            "size": len(self._store),
            "max_size": self._max_size,
            "ttl_seconds": self._ttl,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(self._hits / total, 4) if total else 0.0,
        }

    def purge_expired(self) -> int:
        """Evict all stale entries. Returns count removed."""
        stale = [k for k, v in self._store.items() if v.is_expired()]
        for k in stale:
            del self._store[k]
        return len(stale)


# ---------------------------------------------------------------------------
# RobotsTxtCache
# ---------------------------------------------------------------------------

@dataclass
class _RobotsEntry:
    parser: RobotFileParser
    crawl_delay: float          # seconds (0 = none specified)
    expires_at: float


class RobotsTxtCache:
    """Cache parsed robots.txt rules per domain with crawl-delay enforcement.

    TTL   : 3 600 seconds (1 hour)
    """

    DEFAULT_TTL: float = 3600.0  # 1 hour

    def __init__(self, ttl: float = DEFAULT_TTL, user_agent: str = "*") -> None:
        self._ttl = ttl
        self._user_agent = user_agent
        self._store: Dict[str, _RobotsEntry] = {}
        self._last_request: Dict[str, float] = {}   # domain -> last monotonic fetch time

    # ------------------------------------------------------------------
    @staticmethod
    def _domain(url: str) -> str:
        return urlparse(url).netloc.lower()

    # ------------------------------------------------------------------
    def get(self, url: str) -> Optional[_RobotsEntry]:
        """Return the cached robots entry for *url*'s domain, or *None* on miss/expiry."""
        domain = self._domain(url)
        entry = self._store.get(domain)
        if entry is None:
            return None
        if time.monotonic() > entry.expires_at:
            del self._store[domain]
            return None
        return entry

    def set(self, url: str, robots_txt_content: str) -> None:
        """Parse and store robots.txt content for *url*'s domain."""
        domain = self._domain(url)
        robots_url = f"{urlparse(url).scheme}://{domain}/robots.txt"

        parser = RobotFileParser(url=robots_url)
        parser.parse(robots_txt_content.splitlines())

        raw_delay = parser.crawl_delay(self._user_agent) or 0.0
        entry = _RobotsEntry(
            parser=parser,
            crawl_delay=float(raw_delay),
            expires_at=time.monotonic() + self._ttl,
        )
        self._store[domain] = entry
        logger.debug("RobotsTxtCache stored rules for %s (crawl_delay=%.2fs)", domain, raw_delay)

    def invalidate(self, url: str) -> None:
        """Remove cached robots entry for *url*'s domain."""
        self._store.pop(self._domain(url), None)

    def is_allowed(self, url: str, user_agent: Optional[str] = None) -> bool:
        """Return True if *user_agent* (or the default) is allowed to fetch *url*."""
        entry = self.get(url)
        if entry is None:
            return True   # no rules → allow
        return entry.parser.can_fetch(user_agent or self._user_agent, url)

    def get_crawl_delay(self, url: str) -> float:
        """Return the crawl delay (seconds) for *url*'s domain; 0 if unspecified."""
        entry = self.get(url)
        return entry.crawl_delay if entry else 0.0

    def record_request(self, url: str) -> None:
        """Record that a request was made to this domain (for crawl-delay enforcement)."""
        self._last_request[self._domain(url)] = time.monotonic()

    def seconds_until_allowed(self, url: str) -> float:
        """Return seconds to wait before next crawl, respecting crawl-delay. 0 means now."""
        delay = self.get_crawl_delay(url)
        if delay <= 0:
            return 0.0
        domain = self._domain(url)
        last = self._last_request.get(domain)
        if last is None:
            return 0.0
        wait = delay - (time.monotonic() - last)
        return max(0.0, wait)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "cache": "RobotsTxtCache",
            "domains_cached": len(self._store),
            "ttl_seconds": self._ttl,
        }


# ---------------------------------------------------------------------------
# ResponseCache
# ---------------------------------------------------------------------------

_CACHE_CONTROL_NO_STORE = "no-store"
_CACHE_CONTROL_NO_CACHE = "no-cache"


def _parse_max_age(cache_control: str) -> Optional[float]:
    """Extract ``max-age`` value from a ``Cache-Control`` header string."""
    for part in cache_control.split(","):
        part = part.strip().lower()
        if part.startswith("max-age="):
            try:
                return float(part.split("=", 1)[1])
            except ValueError:
                return None
    return None


class ResponseCache:
    """Cache raw HTTP responses by URL, honouring Cache-Control semantics.

    Payloads are stored gzip-compressed to reduce memory footprint.
    Entries that carry ``no-store`` are never persisted; ``no-cache`` entries
    are stored but marked as immediately stale (require revalidation).
    """

    DEFAULT_TTL: float = 300.0  # 5-minute fallback when no max-age is provided

    def __init__(self, default_ttl: float = DEFAULT_TTL) -> None:
        self._default_ttl = default_ttl
        self._store: Dict[str, CachedEntry] = {}

    # ------------------------------------------------------------------
    @staticmethod
    def _normalise_url(url: str) -> str:
        """Strip fragments; keep query strings (they can carry meaningful params)."""
        parsed = urlparse(url)
        return parsed._replace(fragment="").geturl()

    # ------------------------------------------------------------------
    def get(self, url: str) -> Optional[CachedEntry]:
        """Return cached response or *None* on miss/expiry."""
        key = self._normalise_url(url)
        entry = self._store.get(key)
        if entry is None:
            return None
        if entry.is_expired():
            del self._store[key]
            return None
        return entry

    def set(
        self,
        url: str,
        content: bytes | str,
        headers: Optional[Dict[str, str]] = None,
    ) -> bool:
        """Cache *content* for *url*.

        Returns *True* if stored, *False* if rejected (``no-store``).
        """
        headers = {k.lower(): v for k, v in (headers or {}).items()}
        cache_control = headers.get("cache-control", "")

        # Respect no-store
        if _CACHE_CONTROL_NO_STORE in cache_control.lower():
            logger.debug("ResponseCache: no-store for %s — skipping", url)
            return False

        # Determine TTL
        if _CACHE_CONTROL_NO_CACHE in cache_control.lower():
            ttl = 0.0   # stored but immediately expired (requires revalidation)
        else:
            ttl = _parse_max_age(cache_control) or self._default_ttl

        raw = content if isinstance(content, bytes) else content.encode()
        compressed = gzip.compress(raw, compresslevel=6)

        key = self._normalise_url(url)
        entry = CachedEntry(
            key=key,
            content=compressed,
            headers=headers,
            expires_at=time.monotonic() + ttl,
            is_compressed=True,
        )
        self._store[key] = entry
        logger.debug(
            "ResponseCache stored %s (compressed %d→%d bytes, ttl=%.0fs)",
            key, len(raw), len(compressed), ttl,
        )
        return True

    def invalidate(self, url: str) -> None:
        """Remove the cached entry for *url*."""
        self._store.pop(self._normalise_url(url), None)

    def get_stats(self) -> Dict[str, Any]:
        """Return cache size and compression statistics."""
        total_compressed = sum(len(e.content) for e in self._store.values())
        return {
            "cache": "ResponseCache",
            "entries": len(self._store),
            "total_compressed_bytes": total_compressed,
            "default_ttl_seconds": self._default_ttl,
        }

    def purge_expired(self) -> int:
        """Remove all expired entries. Returns count removed."""
        stale = [k for k, v in self._store.items() if v.is_expired()]
        for k in stale:
            del self._store[k]
        return len(stale)
