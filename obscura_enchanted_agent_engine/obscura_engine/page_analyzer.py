"""Semantic page intelligence for the Obscura Enchanted Agent Engine.

Provides heuristic-based page-type detection, content extraction,
language identification, summarisation, and metadata extraction —
all with zero external ML dependencies beyond beautifulsoup4/lxml.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from typing import TYPE_CHECKING, Any

from bs4 import BeautifulSoup, Comment, Tag

if TYPE_CHECKING:
    from obscura_engine.types import DistilledSnapshot

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_STOP_TAGS = {
    "script", "style", "noscript", "iframe", "svg", "canvas",
    "header", "footer", "nav", "aside", "form", "figure", "figcaption",
}

_NOISE_CLASS_RE = re.compile(
    r"(nav|navbar|navigation|footer|sidebar|widget|ad|advertisement|"
    r"cookie|popup|modal|banner|promo|related|comment|social|share|"
    r"breadcrumb|pagination|newsletter|subscribe)",
    re.IGNORECASE,
)


def _is_noise_tag(tag: Tag) -> bool:
    """Return True if *tag* is a navigational / boilerplate node."""
    classes = " ".join(tag.get("class", []))
    tag_id = tag.get("id", "")
    return bool(_NOISE_CLASS_RE.search(classes) or _NOISE_CLASS_RE.search(str(tag_id)))


def _clean_text(raw: str) -> str:
    """Collapse whitespace and strip zero-width chars from *raw*."""
    raw = unicodedata.normalize("NFKC", raw)
    return re.sub(r"\s+", " ", raw).strip()


# ---------------------------------------------------------------------------
# Language profiles (character n-gram fingerprints for top-6 languages)
# ---------------------------------------------------------------------------

# Trigrams that strongly indicate a given language (hand-curated minimal sets).
_LANG_NGRAMS: dict[str, set[str]] = {
    "en": {"the", "and", "ing", "ion", "ati", "for", "tha", "ent", "tio"},
    "fr": {"les", "des", "que", "ent", "ion", "our", "ant", "ons", "ais"},
    "de": {"die", "der", "und", "ein", "sch", "ich", "ist", "hen", "ver"},
    "es": {"los", "las", "que", "ión", "del", "nte", "con", "par", "est"},
    "ar": {"ال", "في", "من", "على", "إل", "هذ", "كا", "لا", "أن"},
    "zh": set("的一了是我不在人们有来他这上着个地到大里说去子也和那要下看天时过出小"),
}


# ---------------------------------------------------------------------------
# PageAnalyzer
# ---------------------------------------------------------------------------

class PageAnalyzer:
    """Collection of heuristic page-intelligence utilities.

    All methods are pure functions (stateless) and safe for concurrent use.
    """

    # ------------------------------------------------------------------
    # Page-type detection
    # ------------------------------------------------------------------

    _PAGE_TYPE_SIGNALS: dict[str, list[str]] = {
        "login_form": [
            "password", "login", "sign in", "sign-in", "log in", "log-in",
            "forgot password", "remember me",
        ],
        "checkout": [
            "checkout", "payment", "billing", "credit card", "place order",
            "shipping address", "cvv", "card number",
        ],
        "search_results": [
            "search results", "results for", "showing", "found", " results",
            "did you mean",
        ],
        "product_listing": [
            "add to cart", "add to basket", "buy now", "price", "product",
            "in stock", "out of stock", "rating", "reviews",
        ],
        "dashboard": [
            "dashboard", "analytics", "overview", "settings", "profile",
            "notifications", "activity", "metrics",
        ],
        "article": [
            "published", "author", "byline", "read more", "share", "comment",
            "minutes to read", "posted on",
        ],
        "error": [
            "404", "not found", "403", "forbidden", "500", "internal server",
            "page not found", "access denied", "error",
        ],
    }

    def detect_page_type(self, snapshot: "DistilledSnapshot") -> str:
        """Classify the page represented by *snapshot*.

        Returns one of: ``"article"``, ``"search_results"``,
        ``"product_listing"``, ``"login_form"``, ``"checkout"``,
        ``"dashboard"``, ``"error"``, ``"generic"``.
        """
        haystack = (snapshot.title + " " + snapshot.markdown).lower()

        scores: dict[str, int] = {}
        for page_type, signals in self._PAGE_TYPE_SIGNALS.items():
            score = sum(1 for sig in signals if sig in haystack)
            if score:
                scores[page_type] = score

        if not scores:
            return "generic"

        winner = max(scores, key=lambda k: scores[k])
        # Require at least 2 matching signals for high-confidence types;
        # fall back to generic on a single weak hit for most types.
        if scores[winner] < 2 and winner not in {"error", "login_form"}:
            return "generic"
        return winner

    # ------------------------------------------------------------------
    # Main-content extraction
    # ------------------------------------------------------------------

    def extract_main_content(self, html: str) -> str:
        """Extract the primary readable text from *html*.

        Strips navigation, ads, footers, and boilerplate.  Returns
        clean, collapsed plain text.
        """
        soup = BeautifulSoup(html, "lxml")

        # Remove comments
        for comment in soup.find_all(string=lambda t: isinstance(t, Comment)):
            comment.extract()

        # Remove noise tags wholesale
        for tag_name in _STOP_TAGS:
            for node in soup.find_all(tag_name):
                node.decompose()

        # Remove noise by class/id heuristics
        for node in soup.find_all(True):
            if isinstance(node, Tag) and _is_noise_tag(node):
                node.decompose()

        # Try semantic landmarks first
        for landmark in ("main", "article", '[role="main"]'):
            main = soup.select_one(landmark)
            if main:
                return _clean_text(main.get_text(" ", strip=True))

        # Fallback: pick the <div> with the most text
        body = soup.find("body")
        if body is None:
            return _clean_text(soup.get_text(" ", strip=True))

        candidates: list[tuple[int, Tag]] = []
        for div in body.find_all(["div", "section"]):
            text = div.get_text(" ", strip=True)
            candidates.append((len(text), div))

        if candidates:
            candidates.sort(key=lambda x: x[0], reverse=True)
            return _clean_text(candidates[0][1].get_text(" ", strip=True))

        return _clean_text(body.get_text(" ", strip=True))

    # ------------------------------------------------------------------
    # Language detection
    # ------------------------------------------------------------------

    def detect_language(self, text: str) -> str:
        """Detect the dominant language of *text* using character trigrams.

        Supported ISO 639-1 codes: ``en``, ``fr``, ``de``, ``es``,
        ``ar``, ``zh``.  Returns ``"en"`` as the safe default when
        evidence is inconclusive.
        """
        if not text or len(text) < 20:
            return "en"

        # Build trigrams from a sample (first 2 000 chars for speed)
        sample = text[:2000].lower()
        trigrams: Counter[str] = Counter(
            sample[i : i + 3] for i in range(len(sample) - 2)
        )
        total = sum(trigrams.values()) or 1

        scores: dict[str, float] = {}
        for lang, profile in _LANG_NGRAMS.items():
            hit = sum(trigrams[ng] for ng in profile if ng in trigrams)
            scores[lang] = hit / total

        best = max(scores, key=lambda k: scores[k])
        return best if scores[best] > 0.0 else "en"

    # ------------------------------------------------------------------
    # Page summarisation
    # ------------------------------------------------------------------

    _SENT_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-ZА-Я\u0600-\u06FF\u4E00-\u9FFF])")

    def summarize_page(
        self,
        snapshot: "DistilledSnapshot",
        max_sentences: int = 3,
    ) -> str:
        """Return up to *max_sentences* high-signal sentences from *snapshot*.

        Uses a simple extractive scoring: sentences that share words
        with the page title score highest.
        """
        content = snapshot.markdown
        if not content:
            return snapshot.title

        # Split into sentences (rough but dependency-free)
        raw_sentences = self._SENT_SPLIT_RE.split(content)
        sentences = [s.strip() for s in raw_sentences if len(s.strip()) > 30]

        if not sentences:
            return snapshot.title[:300]

        # Score by title-word overlap
        title_words = set(re.findall(r"\w+", snapshot.title.lower()))
        scored: list[tuple[float, str]] = []
        for sent in sentences:
            words = set(re.findall(r"\w+", sent.lower()))
            overlap = len(words & title_words) / (len(title_words) or 1)
            scored.append((overlap, sent))

        scored.sort(key=lambda x: x[0], reverse=True)
        top = [s for _, s in scored[:max_sentences]]
        return " ".join(top)

    # ------------------------------------------------------------------
    # Metadata extraction
    # ------------------------------------------------------------------

    def extract_metadata(self, html: str) -> dict[str, Any]:
        """Extract structured metadata from *html*.

        Returns a dict with keys (all optional / ``None`` if absent):
        ``og_title``, ``og_description``, ``og_image``, ``canonical_url``,
        ``author``, ``published_date``.
        """
        soup = BeautifulSoup(html, "lxml")

        def _meta(name: str = "", prop: str = "") -> str | None:
            if prop:
                tag = soup.find("meta", property=prop)
                if tag and tag.get("content"):
                    return str(tag["content"]).strip() or None
            if name:
                tag = soup.find("meta", attrs={"name": name})
                if tag and tag.get("content"):
                    return str(tag["content"]).strip() or None
            return None

        # Canonical URL
        canonical: str | None = None
        link_canon = soup.find("link", rel="canonical")
        if link_canon and link_canon.get("href"):
            canonical = str(link_canon["href"]).strip() or None

        # Published date — check multiple standard locations
        published_date: str | None = (
            _meta(name="article:published_time")
            or _meta(prop="article:published_time")
            or _meta(name="datePublished")
            or _meta(prop="datePublished")
            or _meta(name="pubdate")
        )

        # Author
        author: str | None = (
            _meta(name="author")
            or _meta(prop="article:author")
            or _meta(name="article:author")
        )

        return {
            "og_title": _meta(prop="og:title") or _meta(name="title"),
            "og_description": (
                _meta(prop="og:description") or _meta(name="description")
            ),
            "og_image": _meta(prop="og:image"),
            "canonical_url": canonical,
            "author": author,
            "published_date": published_date,
        }
