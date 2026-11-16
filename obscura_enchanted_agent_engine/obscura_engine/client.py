"""High-level Async Client SDK for the Obscura Enchanted Agent Engine."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
import httpx
from bs4 import BeautifulSoup

from .diff_engine import DomDiffEngine
from .distiller import DomDistiller
from .session_pool import SessionPool
from .stealth import get_stealth_headers
from .types import (
    ActionType,
    BrowserAction,
    DistilledSnapshot,
    DomDiff,
    FormFieldEntry,
    InteractiveElement,
    TabSession,
)

logger = logging.getLogger("obscura_engine.client")


class AsyncObscuraAgentEngine:
    """Async engine client orchestrating navigation, distillation, actions, and diffs."""

    def __init__(
        self,
        cdp_endpoint: Optional[str] = None,
        max_tabs: int = 8,
        timeout: float = 30.0
    ):
        self.cdp_endpoint = cdp_endpoint
        self.timeout = timeout
        self.distiller = DomDistiller()
        self.diff_engine = DomDiffEngine()
        self.session_pool = SessionPool(max_active_tabs=max_tabs)

        self._http_client = httpx.AsyncClient(
            headers=get_stealth_headers(),
            follow_redirects=True,
            timeout=timeout
        )
        self._current_html: str = ""
        self._current_url: str = "about:blank"
        self._current_title: str = ""
        self._active_tab: Optional[TabSession] = None
        self._last_snapshot: Optional[DistilledSnapshot] = None

    async def initialize(self, agent_id: str = "agent-default") -> TabSession:
        """Bootstraps the engine context and registers the active tab."""
        self._active_tab = await self.session_pool.acquire_tab(agent_id=agent_id)
        return self._active_tab

    async def close(self) -> None:
        """Closes the client and network transports."""
        await self._http_client.aclose()
        if self._active_tab:
            await self.session_pool.release_tab(self._active_tab.tab_id)

    async def navigate(self, url: str) -> DistilledSnapshot:
        """Navigates to a target URL, renders the DOM, and returns a token-compressed snapshot."""
        logger.info(f"Navigating to {url}")
        self._current_url = url

        try:
            resp = await self._http_client.get(url)
            self._current_html = resp.text
            self._current_url = str(resp.url)

            soup = BeautifulSoup(self._current_html, "html.parser")
            self._current_title = soup.title.string.strip() if soup.title and soup.title.string else url

            if self._active_tab:
                self._active_tab.url = self._current_url
                self._active_tab.title = self._current_title

        except Exception as e:
            logger.error(f"Navigation error: {e}")
            self._current_html = f"<html><body><h1>Navigation Failed</h1><p>{str(e)}</p></body></html>"
            self._current_title = "Error"

        snapshot = self.distiller.distill(
            html=self._current_html,
            url=self._current_url,
            title=self._current_title
        )
        self._last_snapshot = snapshot
        saved = max(0, snapshot.estimated_raw_tokens - snapshot.estimated_distilled_tokens)
        self.session_pool.record_token_savings(saved)
        return snapshot

    def snapshot(self) -> DistilledSnapshot:
        """Generates a token-compressed markdown snapshot of the current page."""
        snapshot = self.distiller.distill(
            html=self._current_html,
            url=self._current_url,
            title=self._current_title
        )
        self._last_snapshot = snapshot
        return snapshot

    def diff_snapshot(self) -> DomDiff:
        """Returns the semantic DOM mutation diff since the previous turn."""
        current = self.snapshot()
        return self.diff_engine.compute_diff(current)

    async def act(self, action: BrowserAction) -> Dict[str, Any]:
        """Dispatches an atomic action (click, type, select) against an element reference or selector."""
        self.session_pool.record_action()
        target_el: Optional[InteractiveElement] = None

        # Resolve element by ref or selector
        if action.ref and self._last_snapshot:
            for el in self._last_snapshot.interactive_elements:
                if el.ref_id == action.ref:
                    target_el = el
                    break

        selector = action.selector or (target_el.selector if target_el else None)

        if not selector and not action.ref and action.action not in (ActionType.SCROLL, ActionType.PRESS_KEY):
            return {
                "success": False,
                "error": "Must provide either an actionable 'ref' (e.g. '12') or a 'selector'."
            }

        soup = BeautifulSoup(self._current_html, "html.parser")
        selected_tag = None
        if selector:
            try:
                selected_tag = soup.select_one(selector)
            except Exception:
                selected_tag = None

        # Apply state mutations
        if action.action == ActionType.CLICK:
            # Check for link navigation
            if selected_tag and selected_tag.name == "a" and selected_tag.get("href"):
                next_href = selected_tag.get("href")
                if next_href and not next_href.startswith(("#", "javascript:")):
                    full_url = httpx.URL(self._current_url).join(next_href)
                    await self.navigate(str(full_url))
                    return {
                        "success": True,
                        "action": "click_navigated",
                        "new_url": str(full_url),
                        "ref": action.ref
                    }
            return {
                "success": True,
                "action": "click",
                "ref": action.ref,
                "selector": selector,
                "message": f"Clicked element {action.ref or selector}"
            }

        elif action.action == ActionType.TYPE:
            if selected_tag:
                selected_tag["value"] = action.value or ""
                self._current_html = str(soup)
            return {
                "success": True,
                "action": "type",
                "ref": action.ref,
                "value": action.value
            }

        elif action.action == ActionType.SELECT:
            if selected_tag and selected_tag.name == "select":
                for opt in selected_tag.find_all("option"):
                    if opt.get("value") == action.value or opt.get_text(strip=True) == action.value:
                        opt["selected"] = "selected"
                self._current_html = str(soup)
            return {
                "success": True,
                "action": "select",
                "ref": action.ref,
                "value": action.value
            }

        elif action.action == ActionType.SCROLL:
            return {
                "success": True,
                "action": "scroll",
                "delta_y": action.scroll_delta_y or 500
            }

        elif action.action == ActionType.PRESS_KEY:
            return {
                "success": True,
                "action": "press_key",
                "key": action.key
            }

        return {
            "success": True,
            "action": action.action.value,
            "ref": action.ref
        }

    async def fill_form(self, entries: List[FormFieldEntry]) -> Dict[str, Any]:
        """Batches complex multi-field form population in a single atomic call."""
        results = []
        for entry in entries:
            act = BrowserAction(
                action=ActionType.TYPE,
                ref=entry.ref_or_selector if entry.ref_or_selector.isdigit() else None,
                selector=entry.ref_or_selector if not entry.ref_or_selector.isdigit() else None,
                value=entry.value
            )
            res = await self.act(act)
            results.append({"entry": entry.ref_or_selector, "result": res})
        return {"success": True, "fields_updated": len(results), "details": results}

    def extract_structured_data(self, query_selector: str, fields: Dict[str, str]) -> List[Dict[str, str]]:
        """Extracts structured JSON matching field definitions from repeating DOM cards or rows."""
        soup = BeautifulSoup(self._current_html, "html.parser")
        items = soup.select(query_selector)
        extracted = []

        for item in items:
            row = {}
            for field_name, sub_selector in fields.items():
                target = item.select_one(sub_selector)
                row[field_name] = target.get_text(" ", strip=True) if target else ""
            if any(row.values()):
                extracted.append(row)

        return extracted
