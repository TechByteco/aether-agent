"""Per-agent browsing memory for the Obscura Enchanted Agent Engine.

Maintains a lightweight, in-process episodic memory of a single agent's
browsing session: visited URLs with timestamps, form-fill history,
extracted facts, and a navigation graph.  No persistence layer is required;
callers that want durability should serialise / deserialise the instance.
"""

from __future__ import annotations

import re
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Internal data holders
# ---------------------------------------------------------------------------

@dataclass
class _VisitRecord:
    """A single entry in the browsing history."""
    url: str
    title: str
    snapshot_summary: str
    timestamp: float = field(default_factory=time.time)


# ---------------------------------------------------------------------------
# BrowsingMemory
# ---------------------------------------------------------------------------

class BrowsingMemory:
    """Episodic browsing memory for one autonomous agent.

    Attributes
    ----------
    visited_urls:
        Ordered deque (newest-last) of ``_VisitRecord`` objects; capped at
        100 entries.
    form_data_history:
        Mapping of *url* -> ``{field_name: last_value}`` for auto-fill hints.
    extracted_facts:
        List of ``(url, field_name, value)`` tuples; capped at 500 entries.
    navigation_graph:
        Adjacency mapping of ``url -> [urls navigated to from that url]``.
    """

    _MAX_VISITS: int = 100
    _MAX_FACTS: int = 500
    _CONTEXT_WINDOW: int = 5  # pages shown in get_context_summary

    def __init__(self) -> None:
        self.visited_urls: Deque[_VisitRecord] = deque(maxlen=self._MAX_VISITS)
        self.form_data_history: Dict[str, Dict[str, str]] = {}
        self.extracted_facts: List[Tuple[str, str, str]] = []
        self.navigation_graph: Dict[str, List[str]] = {}
        self._last_url: Optional[str] = None

    # ------------------------------------------------------------------
    # Mutation helpers
    # ------------------------------------------------------------------

    def add_visit(self, url: str, title: str, snapshot_summary: str) -> None:
        """Record a page visit.

        Parameters
        ----------
        url:
            The canonical URL of the page visited.
        title:
            The ``<title>`` or ``og:title`` of the page.
        snapshot_summary:
            A short (1-3 sentence) human-readable summary of the page content.
        """
        record = _VisitRecord(
            url=url,
            title=title,
            snapshot_summary=snapshot_summary,
        )
        self.visited_urls.append(record)

        # Update navigation graph
        if self._last_url and self._last_url != url:
            self.navigation_graph.setdefault(self._last_url, [])
            if url not in self.navigation_graph[self._last_url]:
                self.navigation_graph[self._last_url].append(url)

        self._last_url = url

    def record_form_fill(self, url: str, field_name: str, value: str) -> None:
        """Store a field value that was entered into a form.

        Allows the agent to auto-suggest previously entered values for
        recurring fields (e.g. search queries, usernames).
        """
        self.form_data_history.setdefault(url, {})[field_name] = value

    def record_fact(self, url: str, field_name: str, value: str) -> None:
        """Persist a structured fact extracted from a page.

        Parameters
        ----------
        url:
            Source URL.
        field_name:
            Semantic label for the value (e.g. ``"price"``, ``"author"``).
        value:
            Extracted string value.
        """
        self.extracted_facts.append((url, field_name, value))
        # Trim to cap
        if len(self.extracted_facts) > self._MAX_FACTS:
            self.extracted_facts = self.extracted_facts[-self._MAX_FACTS :]

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    def get_context_summary(self) -> str:
        """Return a plain-text summary of recent browsing activity.

        Includes the last ``_CONTEXT_WINDOW`` pages (most recent last)
        and the current navigation-graph edge count.
        """
        if not self.visited_urls:
            return "No pages visited yet."

        recent = list(self.visited_urls)[-self._CONTEXT_WINDOW :]
        lines: List[str] = ["=== Browsing Context ==="]
        for i, rec in enumerate(recent, 1):
            ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(rec.timestamp))
            lines.append(
                f"{i}. [{ts}] {rec.title!r}\n"
                f"   URL: {rec.url}\n"
                f"   Summary: {rec.snapshot_summary}"
            )

        edge_count = sum(len(v) for v in self.navigation_graph.values())
        lines.append(
            f"\nNavigation graph: {len(self.navigation_graph)} nodes, "
            f"{edge_count} edges."
        )
        lines.append(f"Total visits recorded: {len(self.visited_urls)}")
        lines.append(f"Extracted facts: {len(self.extracted_facts)}")
        return "\n".join(lines)

    def get_form_hints(self, url: str) -> Dict[str, str]:
        """Return previously entered field values for *url* (may be empty)."""
        return dict(self.form_data_history.get(url, {}))

    def find_similar_visited(self, url: str) -> Optional[str]:
        """Return the most similar previously visited URL, or ``None``.

        Uses a simple token-overlap heuristic (Jaccard similarity on
        URL path segments) rather than an external fuzzy-match library.

        Parameters
        ----------
        url:
            Candidate URL to match against history.

        Returns
        -------
        str | None
            The closest historic URL if similarity > 0.4, else ``None``.
        """
        if not self.visited_urls:
            return None

        def _tokenise(u: str) -> set[str]:
            # Strip scheme and split on non-alphanumeric chars
            u = re.sub(r"^https?://", "", u)
            return set(re.split(r"[^a-zA-Z0-9]+", u.lower())) - {"", "www"}

        query_tokens = _tokenise(url)
        if not query_tokens:
            return None

        best_score = 0.0
        best_url: Optional[str] = None

        seen: set[str] = set()
        for rec in self.visited_urls:
            if rec.url in seen or rec.url == url:
                continue
            seen.add(rec.url)

            hist_tokens = _tokenise(rec.url)
            if not hist_tokens:
                continue

            intersection = query_tokens & hist_tokens
            union = query_tokens | hist_tokens
            score = len(intersection) / len(union)

            if score > best_score:
                best_score = score
                best_url = rec.url

        return best_url if best_score > 0.4 else None

    # ------------------------------------------------------------------
    # Serialisation helpers
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        """Serialise memory to a plain dict (JSON-safe)."""
        return {
            "visited_urls": [
                {
                    "url": r.url,
                    "title": r.title,
                    "snapshot_summary": r.snapshot_summary,
                    "timestamp": r.timestamp,
                }
                for r in self.visited_urls
            ],
            "form_data_history": self.form_data_history,
            "extracted_facts": self.extracted_facts,
            "navigation_graph": self.navigation_graph,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "BrowsingMemory":
        """Reconstruct a ``BrowsingMemory`` instance from a serialised dict."""
        mem = cls()
        for entry in data.get("visited_urls", []):
            rec = _VisitRecord(
                url=entry["url"],
                title=entry["title"],
                snapshot_summary=entry["snapshot_summary"],
                timestamp=entry.get("timestamp", time.time()),
            )
            mem.visited_urls.append(rec)
        mem.form_data_history = data.get("form_data_history", {})
        mem.extracted_facts = [tuple(f) for f in data.get("extracted_facts", [])]  # type: ignore[misc]
        mem.navigation_graph = data.get("navigation_graph", {})
        if mem.visited_urls:
            mem._last_url = mem.visited_urls[-1].url
        return mem
