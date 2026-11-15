"""
AETHER Tool Result Cache
=========================
Lightweight in-memory + disk LRU cache for deterministic tool calls.

Why: On a 3B local model, some tools (SEO generation, lead discovery, blueprint)
take 10-30 seconds. If the same args are passed again within the TTL window,
return the cached result immediately with zero LLM overhead.

Rules:
- Only caches DETERMINISTIC=True results (identical inputs → identical outputs).
- TTL is configurable per tool. Default: 30 minutes.
- Max 500 entries in memory; oldest evicted first.
- Persists to disk on shutdown so cold-start hits the cache too.
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger("aether.tool_cache")

_WORKSPACE  = Path(__file__).resolve().parents[3]
_CACHE_FILE = _WORKSPACE / "data" / "leon_intelligence" / "tool_cache.json"
_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)

# Default TTLs per tool category (seconds)
_DEFAULT_TTL = 1800          # 30 min
_TOOL_TTL: Dict[str, int] = {
    "tool_leon_generate_business_ideas": 3600,
    "tool_leon_business_blueprint":      3600,
    "tool_leon_customize_brand":         7200,
    "tool_leon_find_leads":               900,
    "tool_leon_generate_seo_and_web_spec": 3600,
    "tool_get_system_vitals":              60,
    "tool_agi_asset_registry_summary":    120,
}
_MAX_ENTRIES = 500
_LOCK = threading.Lock()


def _key(tool_name: str, kwargs: Dict[str, Any]) -> str:
    payload = json.dumps({"t": tool_name, "a": kwargs}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


class ToolCache:
    def __init__(self) -> None:
        self._store: Dict[str, Tuple[Any, float]] = {}  # key → (result, expires_at)
        self._hits = 0
        self._misses = 0
        self._load()

    def _load(self) -> None:
        try:
            if _CACHE_FILE.exists():
                raw = json.loads(_CACHE_FILE.read_text(encoding="utf-8"))
                now = time.time()
                self._store = {k: (v["r"], v["e"]) for k, v in raw.items() if v["e"] > now}
                logger.debug("Tool cache loaded: %d valid entries", len(self._store))
        except Exception as e:
            logger.debug("Tool cache load failed: %s", e)

    def save(self) -> None:
        try:
            serializable = {k: {"r": v[0], "e": v[1]} for k, v in self._store.items()
                            if isinstance(v[0], (str, int, float, bool, dict, list, type(None)))}
            _CACHE_FILE.write_text(json.dumps(serializable, ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            logger.debug("Tool cache save failed: %s", e)

    def get(self, tool_name: str, kwargs: Dict[str, Any]) -> Optional[Any]:
        k = _key(tool_name, kwargs)
        with _LOCK:
            entry = self._store.get(k)
            if entry and entry[1] > time.time():
                self._hits += 1
                return entry[0]
            self._misses += 1
            return None

    def set(self, tool_name: str, kwargs: Dict[str, Any], result: Any) -> None:
        k = _key(tool_name, kwargs)
        ttl = _TOOL_TTL.get(tool_name, _DEFAULT_TTL)
        with _LOCK:
            # Evict oldest if at capacity
            if len(self._store) >= _MAX_ENTRIES:
                oldest = sorted(self._store.items(), key=lambda x: x[1][1])[:50]
                for ok, _ in oldest:
                    del self._store[ok]
            self._store[k] = (result, time.time() + ttl)

    def stats(self) -> Dict[str, Any]:
        return {
            "entries": len(self._store),
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(self._hits / max(1, self._hits + self._misses), 3),
        }

    def invalidate(self, tool_name: Optional[str] = None) -> int:
        """Remove all entries for a tool (or everything if tool_name is None)."""
        with _LOCK:
            if tool_name is None:
                n = len(self._store); self._store.clear(); return n
            before = len(self._store)
            self._store = {k: v for k, v in self._store.items()
                           if not k.startswith(_key(tool_name, {})[:8])}
            return before - len(self._store)


tool_cache = ToolCache()


def cached_call(tool_name: str, fn, **kwargs) -> Any:
    """
    Call fn(**kwargs) with transparent cache.
    Only caches when AETHER_DETERMINISTIC=1 (default).
    """
    try:
        from aether.system.deterministic_mode import DETERMINISTIC
        if not DETERMINISTIC:
            return fn(**kwargs)
    except ImportError:
        pass

    hit = tool_cache.get(tool_name, kwargs)
    if hit is not None:
        logger.debug("Cache HIT for %s", tool_name)
        return hit
    result = fn(**kwargs)
    tool_cache.set(tool_name, kwargs, result)
    return result
