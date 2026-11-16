"""Structured metrics and telemetry for the Obscura Enchanted Agent Engine.

Provides Prometheus-compatible counters, histograms, and gauges with
a singleton MetricsRegistry. Emits both Prometheus text exposition format
and compact JSON snapshots.
"""

from __future__ import annotations

import bisect
import json
import math
import threading
import time
from collections import defaultdict
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# EngineCounter
# ---------------------------------------------------------------------------

class EngineCounter:
    """Thread-safe atomic counter with label-set support.

    Example::

        nav_total = EngineCounter("navigations_total", "Total navigation requests")
        nav_total.inc(labels={"status": "ok"})
        nav_total.inc(labels={"status": "error"})
        nav_total.get(labels={"status": "ok"})  # -> 1
    """

    def __init__(self, name: str, help: str = "") -> None:
        self.name = name
        self.help = help
        self._lock = threading.Lock()
        # key -> int  (key is a frozenset of label items)
        self._values: Dict[frozenset, int] = defaultdict(int)

    def _key(self, labels: Optional[Dict[str, str]]) -> frozenset:
        return frozenset((labels or {}).items())

    def inc(self, amount: int = 1, labels: Optional[Dict[str, str]] = None) -> None:
        """Increment counter by *amount* (default 1)."""
        with self._lock:
            self._values[self._key(labels)] += amount

    def get(self, labels: Optional[Dict[str, str]] = None) -> int:
        """Return current value for given label combination."""
        with self._lock:
            return self._values[self._key(labels)]

    def reset(self, labels: Optional[Dict[str, str]] = None) -> None:
        """Reset a specific label combination to zero."""
        with self._lock:
            self._values[self._key(labels)] = 0

    def _samples(self) -> List[Tuple[Dict[str, str], int]]:
        with self._lock:
            return [(dict(k), v) for k, v in self._values.items()]


# ---------------------------------------------------------------------------
# EngineHistogram
# ---------------------------------------------------------------------------

class EngineHistogram:
    """Latency histogram with p50 / p95 / p99 percentile computation.

    Observations are stored as a sorted list (up to *max_samples* most recent
    values) so that exact percentiles can be computed on demand without
    approximation. This is appropriate for engine-local metrics; for
    high-cardinality production use, swap the backing store for a sketch.

    Example::

        nav_lat = EngineHistogram("navigation_latency_ms", "Nav round-trip ms")
        nav_lat.observe(142.3)
        nav_lat.observe(87.1)
        nav_lat.percentile(0.95)  # -> 142.3
    """

    def __init__(
        self,
        name: str,
        help: str = "",
        max_samples: int = 10_000,
    ) -> None:
        self.name = name
        self.help = help
        self._max = max_samples
        self._lock = threading.Lock()
        self._observations: List[float] = []  # kept sorted via bisect
        self._count: int = 0
        self._sum: float = 0.0

    def observe(self, value: float) -> None:
        """Record a single observation."""
        with self._lock:
            bisect.insort(self._observations, value)
            if len(self._observations) > self._max:
                self._observations.pop(0)  # drop oldest (smallest)
            self._count += 1
            self._sum += value

    def percentile(self, q: float) -> float:
        """Return the *q*-th percentile (0.0–1.0) of observed values."""
        with self._lock:
            if not self._observations:
                return 0.0
            idx = int(math.ceil(q * len(self._observations))) - 1
            idx = max(0, min(idx, len(self._observations) - 1))
            return self._observations[idx]

    @property
    def p50(self) -> float:
        return self.percentile(0.50)

    @property
    def p95(self) -> float:
        return self.percentile(0.95)

    @property
    def p99(self) -> float:
        return self.percentile(0.99)

    @property
    def count(self) -> int:
        with self._lock:
            return self._count

    @property
    def total(self) -> float:
        with self._lock:
            return self._sum

    @property
    def mean(self) -> float:
        with self._lock:
            return (self._sum / self._count) if self._count else 0.0

    def snapshot(self) -> Dict[str, float]:
        return {
            "count": self.count,
            "sum": round(self.total, 3),
            "mean": round(self.mean, 3),
            "p50": round(self.p50, 3),
            "p95": round(self.p95, 3),
            "p99": round(self.p99, 3),
        }


# ---------------------------------------------------------------------------
# EngineGauge
# ---------------------------------------------------------------------------

class EngineGauge:
    """Thread-safe live-value gauge with label support.

    Example::

        active_tabs = EngineGauge("active_tabs", "Number of open tabs")
        active_tabs.set(5)
        active_tabs.inc()   # -> 6
        active_tabs.dec(2)  # -> 4
    """

    def __init__(self, name: str, help: str = "") -> None:
        self.name = name
        self.help = help
        self._lock = threading.Lock()
        self._values: Dict[frozenset, float] = defaultdict(float)

    def _key(self, labels: Optional[Dict[str, str]]) -> frozenset:
        return frozenset((labels or {}).items())

    def set(self, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        with self._lock:
            self._values[self._key(labels)] = value

    def inc(self, amount: float = 1.0, labels: Optional[Dict[str, str]] = None) -> None:
        with self._lock:
            self._values[self._key(labels)] += amount

    def dec(self, amount: float = 1.0, labels: Optional[Dict[str, str]] = None) -> None:
        with self._lock:
            self._values[self._key(labels)] -= amount

    def get(self, labels: Optional[Dict[str, str]] = None) -> float:
        with self._lock:
            return self._values[self._key(labels)]

    def _samples(self) -> List[Tuple[Dict[str, str], float]]:
        with self._lock:
            return [(dict(k), v) for k, v in self._values.items()]


# ---------------------------------------------------------------------------
# MetricsRegistry
# ---------------------------------------------------------------------------

class MetricsRegistry:
    """Singleton registry holding all engine metrics.

    Access via :func:`get_registry`. Automatically pre-registers the
    standard Obscura Engine metric set on first instantiation.
    """

    _instance: Optional["MetricsRegistry"] = None
    _instance_lock = threading.Lock()

    def __new__(cls) -> "MetricsRegistry":
        with cls._instance_lock:
            if cls._instance is None:
                instance = super().__new__(cls)
                instance._counters: Dict[str, EngineCounter] = {}
                instance._histograms: Dict[str, EngineHistogram] = {}
                instance._gauges: Dict[str, EngineGauge] = {}
                instance._start_time: float = time.time()
                cls._instance = instance
                instance._register_defaults()
            return cls._instance

    # ------------------------------------------------------------------
    # Registration helpers
    # ------------------------------------------------------------------

    def counter(self, name: str, help: str = "") -> EngineCounter:
        if name not in self._counters:
            self._counters[name] = EngineCounter(name, help)
        return self._counters[name]

    def histogram(self, name: str, help: str = "") -> EngineHistogram:
        if name not in self._histograms:
            self._histograms[name] = EngineHistogram(name, help)
        return self._histograms[name]

    def gauge(self, name: str, help: str = "") -> EngineGauge:
        if name not in self._gauges:
            self._gauges[name] = EngineGauge(name, help)
        return self._gauges[name]

    # ------------------------------------------------------------------
    # Pre-registered Obscura Engine metrics
    # ------------------------------------------------------------------

    def _register_defaults(self) -> None:
        # Counters
        self.counter("navigations_total", "Total navigation requests")
        self.counter("actions_total", "Total atomic browser actions executed")
        self.counter("cache_hits_total", "Snapshot cache hit count")
        self.counter("cache_misses_total", "Snapshot cache miss count")
        self.counter("errors_total", "Total errors by type")
        self.counter("sessions_created_total", "Total tab sessions ever created")

        # Histograms
        self.histogram("navigation_latency_ms", "End-to-end navigation latency in milliseconds")
        self.histogram("snapshot_token_savings_pct", "Token savings percentage per snapshot distillation")
        self.histogram("action_latency_ms", "Latency per atomic browser action in milliseconds")

        # Gauges
        self.gauge("active_sessions", "Number of currently active tab sessions")
        self.gauge("memory_mb", "Estimated total memory usage across all active tabs (MB)")
        self.gauge("action_success_rate", "Rolling action success rate [0.0–1.0]")
        self.gauge("cache_hit_rate", "Rolling cache hit rate [0.0–1.0]")

    # ------------------------------------------------------------------
    # Convenience accessors for standard metrics
    # ------------------------------------------------------------------

    @property
    def navigations_total(self) -> EngineCounter:
        return self._counters["navigations_total"]

    @property
    def navigation_latency_ms(self) -> EngineHistogram:
        return self._histograms["navigation_latency_ms"]

    @property
    def snapshot_token_savings_pct(self) -> EngineHistogram:
        return self._histograms["snapshot_token_savings_pct"]

    @property
    def actions_total(self) -> EngineCounter:
        return self._counters["actions_total"]

    @property
    def active_sessions(self) -> EngineGauge:
        return self._gauges["active_sessions"]

    @property
    def memory_mb(self) -> EngineGauge:
        return self._gauges["memory_mb"]

    @property
    def cache_hit_rate(self) -> EngineGauge:
        return self._gauges["cache_hit_rate"]

    @property
    def action_success_rate(self) -> EngineGauge:
        return self._gauges["action_success_rate"]

    # ------------------------------------------------------------------
    # Export formats
    # ------------------------------------------------------------------

    def prometheus_text_format(self) -> str:
        """Emit metrics in Prometheus text exposition format (0.0.4)."""
        lines: List[str] = []
        ts = int(time.time() * 1000)

        # Uptime
        lines.append("# HELP obscura_uptime_seconds Engine uptime in seconds")
        lines.append("# TYPE obscura_uptime_seconds gauge")
        lines.append(f"obscura_uptime_seconds {time.time() - self._start_time:.3f} {ts}")
        lines.append("")

        for name, ctr in self._counters.items():
            safe = f"obscura_{name}"
            lines.append(f"# HELP {safe} {ctr.help}")
            lines.append(f"# TYPE {safe} counter")
            for labels, value in ctr._samples():
                label_str = _format_labels(labels)
                lines.append(f"{safe}{label_str} {value} {ts}")
            lines.append("")

        for name, hist in self._histograms.items():
            safe = f"obscura_{name}"
            lines.append(f"# HELP {safe} {hist.help}")
            lines.append(f"# TYPE {safe} summary")
            snap = hist.snapshot()
            lines.append(f'{safe}{{quantile="0.5"}} {snap["p50"]} {ts}')
            lines.append(f'{safe}{{quantile="0.95"}} {snap["p95"]} {ts}')
            lines.append(f'{safe}{{quantile="0.99"}} {snap["p99"]} {ts}')
            lines.append(f'{safe}_sum {snap["sum"]} {ts}')
            lines.append(f'{safe}_count {snap["count"]} {ts}')
            lines.append("")

        for name, gauge in self._gauges.items():
            safe = f"obscura_{name}"
            lines.append(f"# HELP {safe} {gauge.help}")
            lines.append(f"# TYPE {safe} gauge")
            for labels, value in gauge._samples():
                label_str = _format_labels(labels)
                lines.append(f"{safe}{label_str} {value:.4f} {ts}")
            lines.append("")

        return "\n".join(lines)

    def json_summary(self) -> dict:
        """Return a compact JSON snapshot of all metrics."""
        counters_out = {}
        for name, ctr in self._counters.items():
            samples = ctr._samples()
            if len(samples) == 1 and not samples[0][0]:
                counters_out[name] = samples[0][1]
            else:
                counters_out[name] = {_labels_key(lbl): v for lbl, v in samples}

        histograms_out = {name: h.snapshot() for name, h in self._histograms.items()}

        gauges_out = {}
        for name, g in self._gauges.items():
            samples = g._samples()
            if len(samples) == 1 and not samples[0][0]:
                gauges_out[name] = round(samples[0][1], 4)
            else:
                gauges_out[name] = {_labels_key(lbl): round(v, 4) for lbl, v in samples}

        return {
            "timestamp": time.time(),
            "uptime_seconds": round(time.time() - self._start_time, 2),
            "counters": counters_out,
            "histograms": histograms_out,
            "gauges": gauges_out,
        }


# ---------------------------------------------------------------------------
# Module-level singleton accessor
# ---------------------------------------------------------------------------

def get_registry() -> MetricsRegistry:
    """Return the global MetricsRegistry singleton."""
    return MetricsRegistry()


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _format_labels(labels: Dict[str, str]) -> str:
    if not labels:
        return ""
    parts = [f'{k}="{v}"' for k, v in sorted(labels.items())]
    return "{" + ",".join(parts) + "}"


def _labels_key(labels: Dict[str, str]) -> str:
    if not labels:
        return "__total__"
    return ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
