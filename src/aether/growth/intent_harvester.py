"""
AETHER Intent Harvester & Outbound Lead Machine (Pillar 4)
==========================================================
Monitors public discussion platforms (Hacker News Algolia API, Reddit public JSON feeds,
GitHub public issues) for high-intent buying signals across all 5 active LEON MicroSaaS ventures:

1. CogniGuard Cyber (₹149)  – Domain security, SSL, headers, vulnerability audits.
2. CloudFlow AI (₹199)      – Cloud cost reduction (AWS/GCP/Vercel) & architecture review.
3. LeadPulse Pro (₹299)     – B2B targeted lead generation & cold outreach pipelines.
4. Aether Sovereign OS (₹99)– Offline/local AI, private LLM agents, Snapdragon edge AI.
5. ApexStudio AI (₹499)     – High-converting landing pages, design systems & brand kits.

Workflow:
  Public Source → Keyword Match → Multi-factor Scoring (0-100)
    → Agency Specialist Hook Generation (Free diagnostic value)
      → Storage in lead_signals.json & Owner Approval Inbox (inbox.json)
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import threading
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger("aether.growth.intent_harvester")

_WORKSPACE = Path(__file__).resolve().parent.parent.parent.parent
_INTEL_DIR = _WORKSPACE / "data" / "leon_intelligence"
_INTEL_DIR.mkdir(parents=True, exist_ok=True)

_LEADS_FILE = _INTEL_DIR / "lead_signals.json"
_INBOX_FILE = _INTEL_DIR / "inbox.json"
_LOCK = threading.Lock()

# User Agent for polite public scraping
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AetherIntentHarvester/1.0"


# ── Venture Keyword & ICP Matrix ─────────────────────────────────────────────

VENTURE_INTENT_MATRIX: Dict[str, Dict[str, Any]] = {
    "cogniguard-cyber": {
        "name": "CogniGuard Cyber",
        "niche": "Cybersecurity & Vulnerability Audits",
        "price_inr": 149,
        "keywords": [
            "security audit", "vulnerability scan", "ssl certificate expired",
            "csp header", "security headers", "hacked website", "penetration testing",
            "cors vulnerability", "dns leak", "security compliance"
        ],
        "urgency_triggers": ["urgent", "hacked", "breach", "warning", "fix immediately", "failed audit"],
        "diagnostic_type": "security_header_and_ssl_audit",
        "specialist_slug": "security-appsec-engineer",
    },
    "cloudflow-ai": {
        "name": "CloudFlow AI",
        "niche": "Cloud Cost Optimization & DevOps",
        "price_inr": 199,
        "keywords": [
            "aws bill too high", "cloud cost optimization", "reduce aws bill",
            "vercel pricing shock", "expensive hosting", "kubernetes cost",
            "docker memory leak", "cloud architecture review", "ec2 bill spike"
        ],
        "urgency_triggers": ["expensive", "surprise bill", "over budget", "cut costs", "bleeding money"],
        "diagnostic_type": "cloud_architecture_cost_cut_blueprint",
        "specialist_slug": "devops-cloud-platform-architect",
    },
    "leadpulse-pro": {
        "name": "LeadPulse Pro",
        "niche": "B2B Lead Generation & Prospecting",
        "price_inr": 299,
        "keywords": [
            "find b2b leads", "cold email tool", "prospecting data",
            "lead generation agency", "scrape linkedin leads", "verified email list",
            "b2b sales pipeline", "cold outreach strategy", "find clients"
        ],
        "urgency_triggers": ["need clients", "no sales", "pipeline empty", "looking for leads", "cold email failing"],
        "diagnostic_type": "b2b_prospect_sample_and_script",
        "specialist_slug": "sales-offer-lead-gen-strategist",
    },
    "aether-sovereign-os": {
        "name": "Aether Sovereign OS",
        "niche": "Private Local AI Assistant & Agentic OS",
        "price_inr": 99,
        "keywords": [
            "local llm assistant", "offline ai", "private jarvis",
            "self hosted ai agent", "run llama offline", "snapdragon ai",
            "private coding assistant", "no cloud ai", "desktop ai automation"
        ],
        "urgency_triggers": ["privacy concerns", "data leak", "offline only", "no subscription ai", "open source alternative"],
        "diagnostic_type": "offline_agent_readiness_audit",
        "specialist_slug": "engineering-ai-systems-engineer",
    },
    "apexstudio-ai": {
        "name": "ApexStudio AI",
        "niche": "High-Converting UI & Agency Design Kits",
        "price_inr": 499,
        "keywords": [
            "landing page conversion low", "website redesign feedback", "landing page critique",
            "ui design audit", "figma to tailwind", "high converting hero section",
            "modern design tokens", "b2b saas landing page"
        ],
        "urgency_triggers": ["zero conversions", "ugly design", "bounce rate high", "feedback on landing page"],
        "diagnostic_type": "ux_conversion_and_token_diagnostic",
        "specialist_slug": "design-ui-ux-designer",
    },
}


@dataclass
class IntentSignal:
    id: str
    venture_slug: str
    venture_name: str
    source: str                    # "hackernews", "reddit", "github", "public_web"
    title: str
    snippet: str
    url: str
    author: str
    intent_score: int              # 0 to 100
    matched_keywords: List[str]
    urgency_level: str             # "high", "medium", "low"
    suggested_hook: Dict[str, str] # {"subject": ..., "diagnostic_summary": ..., "cta": ...}
    harvested_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat() + "Z")
    status: str = "ready_for_review"  # "ready_for_review", "approved", "dismissed"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class IntentHarvester:
    """
    Automated Intent Harvester for discovering high-intent leads and
    generating personalized, value-first diagnostic outreach hooks.
    """

    def __init__(self, http_timeout: float = 12.0):
        self.timeout = http_timeout

    def _hash_id(self, s: str) -> str:
        return hashlib.sha256(s.encode("utf-8")).hexdigest()[:12]

    # ── 1. Public Source Harvesters ──────────────────────────────────────────

    def harvest_hackernews(self, keyword: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Query public Algolia Hacker News search API for stories and comments.
        Free, no auth required.
        """
        url = f"https://hn.algolia.com/api/v1/search?query={keyword}&tags=(story,comment)&hitsPerPage={limit}"
        results = []
        try:
            with httpx.Client(timeout=self.timeout, headers={"User-Agent": USER_AGENT}) as client:
                resp = client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    for hit in data.get("hits", []):
                        title = hit.get("title") or hit.get("story_title") or ""
                        comment_text = hit.get("comment_text") or ""
                        clean_text = re.sub(r"<[^>]+>", " ", comment_text).strip()
                        snippet = clean_text[:300] if clean_text else (title or "")
                        story_id = hit.get("story_id") or hit.get("objectID")
                        item_url = hit.get("url") or f"https://news.ycombinator.com/item?id={story_id}"

                        results.append({
                            "source": "hackernews",
                            "title": title or snippet[:80],
                            "snippet": snippet,
                            "url": item_url,
                            "author": hit.get("author", "anonymous"),
                            "created_at_i": hit.get("created_at_i", 0),
                        })
        except Exception as e:
            logger.warning(f"HN harvest error for '{keyword}': {e}")
        return results

    def harvest_reddit(self, subreddit: str, keyword: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Query public Reddit JSON search feed.
        """
        url = f"https://www.reddit.com/r/{subreddit}/search.json?q={keyword}&restrict_sr=1&sort=new&limit={limit}"
        results = []
        try:
            with httpx.Client(timeout=self.timeout, headers={"User-Agent": USER_AGENT}, follow_redirects=True) as client:
                resp = client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    children = data.get("data", {}).get("children", [])
                    for post in children:
                        pdata = post.get("data", {})
                        title = pdata.get("title", "")
                        selftext = pdata.get("selftext", "")
                        permalink = pdata.get("permalink", "")
                        full_url = f"https://reddit.com{permalink}" if permalink else ""

                        results.append({
                            "source": f"reddit/r/{subreddit}",
                            "title": title,
                            "snippet": (selftext or title)[:300],
                            "url": full_url,
                            "author": pdata.get("author", "redditor"),
                            "created_utc": pdata.get("created_utc", 0),
                        })
        except Exception as e:
            logger.warning(f"Reddit harvest error for r/{subreddit} '{keyword}': {e}")
        return results

    def harvest_github(self, keyword: str, limit: int = 8) -> List[Dict[str, Any]]:
        """
        Query public GitHub issue search API for relevant questions/bugs.
        """
        encoded_kw = keyword.replace(" ", "+")
        url = f"https://api.github.com/search/issues?q={encoded_kw}+is:issue+is:open&sort=updated&order=desc&per_page={limit}"
        results = []
        try:
            with httpx.Client(timeout=self.timeout, headers={"User-Agent": USER_AGENT, "Accept": "application/vnd.github.v3+json"}) as client:
                resp = client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    for item in data.get("items", []):
                        title = item.get("title", "")
                        body = (item.get("body") or "")[:300]
                        results.append({
                            "source": "github",
                            "title": title,
                            "snippet": body,
                            "url": item.get("html_url", ""),
                            "author": item.get("user", {}).get("login", "dev"),
                            "created_at": item.get("created_at", ""),
                        })
        except Exception as e:
            logger.warning(f"GitHub harvest error for '{keyword}': {e}")
        return results

    # ── 2. Scoring & Classification ──────────────────────────────────────────

    def score_signal(
        self,
        raw_text: str,
        venture_info: Dict[str, Any]
    ) -> Tuple[int, List[str], str]:
        """
        Compute intent score (0-100), matched keywords, and urgency level.
        Deterministic scoring based on keyword frequency, urgency tokens, and problem pain.
        """
        text_lower = raw_text.lower()
        matched_kw = []
        for kw in venture_info["keywords"]:
            if kw.lower() in text_lower:
                matched_kw.append(kw)

        # Baseline score: 25 points per matched keyword (up to 60)
        base_score = min(len(matched_kw) * 25, 60)

        # Urgency multiplier
        urgency_matches = [u for u in venture_info["urgency_triggers"] if u.lower() in text_lower]
        urgency_score = min(len(urgency_matches) * 20, 30)

        # Length / context bonus
        context_bonus = 10 if len(raw_text) > 100 else 5

        total_score = min(base_score + urgency_score + context_bonus, 100)

        if len(urgency_matches) >= 2 or total_score >= 80:
            urgency_level = "high"
        elif len(urgency_matches) == 1 or total_score >= 50:
            urgency_level = "medium"
        else:
            urgency_level = "low"

        return total_score, matched_kw, urgency_level

    # ── 3. Diagnostic Hook Synthesis (Value-First Outreach) ───────────────────

    def synthesize_diagnostic_hook(
        self,
        venture_slug: str,
        venture_info: Dict[str, Any],
        title: str,
        snippet: str,
        author: str
    ) -> Dict[str, str]:
        """
        Synthesize a non-spammy, highly personalized diagnostic value hook.
        Utilizes MultiProviderRouter with a clean fallback template.
        """
        # Fallback template
        fallback_hooks = {
            "cogniguard-cyber": {
                "subject": f"Quick security header & SSL diagnosis for your inquiry: {title[:40]}",
                "diagnostic_summary": (
                    f"Hi {author}, noticed your question regarding security configurations. "
                    "We ran a standard audit checklist and identified 3 key safeguards worth checking immediately: "
                    "1. Ensure HSTS max-age is set with includeSubDomains. "
                    "2. Verify Content-Security-Policy doesn't permit unsafe-eval. "
                    "3. Validate TLS 1.2+ cipher suites to prevent downgrade vectors."
                ),
                "free_value": "Here is an automated one-click health check tool that grades your security headers in 10 seconds: https://cogniguard-cyber.vercel.app",
                "cta": f"If you need a comprehensive CVE & port vulnerability scan report, our automated scanner provides a full audit for ₹{venture_info['price_inr']}."
            },
            "cloudflow-ai": {
                "subject": f"Cloud cost reduction notes for your workload: {title[:40]}",
                "diagnostic_summary": (
                    f"Hi {author}, saw your post on cloud infrastructure costs. "
                    "Three common high-impact savings areas in similar architectures: "
                    "1. Unattached EBS/disk volumes and idle NAT Gateways (often 20-30% of surprise spend). "
                    "2. Rightsizing overprovisioned memory footprints using ARM64 (Graviton) compute instances. "
                    "3. Configuring aggressive caching / CDN edge rules to eliminate egress egress charges."
                ),
                "free_value": "You can inspect your cloud billing JSON structure with our instant optimizer: https://cloudflow-ai.vercel.app",
                "cta": f"Our automated engine generates a complete refactor & cost-slashing blueprint for ₹{venture_info['price_inr']}."
            },
            "leadpulse-pro": {
                "subject": f"High-intent B2B prospecting approach for {title[:35]}",
                "diagnostic_summary": (
                    f"Hi {author}, regarding your lead generation focus: "
                    "Conversion rates jump 4x when moving away from generic bulk scraping to intent-based triggers: "
                    "1. Target companies actively posting job openings for your exact target skill. "
                    "2. Filter for verified MX records and deliverability scores > 95%. "
                    "3. Open with a specific diagnostic observation rather than a pitch."
                ),
                "free_value": "We maintain an active database of high-intent B2B buyer signals: https://leadpulse-pro.vercel.app",
                "cta": f"Get a verified pack of 50 enriched, targeted buyer leads tailored to your exact niche for ₹{venture_info['price_inr']}."
            },
            "aether-sovereign-os": {
                "subject": f"Local & Offline AI architecture notes for: {title[:40]}",
                "diagnostic_summary": (
                    f"Hi {author}, saw your inquiry about private/local AI assistants. "
                    "Key considerations for 100% offline execution without cloud latency: "
                    "1. Use Q4_K_M quantizations (e.g. Llama-3.2-3B or Qwen-2.5-Coder) for sub-2.5GB RAM footprint. "
                    "2. Leverage SQLite FTS5 for episodic memory retrieval with zero vector DB overhead. "
                    "3. Enable strict role alternation and continuous debouncing for voice & tool control."
                ),
                "free_value": "Review our open offline architecture blueprints: https://aether-os.vercel.app",
                "cta": f"Download the complete AETHER Sovereign OS compiled offline bundle and license for ₹{venture_info['price_inr']}."
            },
            "apexstudio-ai": {
                "subject": f"UX conversion & design critique for {title[:35]}",
                "diagnostic_summary": (
                    f"Hi {author}, reviewed your landing page discussion. "
                    "Three proven conversion levers that consistently lift SaaS signups: "
                    "1. Place the primary value proposition and live interactive preview above the 600px fold. "
                    "2. Eliminate generic stock illustrations in favor of high-fidelity glassmorphic component cards. "
                    "3. Limit navigation friction to a single high-contrast primary CTA button."
                ),
                "free_value": "Explore agency-grade design tokens and hero sections: https://apexstudio-ai.vercel.app",
                "cta": f"Access our complete production-ready agency component and brand design kit for ₹{venture_info['price_inr']}."
            },
        }

        # Attempt enrichment via MultiProviderRouter if available
        try:
            from aether.brain.multi_provider_router import \
                multi_provider_router
            prompt = (
                f"You are the {venture_info['specialist_slug']} specialist for {venture_info['name']}.\n"
                f"A potential client posted:\nTitle: {title}\nSnippet: {snippet}\nAuthor: {author}\n\n"
                f"Draft a polite, value-first response that provides 3 genuine technical diagnostic tips first, "
                f"and concludes with a gentle, non-pushy mention of {venture_info['name']} (priced at ₹{venture_info['price_inr']}).\n"
                "Return JSON with keys: subject, diagnostic_summary, free_value, cta."
            )
            res = multi_provider_router.complete_chat(
                messages=[{"role": "user", "content": prompt}],
                intent="reflex",
                max_tokens=600,
            )
            raw = res.get("content", "")
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                parsed = json.loads(match.group(0))
                if "diagnostic_summary" in parsed and "cta" in parsed:
                    return {
                        "subject": parsed.get("subject", fallback_hooks.get(venture_slug, {}).get("subject", "")),
                        "diagnostic_summary": parsed.get("diagnostic_summary", ""),
                        "free_value": parsed.get("free_value", ""),
                        "cta": parsed.get("cta", ""),
                    }
        except Exception as e:
            logger.debug(f"Router enrichment fallback used: {e}")

        return fallback_hooks.get(venture_slug, fallback_hooks["cogniguard-cyber"])

    # ── 4. Main Harvesting Engine ────────────────────────────────────────────

    def harvest_all_ventures(self, min_score: int = 40, max_signals_per_venture: int = 5) -> List[IntentSignal]:
        """
        Execute an intent harvesting sweep across all 5 ventures.
        Returns high-scoring IntentSignal objects and commits them to storage.
        """
        logger.info("🛰️ Starting Intent Harvesting Sweep across 5 LEON MicroSaaS ventures...")
        signals_found: List[IntentSignal] = []

        subreddits = {
            "cogniguard-cyber": ["cybersecurity", "webdev", "netsec"],
            "cloudflow-ai": ["aws", "devops", "cloud"],
            "leadpulse-pro": ["sales", "smallbusiness", "startups"],
            "aether-sovereign-os": ["LocalLLaMA", "selfhosted", "artificial"],
            "apexstudio-ai": ["web_design", "SaaS", "Frontend"],
        }

        for slug, info in VENTURE_INTENT_MATRIX.items():
            venture_signals: List[IntentSignal] = []
            keywords_to_query = info["keywords"][:3]  # top 3 primary keywords

            for kw in keywords_to_query:
                # 1. Harvest Hacker News
                hn_items = self.harvest_hackernews(kw, limit=4)
                # 2. Harvest Reddit
                sub_list = subreddits.get(slug, ["technology"])
                reddit_items = self.harvest_reddit(sub_list[0], kw, limit=4)
                # 3. Harvest GitHub
                github_items = self.harvest_github(kw, limit=2)

                combined_items = hn_items + reddit_items + github_items

                for raw in combined_items:
                    text_blob = f"{raw.get('title', '')} {raw.get('snippet', '')}"
                    score, matched_kws, urgency = self.score_signal(text_blob, info)

                    if score >= min_score and matched_kws:
                        sig_id = self._hash_id(f"{slug}:{raw.get('url', '')}:{raw.get('title', '')}")
                        
                        hook = self.synthesize_diagnostic_hook(
                            venture_slug=slug,
                            venture_info=info,
                            title=raw.get("title", ""),
                            snippet=raw.get("snippet", ""),
                            author=raw.get("author", "Founder")
                        )

                        signal = IntentSignal(
                            id=sig_id,
                            venture_slug=slug,
                            venture_name=info["name"],
                            source=raw.get("source", "public_web"),
                            title=raw.get("title", "")[:120],
                            snippet=raw.get("snippet", "")[:350],
                            url=raw.get("url", ""),
                            author=raw.get("author", "User"),
                            intent_score=score,
                            matched_keywords=matched_kws,
                            urgency_level=urgency,
                            suggested_hook=hook,
                        )
                        venture_signals.append(signal)

            # Sort by intent score descending and take top
            venture_signals.sort(key=lambda s: s.intent_score, reverse=True)
            signals_found.extend(venture_signals[:max_signals_per_venture])

        # Commit signals to storage & inbox
        self._commit_signals(signals_found)
        logger.info(f"✅ Intent Harvesting Sweep complete: {len(signals_found)} high-intent signals harvested.")
        return signals_found

    # ── 5. Persistence & Inbox Gating ────────────────────────────────────────

    def _commit_signals(self, signals: List[IntentSignal]) -> None:
        """Save signals to lead_signals.json and add top signals to inbox.json for owner approval."""
        if not signals:
            return

        with _LOCK:
            # 1. Update lead_signals.json
            existing_signals = []
            if _LEADS_FILE.exists():
                try:
                    existing_signals = json.loads(_LEADS_FILE.read_text(encoding="utf-8"))
                except Exception:
                    existing_signals = []

            existing_ids = {s.get("id") for s in existing_signals}
            new_records = [s.to_dict() for s in signals if s.id not in existing_ids]
            merged_signals = existing_signals + new_records
            _LEADS_FILE.write_text(json.dumps(merged_signals, indent=2, ensure_ascii=False), encoding="utf-8")

            # 2. Add top leads (score >= 65) to inbox.json for 1-click approval
            inbox_items = []
            if _INBOX_FILE.exists():
                try:
                    inbox_items = json.loads(_INBOX_FILE.read_text(encoding="utf-8"))
                except Exception:
                    inbox_items = []

            inbox_ids = {i.get("id") for i in inbox_items}
            for sig in signals:
                if sig.intent_score >= 65 and sig.id not in inbox_ids:
                    inbox_entry = {
                        "id": sig.id,
                        "category": "intent_lead",
                        "title": f"🎯 [{sig.venture_name}] High-Intent Opportunity ({sig.intent_score}/100)",
                        "data": {
                            "venture_slug": sig.venture_slug,
                            "venture_name": sig.venture_name,
                            "intent_score": sig.intent_score,
                            "urgency": sig.urgency_level,
                            "source_title": sig.title,
                            "source_url": sig.url,
                            "author": sig.author,
                            "matched_keywords": sig.matched_keywords,
                            "outreach_subject": sig.suggested_hook.get("subject"),
                            "diagnostic_preview": sig.suggested_hook.get("diagnostic_summary"),
                            "free_value": sig.suggested_hook.get("free_value"),
                            "cta": sig.suggested_hook.get("cta"),
                        },
                        "requires_approval": True,
                        "status": "pending",
                        "created_at": datetime.now(timezone.utc).isoformat() + "Z",
                    }
                    inbox_items.append(inbox_entry)

                    # Proactive push to Telegram / WhatsApp
                    try:
                        from aether.channels.telegram_assistant import \
                            telegram_assistant
                        telegram_assistant.send_lead_alert(sig.to_dict())
                    except Exception as e:
                        logger.debug(f"Telegram lead push note: {e}")

            _INBOX_FILE.write_text(json.dumps(inbox_items, indent=2, ensure_ascii=False), encoding="utf-8")



intent_harvester = IntentHarvester()
