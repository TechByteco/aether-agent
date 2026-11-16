"""Unit tests for production scaling features: cache, rate limiting, retry, telemetry, intelligence."""

import asyncio
import time
from obscura_engine.cache import SnapshotCache, ResponseCache
from obscura_engine.retry import RetryPolicy, NavigationError
from obscura_engine.rate_limiter import SlidingWindowRateLimiter, AgentRateLimiter
from obscura_engine.telemetry import MetricsRegistry, EngineCounter
from obscura_engine.page_analyzer import PageAnalyzer
from obscura_engine.js_executor import JsExecutor
from obscura_engine.crawler import CrawlPolicy, WebCrawler
from obscura_engine.types import DistilledSnapshot, InteractiveElement


def test_snapshot_cache():
    cache = SnapshotCache(max_size=3, ttl=60.0)
    url = "https://example.com/test"
    content = "<html><body>Hello Cache</body></html>"

    assert cache.get(url, content) is None
    cache.set(url, content)

    cached = cache.get(url, content)
    assert cached is not None
    assert cached.content == content.encode()

    stats = cache.get_stats()
    assert stats["hits"] == 1
    assert stats["misses"] == 1
    assert stats["size"] == 1


def test_retry_policy():
    policy = RetryPolicy(max_attempts=3, base_delay=0.1, jitter=False)
    assert policy.compute_delay(0) == 0.1
    assert policy.compute_delay(1) == 0.2
    assert policy.compute_delay(2) == 0.4


async def test_rate_limiter():
    limiter = SlidingWindowRateLimiter(requests_per_second=5, requests_per_minute=10)
    domain = "api.test"

    # Must allow first request
    allowed = await limiter.check_and_consume(domain)
    assert allowed is True


def test_telemetry_metrics():
    registry = MetricsRegistry()
    counter = registry.counter("test_units_total", "Test counter")
    counter.inc(labels={"module": "test"})
    assert counter.get(labels={"module": "test"}) >= 1

    summary = registry.json_summary()
    assert "counters" in summary
    assert "gauges" in summary


def test_page_analyzer():
    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <title>How to Build AI Browsers</title>
        <meta name="description" content="A guide to modern headless browser engines.">
        <meta property="og:title" content="AI Browsers Guide">
    </head>
    <body>
        <article>
            <h1>How to Build AI Browsers</h1>
            <p>Autonomous agents require lightweight and token-optimized execution runtimes. Traditional headless browsers consume too much memory.</p>
        </article>
    </body>
    </html>
    """
    analyzer = PageAnalyzer()
    snap = DistilledSnapshot(
        url="https://example.com/article",
        title="How to Build AI Browsers",
        markdown="Published on Oct 2026 by Author. How to Build AI Browsers. Read more comments.",
        interactive_elements=[]
    )
    ptype = analyzer.detect_page_type(snap)
    assert ptype in ("article", "generic")

    meta = analyzer.extract_metadata(html)
    assert meta.get("og_title") == "AI Browsers Guide"
    assert meta.get("og_description") == "A guide to modern headless browser engines."


def test_js_executor():
    html = """
    <html>
    <head>
        <title>Structured Test</title>
        <script type="application/ld+json">
        {
            "@context": "https://schema.org",
            "@type": "Product",
            "name": "Super Engine",
            "price": "99.00"
        }
        </script>
        <meta property="og:site_name" content="TechByte" />
    </head>
    <body>
        <button id="buy">Buy</button>
    </body>
    </html>
    """
    js = JsExecutor(html)
    json_ld = js.extract_json_ld()
    assert len(json_ld) == 1
    assert json_ld[0]["name"] == "Super Engine"

    og = js.get_open_graph()
    assert og.get("og:site_name") == "TechByte"
    assert js.count_elements("button") == 1
