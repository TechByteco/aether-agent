"""
LEON Business Intelligence Core
===============================
A unified, deterministic-first intelligence layer that LEON and AETHER use for every
business they operate. It has three engines:

1. IdeationEngine    – Guidelines + scored idea generation for unique business angles,
                       in-product tools, and free "lead-magnet" tools.
2. BrandStudio       – Unique, customisable UI theme / colour palette / typography per
                       business, guaranteed to be visually distinct across the portfolio.
3. LeadDiscovery     – Ideal Customer Profile (ICP), channel playbooks, ready-to-run search
                       queries, and *real* buying-intent signals fetched from public APIs
                       (Reddit, Hacker News, GitHub). It never invents contacts.

Everything works offline (rule-based). When an LLM is reachable, it is used only to
*enrich* results, never as a single point of failure.
"""

from __future__ import annotations

import colorsys
import hashlib
import json
import logging
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx

logger = logging.getLogger("aether.leon_business_intelligence")

_WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent.parent


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower().strip()).strip("-")


def _stable_int(text: str) -> int:
    return int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:8], 16)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_niche(niche: str) -> str:
    n = re.sub(r"[^a-z0-9]+", "_", niche.lower()).strip("_")
    aliases = {
        "productivity_saas": "productivity",
        "saas": "b2b_saas",
        "security": "cybersecurity",
        "cyber": "cybersecurity",
        "devtools": "developer_tools",
        "agency": "agency_services",
        "ecommerce": "e_commerce",
        "edtech": "education",
        "healthtech": "health",
    }
    for key, val in aliases.items():
        if key in n:
            return val
    return n or "general"


# ═══════════════════════════════════════════════════════════════════════════════
# 1. IDEATION ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

# Core guidelines LEON follows whenever it invents a business idea or feature.
IDEATION_GUIDELINES: List[Dict[str, str]] = [
    {"rule": "Start from a painful, frequent, expensive problem",
     "why": "Ideas that save money/time weekly get paid for; 'nice-to-have' ideas don't."},
    {"rule": "Pick one narrow customer first (beachhead)",
     "why": "'Indian D2C brands doing ₹10L-1Cr/mo' beats 'all businesses'. Narrow = cheaper leads, sharper copy."},
    {"rule": "Have one unfair angle",
     "why": "Price, locality (UPI/GST/vernacular), speed, privacy, or a niche workflow competitors ignore."},
    {"rule": "Ship a free tool before the paid product",
     "why": "A free calculator/checker/grader brings SEO traffic and collects warm leads at near-zero cost."},
    {"rule": "Validate before building",
     "why": "Find 10 public posts complaining about the problem and 3 people willing to pay before writing code."},
    {"rule": "Price low to start, then raise with proof",
     "why": "Launch at an impulse price (₹99-₹499/mo), raise after testimonials and feature maturity."},
    {"rule": "Make the first value moment < 5 minutes",
     "why": "Users who get value in the first session convert and retain far better."},
    {"rule": "Build distribution into the product",
     "why": "Shareable reports, 'made with' badges, referrals and public pages turn users into a channel."},
]

# Differentiation frameworks used to mutate a base niche into unique angles.
IDEA_FRAMEWORKS: List[Dict[str, str]] = [
    {"id": "unbundle", "name": "Unbundle a big platform",
     "template": "Take the single most-used feature of an expensive {niche} suite and sell it standalone, done better, for {audience}."},
    {"id": "india_first", "name": "India-first / Bharat angle",
     "template": "A {niche} product built for {audience} with UPI billing, GST invoices, WhatsApp delivery and Hindi/regional language UI."},
    {"id": "ai_native", "name": "AI-native workflow",
     "template": "Replace a manual {niche} workflow ({problem_short}) with an AI agent that does it end-to-end and asks only for approval."},
    {"id": "price_disrupt", "name": "Price disruption",
     "template": "Offer 80% of the value of premium {niche} tools at 10% of the price, targeting {audience} who are priced out."},
    {"id": "vertical", "name": "Go vertical",
     "template": "A {niche} solution tailored to one industry (e.g. clinics, coaching institutes, real-estate agents) with pre-built templates."},
    {"id": "done_for_you", "name": "Service-as-software",
     "template": "Sell the outcome, not the tool: '{outcome}' delivered monthly for {audience}, powered by automation behind the scenes."},
    {"id": "privacy", "name": "Privacy / local-first",
     "template": "A {niche} tool that runs locally or self-hosted so {audience} keep full data ownership—no data leaves their machine."},
    {"id": "community", "name": "Community + tool",
     "template": "Bundle a {niche} tool with a paid community/playbook library so {audience} get both software and peer know-how."},
]

# Niche knowledge base: audiences, outcomes, product tools and free lead-magnet tools.
NICHE_KNOWLEDGE: Dict[str, Dict[str, Any]] = {
    "developer_tools": {
        "audience": "small dev teams and indie hackers",
        "outcome": "zero broken deploys",
        "product_tools": ["CI failure root-cause explainer", "Config drift detector", "Auto-generated changelog & release notes",
                          "Dependency vulnerability auto-patcher", "API uptime + latency monitor"],
        "free_tools": ["Dockerfile linter & optimizer", "Cron expression explainer", "GitHub Actions YAML validator",
                       "Regex tester with plain-English explanation", ".env leak scanner"],
        "keywords": ["CI/CD", "deploy failing", "devops", "github actions", "infrastructure drift"],
    },
    "cybersecurity": {
        "audience": "SMBs without a security team",
        "outcome": "a clean monthly security report",
        "product_tools": ["Website vulnerability scanner", "Phishing simulation for staff", "Leaked-credential monitor",
                          "SSL/DNS/email-auth (SPF/DKIM/DMARC) monitor", "Compliance checklist tracker (ISO/SOC2/DPDP)"],
        "free_tools": ["Free website security grade", "Email SPF/DMARC checker", "Password breach checker",
                       "Security headers analyzer", "DPDP Act readiness quiz"],
        "keywords": ["website hacked", "security audit", "phishing", "DMARC", "data breach", "DPDP compliance"],
    },
    "productivity": {
        "audience": "solo founders, freelancers and busy professionals",
        "outcome": "10 hours saved every week",
        "product_tools": ["AI daily planner from inbox + calendar", "Meeting notes → action items", "Personal knowledge vault",
                          "Focus timer with distraction blocking", "Auto weekly review report"],
        "free_tools": ["Time-cost-of-meetings calculator", "Weekly planner template generator", "Pomodoro + task timer",
                       "Email rewrite assistant", "Habit streak tracker"],
        "keywords": ["productivity app", "too many tasks", "time management", "notion alternative", "personal assistant"],
    },
    "agency_services": {
        "audience": "agencies, consultants and B2B founders",
        "outcome": "a full pipeline of qualified meetings",
        "product_tools": ["Lead list builder from public signals", "Personalised outreach writer", "Proposal & quote generator",
                          "Client reporting dashboard", "Brand kit + landing page generator"],
        "free_tools": ["Cold email subject-line grader", "Landing page conversion audit", "Brand colour palette generator",
                       "Agency pricing calculator", "Website speed + SEO grader"],
        "keywords": ["need more clients", "lead generation", "cold outreach", "agency growth", "looking for designer"],
    },
    "b2b_saas": {
        "audience": "SMB operators",
        "outcome": "automated back-office ops",
        "product_tools": ["Workflow automation builder", "Customer portal", "Usage analytics", "Invoice & GST automation", "Team permissions"],
        "free_tools": ["ROI calculator", "SaaS pricing calculator", "Churn rate calculator", "Invoice generator", "Process audit quiz"],
        "keywords": ["software for small business", "automate workflow", "spreadsheet replacement"],
    },
    "fintech": {
        "audience": "freelancers and small businesses in India",
        "outcome": "always-on cash-flow clarity",
        "product_tools": ["UPI payment reconciliation", "GST filing assistant", "Cash-flow forecaster", "Expense categoriser", "Invoice reminders"],
        "free_tools": ["GST calculator", "EMI calculator", "Freelancer tax estimator", "Invoice generator", "Profit margin calculator"],
        "keywords": ["GST filing", "invoice software", "track expenses", "accounting for freelancers"],
    },
    "e_commerce": {
        "audience": "D2C and Instagram sellers",
        "outcome": "more repeat orders",
        "product_tools": ["WhatsApp order bot", "Abandoned cart recovery", "AI product description writer", "Inventory alerts", "Review collector"],
        "free_tools": ["Product title optimizer", "Shipping cost calculator", "Profit per order calculator", "Store speed grader", "Hashtag generator"],
        "keywords": ["shopify store", "increase sales", "abandoned cart", "instagram seller"],
    },
    "education": {
        "audience": "coaching institutes, tutors and course creators",
        "outcome": "more enrolled students with less admin",
        "product_tools": ["AI quiz & test generator", "Attendance + fee tracker", "Doubt-solving chatbot", "Course landing builder", "Progress reports for parents"],
        "free_tools": ["Question paper generator", "Grade calculator", "Study timetable maker", "Flashcard generator", "Course price calculator"],
        "keywords": ["coaching institute software", "online course", "tutor app", "create quiz"],
    },
    "health": {
        "audience": "clinics and wellness professionals",
        "outcome": "fuller appointment calendars",
        "product_tools": ["Appointment booking + reminders", "Patient follow-up automation", "Digital prescriptions", "Review & reputation manager", "Telehealth links"],
        "free_tools": ["BMI/calorie calculator", "Clinic no-show cost calculator", "Appointment reminder template", "Google profile audit", "Diet plan generator"],
        "keywords": ["clinic software", "appointment booking", "patient reminders"],
    },
}
_DEFAULT_KNOWLEDGE = {
    "audience": "small businesses and professionals",
    "outcome": "measurable time and money saved",
    "product_tools": ["Automation workflow builder", "AI assistant for the core task", "Analytics dashboard", "Integrations hub", "Reports & exports"],
    "free_tools": ["ROI calculator", "Free audit / grader", "Template generator", "Checklist builder", "Cost calculator"],
    "keywords": ["software", "automation", "tool"],
}


@dataclass
class IdeaCandidate:
    title: str
    framework: str
    pitch: str
    target_customer: str
    unique_angle: str
    core_tools: List[str]
    free_lead_magnet_tool: str
    scores: Dict[str, int]
    total_score: int
    validation_steps: List[str]
    mvp_scope: List[str]


class IdeationEngine:
    """Generates and ranks unique business ideas + in-product tools under explicit guidelines."""

    SCORE_WEIGHTS = {"pain": 3, "willingness_to_pay": 3, "reach": 2, "differentiation": 2, "build_ease": 1}

    def knowledge(self, niche: str) -> Dict[str, Any]:
        return NICHE_KNOWLEDGE.get(_normalize_niche(niche), _DEFAULT_KNOWLEDGE)

    def _score(self, framework_id: str, niche_key: str, seed: int) -> Dict[str, int]:
        # Deterministic heuristic scores (1-10) per framework, nudged per niche for variety.
        base = {
            "unbundle":      {"pain": 7, "willingness_to_pay": 7, "reach": 7, "differentiation": 6, "build_ease": 7},
            "india_first":   {"pain": 7, "willingness_to_pay": 6, "reach": 9, "differentiation": 8, "build_ease": 7},
            "ai_native":     {"pain": 8, "willingness_to_pay": 8, "reach": 7, "differentiation": 7, "build_ease": 5},
            "price_disrupt": {"pain": 6, "willingness_to_pay": 6, "reach": 8, "differentiation": 6, "build_ease": 7},
            "vertical":      {"pain": 8, "willingness_to_pay": 8, "reach": 6, "differentiation": 8, "build_ease": 6},
            "done_for_you":  {"pain": 9, "willingness_to_pay": 9, "reach": 5, "differentiation": 7, "build_ease": 5},
            "privacy":       {"pain": 6, "willingness_to_pay": 7, "reach": 5, "differentiation": 8, "build_ease": 5},
            "community":     {"pain": 5, "willingness_to_pay": 6, "reach": 6, "differentiation": 6, "build_ease": 8},
        }[framework_id].copy()
        if niche_key in ("cybersecurity", "health") and framework_id in ("privacy", "done_for_you"):
            base["willingness_to_pay"] = min(10, base["willingness_to_pay"] + 1)
        if niche_key in ("developer_tools",) and framework_id in ("ai_native", "privacy"):
            base["differentiation"] = min(10, base["differentiation"] + 1)
        if niche_key in ("e_commerce", "education", "fintech") and framework_id == "india_first":
            base["pain"] = min(10, base["pain"] + 1)
        # small deterministic jitter so different businesses rank differently
        key = list(base.keys())[seed % len(base)]
        base[key] = max(1, min(10, base[key] + (1 if seed % 2 else -1)))
        return base

    def generate_ideas(self, niche: str, problem: str = "", audience: Optional[str] = None,
                       count: int = 5) -> List[IdeaCandidate]:
        niche_key = _normalize_niche(niche)
        kb = self.knowledge(niche)
        aud = audience or kb["audience"]
        problem_short = (problem or f"manual {niche_key.replace('_', ' ')} work").rstrip(".")[:90]
        ideas: List[IdeaCandidate] = []
        for i, fw in enumerate(IDEA_FRAMEWORKS):
            seed = _stable_int(f"{niche_key}:{fw['id']}")
            scores = self._score(fw["id"], niche_key, seed)
            total = sum(scores[k] * w for k, w in self.SCORE_WEIGHTS.items())
            tools = [kb["product_tools"][(i + j) % len(kb["product_tools"])] for j in range(3)]
            magnet = kb["free_tools"][i % len(kb["free_tools"])]
            pitch = fw["template"].format(niche=niche_key.replace("_", " "), audience=aud,
                                          problem_short=problem_short, outcome=kb["outcome"])
            ideas.append(IdeaCandidate(
                title=f"{fw['name']}: {tools[0]} for {aud}",
                framework=fw["name"],
                pitch=pitch,
                target_customer=aud,
                unique_angle=fw["name"],
                core_tools=tools,
                free_lead_magnet_tool=magnet,
                scores=scores,
                total_score=total,
                validation_steps=[
                    f"Find 10 public posts where {aud} complain about: {problem_short}",
                    f"Launch the free '{magnet}' and get 50 uses in 14 days",
                    "Run 5 short calls / DMs: ask what they use today and what they pay",
                    "Put a ₹99 pre-order / waitlist button on the landing page; target 3 paid sign-ups",
                ],
                mvp_scope=[f"Must-have: {tools[0]}", "Razorpay/UPI checkout", "Email + WhatsApp onboarding",
                           f"Later: {tools[1]}, {tools[2]}"],
            ))
        ideas.sort(key=lambda x: x.total_score, reverse=True)
        return ideas[:max(1, count)]

    def tool_guidelines(self, niche: str) -> Dict[str, Any]:
        kb = self.knowledge(niche)
        return {
            "principles": [
                "Each tool must map to one job-to-be-done and produce a visible result in < 5 minutes.",
                "Free tools: no signup to use; ask for email only to export/save the result.",
                "Paid tools: automate a recurring task (weekly/monthly) so value repeats and churn stays low.",
                "Every output should be shareable (PDF/link/badge) to create word-of-mouth.",
                "Instrument usage: track activation event, weekly active use, and upgrade clicks per tool.",
            ],
            "paid_product_tools": kb["product_tools"],
            "free_lead_magnet_tools": kb["free_tools"],
            "build_order": [
                f"1. Free tool: {kb['free_tools'][0]} (SEO + lead capture)",
                f"2. Core paid tool: {kb['product_tools'][0]}",
                f"3. Retention tool: {kb['product_tools'][-1]}",
                "4. Integrations / exports requested by first 10 customers",
            ],
        }


# ═══════════════════════════════════════════════════════════════════════════════
# 2. BRAND STUDIO (UI theme, colours, typography)
# ═══════════════════════════════════════════════════════════════════════════════

# Colour psychology: hue ranges (degrees) per niche.
NICHE_HUE_RANGES: Dict[str, Tuple[int, int, str]] = {
    "developer_tools": (195, 235, "trust, precision, technical calm"),
    "cybersecurity":   (145, 178, "safety, protection, 'all clear' green"),
    "productivity":    (255, 290, "creativity, focus, premium calm"),
    "agency_services": (12, 45, "warmth, energy, confident creativity"),
    "b2b_saas":        (215, 250, "reliability, professionalism"),
    "fintech":         (135, 165, "growth, money, stability"),
    "e_commerce":      (325, 355, "excitement, impulse, delight"),
    "education":       (38, 58, "optimism, curiosity, learning"),
    "health":          (168, 192, "care, cleanliness, wellbeing"),
}

ARCHETYPE_BY_NICHE = {
    "developer_tools": "linear_dark", "cybersecurity": "linear_dark", "productivity": "bento_modern",
    "agency_services": "editorial_luxury", "b2b_saas": "bento_modern", "fintech": "vibrant_fintech",
    "e_commerce": "apple_minimal", "education": "apple_minimal", "health": "apple_minimal",
}

FONT_PAIRS: Dict[str, List[Tuple[str, str]]] = {
    "linear_dark":      [("Space Grotesk", "Inter"), ("JetBrains Mono", "Inter"), ("IBM Plex Sans", "IBM Plex Sans")],
    "bento_modern":     [("Sora", "Inter"), ("Outfit", "Inter"), ("Lexend", "Inter")],
    "editorial_luxury": [("Playfair Display", "Plus Jakarta Sans"), ("Fraunces", "Manrope"), ("DM Serif Display", "DM Sans")],
    "vibrant_fintech":  [("Manrope", "Inter"), ("Urbanist", "Inter"), ("Poppins", "Inter")],
    "apple_minimal":    [("Outfit", "Inter"), ("Plus Jakarta Sans", "Inter"), ("Nunito Sans", "Nunito Sans")],
}

VOICE_BY_ARCHETYPE = {
    "linear_dark": "Precise, technical, no fluff. Short sentences. Numbers over adjectives.",
    "bento_modern": "Friendly-smart and modern. Benefit-led headlines, playful micro-copy.",
    "editorial_luxury": "Confident, premium, outcome-focused. Fewer words, bigger promises backed by proof.",
    "vibrant_fintech": "Clear, trustworthy, data-driven. Show the money saved.",
    "apple_minimal": "Simple, warm, human. One idea per line.",
}

SHADE_LIGHTNESS = {50: 97, 100: 93, 200: 86, 300: 76, 400: 65, 500: 55, 600: 46, 700: 38, 800: 30, 900: 23, 950: 14}


def _hsl_hex(h: float, s: float, l: float) -> str:
    r, g, b = colorsys.hls_to_rgb((h % 360) / 360.0, l / 100.0, s / 100.0)
    return "#{:02X}{:02X}{:02X}".format(round(r * 255), round(g * 255), round(b * 255))


def _hex_rgb(hex_color: str) -> Tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _hex_hue(hex_color: str) -> float:
    r, g, b = (c / 255.0 for c in _hex_rgb(hex_color))
    h, _, _ = colorsys.rgb_to_hls(r, g, b)
    return h * 360.0


def _shade_scale(hue: float, sat: float) -> Dict[str, str]:
    scale = {}
    for shade, light in SHADE_LIGHTNESS.items():
        s = sat if 300 <= shade <= 700 else max(20.0, sat - 12)
        scale[str(shade)] = _hsl_hex(hue, s, light)
    return scale


def _hue_distance(a: float, b: float) -> float:
    d = abs(a - b) % 360
    return min(d, 360 - d)


@dataclass
class BrandIdentity:
    slug: str
    venture_name: str
    niche: str
    archetype: str
    primary_hue: int
    accent_hue: int
    primary_scale: Dict[str, str]
    accent_scale: Dict[str, str]
    background: str
    surface: str
    text: str
    muted_text: str
    font_heading: str
    font_body: str
    border_radius: str
    color_psychology: str
    brand_voice: str
    logo_monogram: str
    customized: bool = False
    updated_at: str = field(default_factory=_now)

    @property
    def primary(self) -> str:
        return self.primary_scale["500"]

    @property
    def accent(self) -> str:
        return self.accent_scale["400"]

    def css_variables(self) -> str:
        lines = [f"--brand-{k}: {v};" for k, v in self.primary_scale.items()]
        lines += [f"--accent-{k}: {v};" for k, v in self.accent_scale.items()]
        lines += [f"--bg: {self.background};", f"--surface: {self.surface};", f"--text: {self.text};"]
        return ":root { " + " ".join(lines) + " }"


class BrandStudio:
    """Creates a unique, persistent, customisable brand identity for every business."""

    def __init__(self, workspace_root: Optional[Path] = None):
        root = workspace_root or _WORKSPACE_ROOT
        self.registry_file = root / "data" / "leon_intelligence" / "brand_registry.json"
        self.registry_file.parent.mkdir(parents=True, exist_ok=True)
        self.brands: Dict[str, BrandIdentity] = {}
        self._load()

    def _load(self) -> None:
        if self.registry_file.exists():
            try:
                for k, v in json.loads(self.registry_file.read_text(encoding="utf-8")).items():
                    self.brands[k] = BrandIdentity(**v)
            except Exception as e:
                logger.warning(f"Brand registry load failed: {e}")

    def _save(self) -> None:
        self.registry_file.write_text(
            json.dumps({k: asdict(v) for k, v in self.brands.items()}, indent=2), encoding="utf-8")

    def _pick_hue(self, slug: str, niche_key: str) -> int:
        lo, hi, _ = NICHE_HUE_RANGES.get(niche_key, (0, 359, ""))
        span = (hi - lo) % 360 or 360
        start = lo + _stable_int(slug) % span
        taken = [b.primary_hue for s, b in self.brands.items() if s != slug]
        # Walk the hue wheel (preferring the niche range) until it is >= 28° from every other brand.
        for step in range(0, 360, 7):
            cand = (start + step) % 360
            if all(_hue_distance(cand, t) >= 28 for t in taken):
                return int(cand)
        return int(start % 360)

    def _pick_fonts(self, slug: str, archetype: str) -> Tuple[str, str]:
        pairs = FONT_PAIRS.get(archetype, FONT_PAIRS["bento_modern"])
        used = {b.font_heading for s, b in self.brands.items() if s != slug}
        offset = _stable_int(slug + "font") % len(pairs)
        for i in range(len(pairs)):
            pair = pairs[(offset + i) % len(pairs)]
            if pair[0] not in used:
                return pair
        return pairs[offset]

    def _build(self, slug: str, venture_name: str, niche: str, hue: int,
               accent_hue: Optional[int] = None, archetype: Optional[str] = None,
               fonts: Optional[Tuple[str, str]] = None, radius: Optional[str] = None) -> BrandIdentity:
        niche_key = _normalize_niche(niche)
        arch = archetype or ARCHETYPE_BY_NICHE.get(niche_key, "bento_modern")
        # Accent: analogous (+35°) for calm archetypes, split-complementary (+150°) for vibrant ones.
        if accent_hue is None:
            accent_hue = (hue + (150 if arch in ("vibrant_fintech", "editorial_luxury") else 35)) % 360
        sat = 72 if arch != "editorial_luxury" else 62
        fh, fb = fonts or self._pick_fonts(slug, arch)
        words = [w for w in re.split(r"[^A-Za-z0-9]+", venture_name) if w]
        monogram = "".join(w[0] for w in words[:2]).upper() or venture_name[:2].upper()
        return BrandIdentity(
            slug=slug, venture_name=venture_name, niche=niche_key, archetype=arch,
            primary_hue=int(hue), accent_hue=int(accent_hue),
            primary_scale=_shade_scale(hue, sat), accent_scale=_shade_scale(accent_hue, sat + 6),
            # Dark, hue-tinted surfaces so each brand feels distinct even in dark mode.
            background=_hsl_hex(hue, 28, 5), surface=_hsl_hex(hue, 22, 9),
            text="#F1F5F9", muted_text="#94A3B8",
            font_heading=fh, font_body=fb,
            border_radius=radius or {"linear_dark": "8px", "editorial_luxury": "4px",
                                     "apple_minimal": "18px"}.get(arch, "14px"),
            color_psychology=NICHE_HUE_RANGES.get(niche_key, (0, 0, "distinct, memorable brand colour"))[2],
            brand_voice=VOICE_BY_ARCHETYPE.get(arch, VOICE_BY_ARCHETYPE["bento_modern"]),
            logo_monogram=monogram,
        )

    def get_or_create(self, venture_name: str, niche: str) -> BrandIdentity:
        slug = _slugify(venture_name)
        if slug in self.brands:
            return self.brands[slug]
        brand = self._build(slug, venture_name, niche, self._pick_hue(slug, _normalize_niche(niche)))
        self.brands[slug] = brand
        self._save()
        return brand

    def customize(self, venture_name_or_slug: str, primary_hex: Optional[str] = None,
                  accent_hex: Optional[str] = None, font_heading: Optional[str] = None,
                  font_body: Optional[str] = None, archetype: Optional[str] = None,
                  border_radius: Optional[str] = None, niche: Optional[str] = None) -> BrandIdentity:
        """Owner overrides: any colour (hex), fonts (Google Fonts names), archetype or radius."""
        slug = _slugify(venture_name_or_slug)
        current = self.brands.get(slug) or self.get_or_create(venture_name_or_slug, niche or "general")
        for hx in (primary_hex, accent_hex):
            if hx and not re.fullmatch(r"#?[0-9A-Fa-f]{6}", hx):
                raise ValueError(f"Invalid hex colour: {hx}")
        hue = int(_hex_hue("#" + primary_hex.lstrip("#"))) if primary_hex else current.primary_hue
        acc = int(_hex_hue("#" + accent_hex.lstrip("#"))) if accent_hex else (
            current.accent_hue if not primary_hex else None)
        brand = self._build(
            slug, current.venture_name, niche or current.niche, hue, accent_hue=acc,
            archetype=archetype or current.archetype,
            fonts=(font_heading or current.font_heading, font_body or current.font_body),
            radius=border_radius or current.border_radius,
        )
        if primary_hex:  # keep the exact owner colour at the 500 stop
            brand.primary_scale["500"] = "#" + primary_hex.lstrip("#").upper()
        if accent_hex:
            brand.accent_scale["400"] = "#" + accent_hex.lstrip("#").upper()
        brand.customized = True
        self.brands[slug] = brand
        self._save()
        return brand

    def apply_to_html(self, html: str, brand: BrandIdentity) -> str:
        """Re-skins a LEON landing page: swaps hard-coded palette classes for brand scales,
        injects Tailwind colour scales, fonts, and tinted surfaces."""
        html = re.sub(r"\bindigo-(\d{2,3})", r"brand-\1", html)
        html = re.sub(r"\b(?:cyan|purple)-(\d{2,3})", r"accent-\1", html)
        fonts = sorted({brand.font_heading, brand.font_body, "JetBrains Mono"})
        fam = "&".join("family=" + f.replace(" ", "+") + ":wght@400;500;600;700;800" for f in fonts)
        font_link = f'<link href="https://fonts.googleapis.com/css2?{fam}&display=swap" rel="stylesheet">'
        html = re.sub(r'<link href="https://fonts\.googleapis\.com/css2\?[^"]+" rel="stylesheet">', font_link, html, count=1)
        cfg = {
            "darkMode": "class",
            "theme": {"extend": {
                "colors": {"brand": brand.primary_scale, "accent": brand.accent_scale,
                           "surface": brand.surface, "canvas": brand.background},
                "fontFamily": {"heading": [brand.font_heading, "sans-serif"],
                               "body": [brand.font_body, "sans-serif"],
                               "mono": ["JetBrains Mono", "monospace"]},
                "borderRadius": {"brand": brand.border_radius},
            }},
        }
        html = re.sub(r"<script>\s*tailwind\.config\s*=.*?</script>",
                      lambda _: f"<script>\n    tailwind.config = {json.dumps(cfg)};\n  </script>",
                      html, count=1, flags=re.DOTALL)
        r, g, b = _hex_rgb(brand.surface)
        pr, pg, pb = _hex_rgb(brand.primary)
        style = (
            f"<style id=\"leon-brand\">\n    {brand.css_variables()}\n"
            f"    body {{ background-color: {brand.background} !important; color: {brand.text}; font-family: '{brand.font_body}', sans-serif !important; }}\n"
            f"    h1, h2, h3, .font-heading {{ font-family: '{brand.font_heading}', sans-serif; }}\n"
            f"    .glass {{ background: rgba({r}, {g}, {b}, 0.78) !important; border-color: rgba({pr}, {pg}, {pb}, 0.14) !important; }}\n"
            f"    .glow-subtle {{ box-shadow: 0 0 50px -10px {brand.primary}55 !important; }}\n"
            f"    .gradient-text {{ background: linear-gradient(135deg, #FFFFFF 25%, {brand.accent} 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}\n"
            f"  </style>\n</head>"
        )
        html = html.replace("</head>", style, 1)
        html = html.replace('<body class="antialiased',
                            f'<body data-brand="{brand.slug}" data-archetype="{brand.archetype}" class="antialiased', 1)
        return html


# ═══════════════════════════════════════════════════════════════════════════════
# 3. LEAD DISCOVERY
# ═══════════════════════════════════════════════════════════════════════════════

INTENT_PATTERNS: List[Tuple[str, int]] = [
    (r"\b(looking for|need|searching for|in search of)\b.{0,40}\b(tool|app|software|service|agency|solution|someone)\b", 35),
    (r"\b(any|can you|can anyone)\s+recommend", 30),
    (r"\balternative(s)? to\b", 30),
    (r"\b(willing to pay|budget|pricing|how much)\b", 25),
    (r"\b(struggling|frustrated|tired of|hate|pain|nightmare|wasting)\b", 20),
    (r"\b(how (do|can) (i|we)|is there a way)\b", 15),
    (r"\b(hiring|freelancer|contractor)\b", 15),
]

AUDIENCE_PLAYBOOKS: Dict[str, Dict[str, Any]] = {
    "b2b_smb": {
        "icp": "Owner/founder of a 2-50 person business, decides and pays personally, feels the pain weekly.",
        "channels": ["Reddit (r/smallbusiness, r/Entrepreneur, r/startups)", "LinkedIn search + content",
                     "Google Maps / JustDial category lists", "IndieHackers & Product Hunt comments",
                     "WhatsApp/Telegram business communities"],
    },
    "b2b_enterprise": {
        "icp": "Head of Growth/Engineering/IT at a 50-1000 person company with budget and a measurable KPI.",
        "channels": ["LinkedIn boolean search (title + industry + size)", "Job posts revealing the pain (hiring for the role you automate)",
                     "Tech-stack signals (BuiltWith/GitHub)", "Industry Slack/Discord communities", "Conference speaker lists"],
    },
    "individual_prosumer": {
        "icp": "Professional or power user paying out of pocket for productivity; active online, values time.",
        "channels": ["Reddit (r/productivity, r/getdisciplined, niche subs)", "X/Twitter searches for complaints",
                     "YouTube comments on competitor tutorials", "Hacker News 'Ask HN' threads", "Product Hunt launches"],
    },
    "creator_freelancer": {
        "icp": "Freelancer/creator earning from clients or audience who needs leverage on time or reach.",
        "channels": ["Reddit (r/freelance, r/forhire, r/content_marketing)", "X/Twitter creator circles",
                     "Upwork/Fiverr job post trends", "Discord creator servers", "Instagram/YouTube niche hashtags"],
    },
}


@dataclass
class LeadSignal:
    id: str
    venture_slug: str
    source: str
    title: str
    url: str
    author: str
    snippet: str
    intent_score: int
    matched_signals: List[str]
    suggested_action: str
    status: str = "new"  # new → engaged → replied → converted / dismissed
    found_at: str = field(default_factory=_now)


class LeadDiscovery:
    """Finds real people publicly expressing a need, and gives a playbook for everything else."""

    USER_AGENT = "LEON-LeadDiscovery/1.0 (by saalimin21; market research)"

    def __init__(self, workspace_root: Optional[Path] = None, timeout: float = 8.0):
        root = workspace_root or _WORKSPACE_ROOT
        self.signals_file = root / "data" / "leon_intelligence" / "lead_signals.json"
        self.signals_file.parent.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout

    # ── Playbook (offline) ────────────────────────────────────────────────────
    def build_playbook(self, venture_name: str, niche: str, value_prop: str,
                       audience_type: str = "b2b_smb") -> Dict[str, Any]:
        kb = NICHE_KNOWLEDGE.get(_normalize_niche(niche), _DEFAULT_KNOWLEDGE)
        aud = AUDIENCE_PLAYBOOKS.get(audience_type, AUDIENCE_PLAYBOOKS["b2b_smb"])
        kws = kb["keywords"]
        q = " OR ".join(f'"{k}"' for k in kws[:4])
        return {
            "venture": venture_name,
            "ideal_customer_profile": aud["icp"],
            "who_specifically": kb["audience"],
            "pain_keywords": kws,
            "priority_channels": aud["channels"],
            "search_queries": {
                "google_intent": f'({q}) ("looking for" OR "recommend" OR "alternative to") -jobs',
                "google_reddit": f'site:reddit.com ({q}) ("any recommendations" OR "what do you use")',
                "linkedin_boolean": f'("founder" OR "owner" OR "head of") AND ({" OR ".join(kws[:3])})',
                "x_twitter": f'({" OR ".join(kws[:3])}) ("need a" OR "recommend" OR "frustrated") -filter:links lang:en',
                "google_maps_local": f"{kb['audience'].split(' and ')[0]} near <city>",
            },
            "lead_scoring_rubric": {
                "explicit_need_or_request": 35, "asking_for_alternatives": 30, "mentions_budget_or_price": 25,
                "expresses_frustration": 20, "decision_maker_title": 15, "recent_post_<14_days": 10,
            },
            "outreach_sequence": [
                "Day 0: Reply publicly with genuinely useful advice (no pitch). Mention the free tool only if relevant.",
                f"Day 1: If they engage, DM: one line on their problem + link to the free '{kb['free_tools'][0]}'.",
                f"Day 3: Share a 60-sec loom/screenshot showing {venture_name} solving their exact case.",
                "Day 7: Offer the low-cost launch plan with a 7-day refund guarantee. Stop after one follow-up.",
            ],
            "inbound_engines": [
                f"Free tool pages: {', '.join(kb['free_tools'][:3])} (each targets a long-tail keyword)",
                "Comparison pages: '<competitor> alternative for India'",
                "Weekly build-in-public posts on X/LinkedIn with real numbers",
            ],
            "compliance": [
                "Only use publicly posted content; respect each platform's rules on self-promotion.",
                "Never scrape or buy personal emails/phone numbers; collect consent via your free tool.",
                "Every email must include sender identity and an unsubscribe line (CAN-SPAM / DPDP Act).",
            ],
        }

    # ── Live public signal discovery ──────────────────────────────────────────
    def score_intent(self, text: str) -> Tuple[int, List[str]]:
        t = text.lower()
        score, hits = 0, []
        for pattern, weight in INTENT_PATTERNS:
            m = re.search(pattern, t)
            if m:
                score += weight
                hits.append(m.group(0)[:40])
        return min(100, score), hits

    def _get(self, client: httpx.Client, url: str, params: Dict[str, Any]) -> Optional[Any]:
        try:
            r = client.get(url, params=params, headers={"User-Agent": self.USER_AGENT})
            if r.status_code == 200:
                return r.json()
            logger.info(f"Lead source {url} returned {r.status_code}")
        except Exception as e:
            logger.info(f"Lead source {url} unavailable: {e}")
        return None

    def _search_reddit(self, client, query: str, limit: int) -> List[Dict[str, str]]:
        data = self._get(client, "https://www.reddit.com/search.json",
                         {"q": query, "sort": "new", "t": "month", "limit": limit})
        out = []
        for c in ((data or {}).get("data", {}) or {}).get("children", []):
            d = c.get("data", {})
            out.append({"source": f"reddit/r/{d.get('subreddit', '')}", "title": d.get("title", ""),
                        "url": "https://www.reddit.com" + d.get("permalink", ""), "author": d.get("author", ""),
                        "text": d.get("selftext", "")[:600]})
        return out

    def _search_hn(self, client, query: str, limit: int) -> List[Dict[str, str]]:
        data = self._get(client, "https://hn.algolia.com/api/v1/search_by_date",
                         {"query": query, "tags": "(story,comment)", "hitsPerPage": limit})
        out = []
        for h in (data or {}).get("hits", []):
            title = h.get("title") or h.get("story_title") or ""
            text = re.sub(r"<[^>]+>", " ", h.get("comment_text") or h.get("story_text") or "")[:600]
            out.append({"source": "hackernews", "title": title,
                        "url": f"https://news.ycombinator.com/item?id={h.get('objectID')}",
                        "author": h.get("author", ""), "text": text})
        return out

    def _search_github(self, client, query: str, limit: int) -> List[Dict[str, str]]:
        data = self._get(client, "https://api.github.com/search/issues",
                         {"q": f"{query} is:issue is:open", "sort": "created", "per_page": limit})
        out = []
        for it in (data or {}).get("items", []):
            out.append({"source": "github", "title": it.get("title", ""), "url": it.get("html_url", ""),
                        "author": (it.get("user") or {}).get("login", ""), "text": (it.get("body") or "")[:600]})
        return out

    def discover_signals(self, venture_name: str, niche: str, value_prop: str = "",
                         sources: Optional[List[str]] = None, per_source: int = 15,
                         min_score: int = 20) -> List[LeadSignal]:
        niche_key = _normalize_niche(niche)
        kb = NICHE_KNOWLEDGE.get(niche_key, _DEFAULT_KNOWLEDGE)
        sources = sources or (["reddit", "hackernews", "github"] if niche_key == "developer_tools"
                              else ["reddit", "hackernews"])
        slug = _slugify(venture_name)
        raw: List[Dict[str, str]] = []
        with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
            for kw in kb["keywords"][:3]:
                if "reddit" in sources:
                    raw += self._search_reddit(client, f'"{kw}" (recommend OR alternative OR looking)', per_source)
                if "hackernews" in sources:
                    raw += self._search_hn(client, kw, per_source)
                if "github" in sources:
                    raw += self._search_github(client, kw, min(per_source, 10))
        seen, signals = set(), []
        for item in raw:
            if not item["url"] or item["url"] in seen:
                continue
            seen.add(item["url"])
            score, hits = self.score_intent(f"{item['title']} {item['text']}")
            if score < min_score:
                continue
            signals.append(LeadSignal(
                id=f"sig_{_stable_int(item['url']):08x}", venture_slug=slug, source=item["source"],
                title=item["title"][:200], url=item["url"], author=item["author"],
                snippet=re.sub(r"\s+", " ", item["text"])[:280], intent_score=score, matched_signals=hits,
                suggested_action=(f"Reply on {item['source'].split('/')[0]} with a helpful answer; "
                                  f"offer the free '{kb['free_tools'][0]}' if it genuinely fits."),
            ))
        signals.sort(key=lambda s: s.intent_score, reverse=True)
        self._store(signals)
        return signals

    def _store(self, signals: List[LeadSignal]) -> None:
        try:
            existing = json.loads(self.signals_file.read_text(encoding="utf-8")) if self.signals_file.exists() else []
        except Exception:
            existing = []
        known = {s.get("url") for s in existing}
        existing += [asdict(s) for s in signals if s.url not in known]
        self.signals_file.write_text(json.dumps(existing[-2000:], indent=2), encoding="utf-8")

    def list_signals(self, venture_slug: Optional[str] = None, limit: int = 25) -> List[Dict[str, Any]]:
        try:
            items = json.loads(self.signals_file.read_text(encoding="utf-8"))
        except Exception:
            return []
        if venture_slug:
            items = [i for i in items if i.get("venture_slug") == _slugify(venture_slug)]
        return sorted(items, key=lambda i: i.get("intent_score", 0), reverse=True)[:limit]


# ═══════════════════════════════════════════════════════════════════════════════
# 4. FACADE – one call per business
# ═══════════════════════════════════════════════════════════════════════════════

class LEONBusinessIntelligence:
    def __init__(self, workspace_root: Optional[Path] = None):
        root = workspace_root or _WORKSPACE_ROOT
        self.ideation = IdeationEngine()
        self.brand_studio = BrandStudio(root)
        self.leads = LeadDiscovery(root)
        self.out_dir = root / "data" / "leon_intelligence" / "blueprints"
        self.out_dir.mkdir(parents=True, exist_ok=True)

    def build_blueprint(self, venture_name: str, niche: str, value_prop: str = "", problem: str = "",
                        audience_type: str = "b2b_smb", live_leads: bool = False) -> Dict[str, Any]:
        brand = self.brand_studio.get_or_create(venture_name, niche)
        ideas = self.ideation.generate_ideas(niche, problem)
        blueprint = {
            "venture": venture_name,
            "generated_at": _now(),
            "ideation_guidelines": IDEATION_GUIDELINES,
            "top_ideas": [asdict(i) for i in ideas],
            "tool_guidelines": self.ideation.tool_guidelines(niche),
            "brand": asdict(brand),
            "lead_playbook": self.leads.build_playbook(venture_name, niche, value_prop, audience_type),
            "live_lead_signals": [asdict(s) for s in self.leads.discover_signals(venture_name, niche, value_prop)[:10]]
            if live_leads else [],
        }
        (self.out_dir / f"{brand.slug}.json").write_text(json.dumps(blueprint, indent=2), encoding="utf-8")
        (self.out_dir / f"{brand.slug}.md").write_text(self.render_markdown(blueprint), encoding="utf-8")
        return blueprint

    @staticmethod
    def render_markdown(bp: Dict[str, Any]) -> str:
        b = bp["brand"]
        lines = [f"# {bp['venture']} — LEON Business Blueprint", "",
                 "## Ideation guidelines"]
        lines += [f"- **{g['rule']}** — {g['why']}" for g in bp["ideation_guidelines"]]
        lines += ["", "## Top ideas (ranked)"]
        for i, idea in enumerate(bp["top_ideas"], 1):
            lines += [f"### {i}. {idea['title']}  (score {idea['total_score']})", idea["pitch"],
                      f"- Core tools: {', '.join(idea['core_tools'])}",
                      f"- Free lead-magnet: {idea['free_lead_magnet_tool']}",
                      f"- Validate: " + " → ".join(idea["validation_steps"]), ""]
        tg = bp["tool_guidelines"]
        lines += ["## Tool guidelines"] + [f"- {p}" for p in tg["principles"]]
        lines += ["", "**Build order:**"] + [f"- {s}" for s in tg["build_order"]]
        lines += ["", "## Brand & UI",
                  f"- Archetype: `{b['archetype']}` · Radius: `{b['border_radius']}`",
                  f"- Primary: `{b['primary_scale']['500']}` (hue {b['primary_hue']}°) · Accent: `{b['accent_scale']['400']}`",
                  f"- Background: `{b['background']}` · Surface: `{b['surface']}`",
                  f"- Fonts: **{b['font_heading']}** / {b['font_body']}",
                  f"- Psychology: {b['color_psychology']}", f"- Voice: {b['brand_voice']}", ""]
        lp = bp["lead_playbook"]
        lines += ["## Lead discovery playbook", f"- ICP: {lp['ideal_customer_profile']}",
                  f"- Who: {lp['who_specifically']}", "- Channels: " + "; ".join(lp["priority_channels"]), "",
                  "**Search queries:**"] + [f"- {k}: `{v}`" for k, v in lp["search_queries"].items()]
        lines += ["", "**Outreach sequence:**"] + [f"- {s}" for s in lp["outreach_sequence"]]
        lines += ["", "**Compliance:**"] + [f"- {s}" for s in lp["compliance"]]
        if bp.get("live_lead_signals"):
            lines += ["", "## Live buying-intent signals"]
            lines += [f"- [{s['intent_score']}] [{s['title'][:90]}]({s['url']}) — {s['source']}"
                      for s in bp["live_lead_signals"]]
        return "\n".join(lines) + "\n"


leon_business_intelligence = LEONBusinessIntelligence()


# ═══════════════════════════════════════════════════════════════════════════════
# 5. ReWOO tool wrappers (LEON / AETHER)
# ═══════════════════════════════════════════════════════════════════════════════

def _resolve_venture(name_or_slug: str) -> Tuple[str, str, str, str]:
    """Look up a portfolio venture; returns (name, niche, value_prop, problem)."""
    try:
        from aether.brain.leon_portfolio_manager import leon_portfolio_manager
        slug = _slugify(name_or_slug)
        for s, v in leon_portfolio_manager.ventures.items():
            if s == slug or v.name.lower() == name_or_slug.lower():
                return v.name, v.niche, v.value_prop, v.problem
    except Exception:
        pass
    return name_or_slug, "general", "", ""


def tool_leon_generate_business_ideas(niche: str, problem: str = "", count: int = 5) -> str:
    """Generate ranked, unique business ideas + in-product tools for a niche using LEON's ideation guidelines."""
    ideas = leon_business_intelligence.ideation.generate_ideas(niche, problem, count=int(count))
    out = [f"### 💡 LEON Idea Lab — {niche}\n"]
    for i, idea in enumerate(ideas, 1):
        out.append(f"**{i}. {idea.title}** (score {idea.total_score})\n{idea.pitch}\n"
                   f"• Tools: {', '.join(idea.core_tools)}\n• Free lead-magnet: {idea.free_lead_magnet_tool}\n")
    return "\n".join(out)


def tool_leon_business_blueprint(venture_name_or_slug: str, live_leads: bool = False) -> str:
    """Build the full blueprint (ideas, tool guidelines, brand theme, lead playbook) for a business."""
    name, niche, vp, problem = _resolve_venture(venture_name_or_slug)
    bp = leon_business_intelligence.build_blueprint(name, niche, vp, problem, live_leads=bool(live_leads))
    path = leon_business_intelligence.out_dir / f"{_slugify(name)}.md"
    return f"📘 Blueprint for **{name}** saved to {path}\n\n" + leon_business_intelligence.render_markdown(bp)[:3500]


def tool_leon_customize_brand(venture_name_or_slug: str, primary_hex: str = "", accent_hex: str = "",
                              font_heading: str = "", font_body: str = "", archetype: str = "") -> str:
    """Customise a business's theme colours, fonts or UI archetype. Redeploy to apply live."""
    name, niche, _, _ = _resolve_venture(venture_name_or_slug)
    b = leon_business_intelligence.brand_studio.customize(
        name, primary_hex=primary_hex or None, accent_hex=accent_hex or None,
        font_heading=font_heading or None, font_body=font_body or None,
        archetype=archetype or None, niche=niche)
    return (f"🎨 Brand updated for **{b.venture_name}**: primary {b.primary}, accent {b.accent}, "
            f"fonts {b.font_heading}/{b.font_body}, archetype {b.archetype}. Redeploy to publish.")


def tool_leon_find_leads(venture_name_or_slug: str, live: bool = True) -> str:
    """Find real buying-intent leads (public Reddit/HN/GitHub posts) plus the channel playbook for a business."""
    name, niche, vp, _ = _resolve_venture(venture_name_or_slug)
    pb = leon_business_intelligence.leads.build_playbook(name, niche, vp)
    out = [f"### 🎯 Lead discovery — {name}", f"ICP: {pb['ideal_customer_profile']}",
           "Channels: " + "; ".join(pb["priority_channels"][:4])]
    if live:
        sigs = leon_business_intelligence.leads.discover_signals(name, niche, vp)
        out.append(f"\n**{len(sigs)} live intent signals found:**")
        out += [f"- [{s.intent_score}] {s.title[:90]} — {s.url}" for s in sigs[:10]]
        if not sigs:
            out.append("- None above threshold right now; use the search queries below.")
    out.append("\n**Search queries:**")
    out += [f"- {k}: `{v}`" for k, v in pb["search_queries"].items()]
    return "\n".join(out)
