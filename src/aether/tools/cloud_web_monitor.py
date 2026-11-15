"""
AETHER Cloud Web Intelligence & Trend Radar
============================================
Proactively scans public RSS feeds and developer/business radars (Hacker News,
TechCrunch, GitHub Trends, Product Hunt) for market shifts, competitor launches,
and high-value commercial opportunities 24/7 in the cloud.
"""

from __future__ import annotations

import json
import logging
import re
import threading
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger("aether.tools.web_monitor")

_WORKSPACE = Path(__file__).resolve().parent.parent.parent.parent
_INTEL_DIR = _WORKSPACE / "data" / "leon_intelligence"
_RADAR_FILE = _INTEL_DIR / "market_radar.json"

_INTEL_DIR.mkdir(parents=True, exist_ok=True)
_LOCK = threading.Lock()

PUBLIC_FEEDS = [
    {"name": "HackerNews Frontpage", "url": "https://hnrss.org/frontpage", "category": "tech_general"},
    {"name": "TechCrunch Startups", "url": "https://techcrunch.com/category/startups/feed/", "category": "funding_startups"},
    {"name": "GitHub Trending AI", "url": "https://hnrss.org/newest?q=AI+OR+LLM+OR+SaaS", "category": "ai_tools"},
]


@dataclass
class MarketSignal:
    id: str
    source: str
    title: str
    link: str
    summary: str
    relevance_score: int
    matched_ventures: List[str]
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat() + "Z")

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class CloudWebMonitor:
    """
    24/7 Cloud Market Radar & Competitive Intelligence Engine.
    """

    def __init__(self):
        self.timeout = 15.0

    def _read_radar(self) -> List[Dict[str, Any]]:
        try:
            if _RADAR_FILE.exists():
                return json.loads(_RADAR_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
        return []

    def _save_radar(self, signals: List[Dict[str, Any]]) -> None:
        with _LOCK:
            _RADAR_FILE.write_text(json.dumps(signals[-500:], indent=2, ensure_ascii=False), encoding="utf-8")

    def scan_feeds(self) -> List[MarketSignal]:
        """Fetch and score top market signals from public RSS feeds."""
        existing = self._read_radar()
        existing_ids = {s.get("id") for s in existing}
        new_signals: List[MarketSignal] = []

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 AETHER/2.0"
        }

        venture_keywords = {
            "CogniGuard Cyber": ["cve", "vulnerability", "ransomware", "ssl", "data breach", "infosec", "cybersecurity"],
            "CloudFlow AI": ["cloud cost", "aws bill", "finops", "kubernetes cost", "cloud architecture", "egress"],
            "LeadPulse Pro": ["lead generation", "b2b sales", "cold email", "prospecting", "pipeline", "outreach"],
            "Aether Sovereign OS": ["local llm", "edge ai", "private ai", "ollama", "snapdragon", "npu"],
            "ApexStudio AI": ["landing page", "web design", "framer", "conversion rate", "ui ux", "frontend"],
        }

        with httpx.Client(timeout=self.timeout, headers=headers, follow_redirects=True) as client:
            for feed in PUBLIC_FEEDS:
                try:
                    res = client.get(feed["url"])
                    if res.status_code != 200:
                        continue

                    # Parse XML RSS
                    root = ET.fromstring(res.content)
                    items = root.findall(".//item")

                    for it in items[:6]:
                        title = it.findtext("title") or ""
                        link = it.findtext("link") or ""
                        desc = it.findtext("description") or ""
                        clean_desc = re.sub(r"<[^>]+>", " ", desc).strip()

                        text_body = f"{title} {clean_desc}".lower()
                        matched_v = []
                        score = 0

                        for vname, kws in venture_keywords.items():
                            for kw in kws:
                                if kw in text_body:
                                    matched_v.append(vname)
                                    score += 25
                                    break

                        if score >= 25 and link:
                            sig_id = f"radar_{abs(hash(link)) % 10000000}"
                            if sig_id not in existing_ids:
                                sig = MarketSignal(
                                    id=sig_id,
                                    source=feed["name"],
                                    title=title[:120],
                                    link=link,
                                    summary=clean_desc[:250],
                                    relevance_score=min(score, 100),
                                    matched_ventures=list(set(matched_v)),
                                )
                                new_signals.append(sig)
                                existing.append(sig.to_dict())

                except Exception as e:
                    logger.debug(f"RSS feed scan note for {feed['name']}: {e}")

        if new_signals:
            self._save_radar(existing)
            logger.info(f"📡 Discovered {len(new_signals)} new market signals.")

        return new_signals


cloud_web_monitor = CloudWebMonitor()
