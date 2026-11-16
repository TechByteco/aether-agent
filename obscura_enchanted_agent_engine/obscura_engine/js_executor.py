"""Safe JavaScript and Microdata/JSON-LD structured evaluation engine.

Provides helper utilities for executing JavaScript-like DOM manipulations,
extracting schema.org JSON-LD, OpenGraph tags, and DOM queries safely.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional
from bs4 import BeautifulSoup, Tag

logger = logging.getLogger("obscura_engine.js_executor")


class JsExecutor:
    """Safe DOM evaluation and structured metadata extraction."""

    def __init__(self, html: str = ""):
        self._html = html
        self._soup: Optional[BeautifulSoup] = BeautifulSoup(html, "html.parser") if html else None

    def update_html(self, html: str) -> None:
        """Update current HTML representation."""
        self._html = html
        self._soup = BeautifulSoup(html, "html.parser")

    @property
    def soup(self) -> BeautifulSoup:
        if self._soup is None:
            self._soup = BeautifulSoup(self._html or "<html><body></body></html>", "html.parser")
        return self._soup

    def extract_json_ld(self) -> List[Dict[str, Any]]:
        """Extract all JSON-LD (<script type="application/ld+json">) structured data blocks."""
        results: List[Dict[str, Any]] = []
        scripts = self.soup.find_all("script", type=lambda t: t and "ld+json" in t.lower())

        for s in scripts:
            content = s.string or s.get_text()
            if not content:
                continue
            content = content.strip()
            try:
                data = json.loads(content)
                if isinstance(data, list):
                    results.extend([item for item in data if isinstance(item, dict)])
                elif isinstance(data, dict):
                    results.append(data)
            except Exception as e:
                logger.debug(f"Failed to parse JSON-LD block: {e}")

        return results

    def get_meta_tags(self) -> Dict[str, str]:
        """Extract all <meta> tags as a flat dictionary."""
        meta_dict: Dict[str, str] = {}
        for tag in self.soup.find_all("meta"):
            key = tag.get("name") or tag.get("property") or tag.get("http-equiv")
            val = tag.get("content")
            if key and val:
                meta_dict[key.strip()] = val.strip()
        return meta_dict

    def get_open_graph(self) -> Dict[str, str]:
        """Extract OpenGraph (og:*) and Twitter Card (twitter:*) metadata."""
        meta = self.get_meta_tags()
        og_data: Dict[str, str] = {}
        for k, v in meta.items():
            if k.startswith("og:") or k.startswith("twitter:"):
                og_data[k] = v
        return og_data

    def count_elements(self, selector: str) -> int:
        """Count elements matching a CSS selector."""
        try:
            return len(self.soup.select(selector))
        except Exception:
            return 0

    def query_selector_text(self, selector: str) -> Optional[str]:
        """Get text of first element matching selector."""
        try:
            el = self.soup.select_one(selector)
            return el.get_text(" ", strip=True) if el else None
        except Exception:
            return None

    def query_selector_all_text(self, selector: str) -> List[str]:
        """Get text of all elements matching selector."""
        try:
            return [el.get_text(" ", strip=True) for el in self.soup.select(selector)]
        except Exception:
            return []

    def eval_safe(self, expr: str) -> Optional[Any]:
        """
        Safe heuristic evaluator for common JavaScript DOM expressions
        (e.g., 'document.title', 'document.location.href', 'document.querySelectorAll(...)').
        """
        expr = expr.strip()

        if expr in ("document.title", "window.document.title"):
            title = self.soup.find("title")
            return title.get_text(strip=True) if title else ""

        if expr.startswith("document.querySelector('") or expr.startswith('document.querySelector("'):
            match = re.search(r"document\.querySelector\(['\"]([^'\"]+)['\"]\)", expr)
            if match:
                sel = match.group(1)
                el = self.soup.select_one(sel)
                return el.get_text(" ", strip=True) if el else None

        if expr.startswith("document.querySelectorAll('") or expr.startswith('document.querySelectorAll("'):
            match = re.search(r"document\.querySelectorAll\(['\"]([^'\"]+)['\"]\)\.length", expr)
            if match:
                sel = match.group(1)
                return self.count_elements(sel)

        return None
