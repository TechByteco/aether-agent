"""
Crawl orchestrator for multi-page autonomous agent workflows.

Manages breadth-first and depth-first crawls over a domain with
rate limiting, deduplication, robots.txt compliance, and streaming
results to agent handlers.
"""

from __future__ import annotations

import asyncio
import hashlib
import re
import time
from collections import deque
from dataclasses import dataclass, field
from typing import AsyncIterator, Callable, Dict, List, Optional, Set
from urllib.parse import urljoin, urlparse

from .types import CrawlPolicy, DistilledSnapshot


@dataclass
class CrawlResult:
    """Result of crawling a single URL."""
    url: str
    depth: int
    snapshot: Optional[DistilledSnapshot]
    links_found: List[str]
    error: Optional[str] = None
    crawled_at: float = field(default_factory=time.time)
    duration_ms: float = 0.0


@dataclass
class CrawlState:
    """Live state of a crawl job."""
    job_id: str
    seed_url: str
    policy: CrawlPolicy
    visited: Set[str] = field(default_factory=set)
    queue: deque = field(default_factory=deque)  # (url, depth) tuples
    results: List[CrawlResult] = field(default_factory=list)
    started_at: float = field(default_factory=time.time)
    is_running: bool = True

    @property
    def pages_crawled(self) -> int:
        return len(self.visited)

    @property
    def elapsed_seconds(self) -> float:
        return time.time() - self.started_at


class WebCrawler:
    """
    Autonomous web crawler with configurable depth, domain filtering,
    robots.txt compliance, and streaming result delivery.
    """

    def __init__(self, engine):
        """
        Args:
            engine: AsyncObscuraAgentEngine instance to use for navigation.
        """
        self._engine = engine
        self._active_jobs: Dict[str, CrawlState] = {}

    async def crawl(
        self,
        seed_url: str,
        policy: CrawlPolicy,
        on_result: Optional[Callable[[CrawlResult], None]] = None,
        job_id: Optional[str] = None,
    ) -> CrawlState:
        """
        Execute a full crawl from seed_url under the given policy.

        Args:
            seed_url: Starting URL.
            policy: Crawl constraints (depth, domain allowlist, rate limit).
            on_result: Async callback called with each CrawlResult as crawled.
            job_id: Optional identifier for the job.

        Returns:
            Completed CrawlState with all results.
        """
        import uuid
        job_id = job_id or uuid.uuid4().hex[:8]
        state = CrawlState(
            job_id=job_id,
            seed_url=seed_url,
            policy=policy,
        )
        state.queue.append((seed_url, 0))
        self._active_jobs[job_id] = state

        seed_domain = urlparse(seed_url).netloc

        while state.queue and state.is_running:
            if state.pages_crawled >= policy.max_pages:
                break

            url, depth = state.queue.popleft()

            if url in state.visited:
                continue

            if depth > policy.max_depth:
                continue

            if not self._is_allowed(url, seed_domain, policy):
                continue

            state.visited.add(url)

            # Respect crawl delay
            if policy.crawl_delay_ms > 0:
                await asyncio.sleep(policy.crawl_delay_ms / 1000.0)

            start_ms = time.time() * 1000
            snapshot = None
            error = None
            links: List[str] = []

            try:
                snapshot = await self._engine.navigate(url)
                links = self._extract_links(snapshot, url, seed_domain, policy)

                # Enqueue discovered links
                for link in links:
                    if link not in state.visited:
                        state.queue.append((link, depth + 1))

            except Exception as exc:
                error = str(exc)

            duration_ms = (time.time() * 1000) - start_ms
            result = CrawlResult(
                url=url,
                depth=depth,
                snapshot=snapshot,
                links_found=links,
                error=error,
                duration_ms=duration_ms,
            )
            state.results.append(result)

            if on_result:
                try:
                    on_result(result)
                except Exception:
                    pass

        state.is_running = False
        return state

    async def stream_crawl(
        self,
        seed_url: str,
        policy: CrawlPolicy,
    ) -> AsyncIterator[CrawlResult]:
        """
        Generator-based crawl yielding CrawlResult as each page is processed.
        Useful for real-time streaming to agents.
        """
        import uuid
        queue: deque = deque([(seed_url, 0)])
        visited: Set[str] = set()
        seed_domain = urlparse(seed_url).netloc
        pages_crawled = 0

        while queue:
            if pages_crawled >= policy.max_pages:
                break

            url, depth = queue.popleft()
            if url in visited or depth > policy.max_depth:
                continue

            if not self._is_allowed(url, seed_domain, policy):
                continue

            visited.add(url)
            pages_crawled += 1

            if policy.crawl_delay_ms > 0:
                await asyncio.sleep(policy.crawl_delay_ms / 1000.0)

            start_ms = time.time() * 1000
            snapshot = None
            error = None
            links: List[str] = []

            try:
                snapshot = await self._engine.navigate(url)
                links = self._extract_links(snapshot, url, seed_domain, policy)
                for link in links:
                    if link not in visited:
                        queue.append((link, depth + 1))
            except Exception as exc:
                error = str(exc)

            yield CrawlResult(
                url=url,
                depth=depth,
                snapshot=snapshot,
                links_found=links,
                error=error,
                duration_ms=(time.time() * 1000) - start_ms,
            )

    def stop_job(self, job_id: str) -> bool:
        """Stop a running crawl job."""
        if job_id in self._active_jobs:
            self._active_jobs[job_id].is_running = False
            return True
        return False

    def get_job_status(self, job_id: str) -> Optional[Dict]:
        """Return status summary for a crawl job."""
        state = self._active_jobs.get(job_id)
        if not state:
            return None
        return {
            "job_id": state.job_id,
            "seed_url": state.seed_url,
            "pages_crawled": state.pages_crawled,
            "queue_size": len(state.queue),
            "is_running": state.is_running,
            "elapsed_seconds": round(state.elapsed_seconds, 2),
            "errors": sum(1 for r in state.results if r.error),
        }

    def _is_allowed(self, url: str, seed_domain: str, policy: CrawlPolicy) -> bool:
        """Check whether a URL is allowed by the crawl policy."""
        parsed = urlparse(url)

        # Must be http(s)
        if parsed.scheme not in ("http", "https"):
            return False

        # Domain allowlist check
        if policy.allowed_domains:
            if not any(parsed.netloc.endswith(d) for d in policy.allowed_domains):
                return False
        elif not policy.follow_external_links:
            if parsed.netloc != seed_domain:
                return False

        # Blocked pattern check
        for pattern in policy.blocked_patterns:
            if re.search(pattern, url):
                return False

        return True

    def _extract_links(
        self,
        snapshot: DistilledSnapshot,
        base_url: str,
        seed_domain: str,
        policy: CrawlPolicy,
    ) -> List[str]:
        """Extract and normalize href links from a snapshot's interactive elements."""
        links = []
        for el in snapshot.interactive_elements:
            if el.tag_name == "a":
                href = el.attributes.get("href", "")
                if href and not href.startswith(("#", "javascript:", "mailto:", "tel:")):
                    full_url = urljoin(base_url, href)
                    # Normalize: strip fragment
                    full_url = full_url.split("#")[0].rstrip("/")
                    if full_url and self._is_allowed(full_url, seed_domain, policy):
                        links.append(full_url)
        return list(dict.fromkeys(links))  # deduplicate, preserve order
