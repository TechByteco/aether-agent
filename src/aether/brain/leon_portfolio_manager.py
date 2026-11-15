"""
LEON Autonomous Business Portfolio & Dynamic Low-Cost Subscription Manager
==========================================================================
Coordinates LEON's full multi-venture business empire:
1. Portfolio Initialization: Launches high-converting businesses with ultra-low entry pricing.
2. 1-Click Multi-Cloud & Payment Provisioning: Deploys all ventures with Razorpay & Stripe.
3. Automated Multi-Channel Growth: Generates target leads, cold outreach copy, and SEO specs.
4. Dynamic Pricing Revision Engine: Incrementally scales subscription prices based on
   adoption metrics, feature maturation, and conversion velocity.
"""

import json
import logging
import os
import re
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from aether.brain.leon_deployer import (DeploymentResult, DeployProvider,
                                        leon_deployer)
from aether.brain.leon_growth_engine import (LeadProfile, OutreachMessage,
                                             SEOMetadataSpec,
                                             TargetAudienceType, UIArchetype,
                                             leon_growth_engine)
from aether.brain.leon_venture_os import VentureRecord, VentureStage, leon_os
from aether.config import config

logger = logging.getLogger("aether.leon_portfolio_manager")


@dataclass
class BusinessVentureSpec:
    slug: str
    name: str
    niche: str
    target_audience_type: TargetAudienceType
    value_prop: str
    problem: str
    features: List[str]
    initial_monthly_price_inr: float
    initial_annual_price_inr: float
    current_monthly_price_inr: float
    current_annual_price_inr: float
    price_revision_history: List[Dict[str, Any]] = field(default_factory=list)
    live_url: Optional[str] = None
    subscribers_count: int = 0
    total_revenue_inr: float = 0.0
    status: str = "active"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


CANONICAL_PORTFOLIO_SPECS: List[Dict[str, Any]] = [
    {
        "slug": "cloudflow-ai",
        "name": "CloudFlow AI",
        "niche": "developer_tools",
        "target_audience_type": TargetAudienceType.B2B_SMB,
        "value_prop": "Instant AI Infrastructure Drift Detection & Continuous AST Self-Healing",
        "problem": "DevOps teams spend 15+ hours weekly diagnosing cloud configuration drift and broken pipelines.",
        "features": [
            "Autonomous Real-Time Infrastructure Drift Detection & Rollback",
            "AST Code Syntax Verification & Micro-Patch Synthesis",
            "Zero-Cloud-Cost Local Static Analysis Engine",
            "Seamless GitHub Actions, GitLab CI & AWS/GCP Integrations",
            "Instant Telegram & Discord Alerting Webhooks"
        ],
        "initial_monthly_price_inr": 199.0,
        "initial_annual_price_inr": 1499.0,
    },
    {
        "slug": "leadpulse-pro",
        "name": "LeadPulse Pro",
        "niche": "agency_services",
        "target_audience_type": TargetAudienceType.B2B_ENTERPRISE,
        "value_prop": "Hyper-Targeted B2B Lead Scraping, Contact Enrichment & AI Cold Outreach",
        "problem": "Founders and sales teams waste hundreds of hours manually searching leads and writing low-response emails.",
        "features": [
            "Automated Multi-Channel Lead Discovery (LinkedIn, GitHub, Web)",
            "Deep Contact Qualification Scoring & Verified Email Discovery",
            "Anti-Spam Compliant Personalized Copywriting Engine",
            "1-Click CSV Export & CRM Direct Webhook Sync",
            "Automated Multi-Stage Follow-Up Cadence Dispatcher"
        ],
        "initial_monthly_price_inr": 299.0,
        "initial_annual_price_inr": 2499.0,
    },
    {
        "slug": "apexstudio-ai",
        "name": "ApexStudio AI",
        "niche": "agency_services",
        "target_audience_type": TargetAudienceType.CREATOR_FREELANCER,
        "value_prop": "High-Converting Interactive Animated Websites & Brand Systems in <30 Seconds",
        "problem": "Hiring agency designers costs ₹50,000+ and takes weeks to build luxury animated landing pages.",
        "features": [
            "Awwwards-Grade Interactive Tailwind CSS & Canvas Animations",
            "6 Dynamic Design Token Archetypes (Bento, Glass, Luxury, Terminal)",
            "Embedded Razorpay Instant UPI QR & Card Checkout Modals",
            "1-Click Instant Vercel & Netlify Cloud Deployment",
            "Built-in Schema.org JSON-LD Structured SEO Optimization"
        ],
        "initial_monthly_price_inr": 499.0,
        "initial_annual_price_inr": 3999.0,
    },
    {
        "slug": "cogniguard-cyber",
        "name": "CogniGuard Cyber",
        "niche": "cybersecurity",
        "target_audience_type": TargetAudienceType.B2B_SMB,
        "value_prop": "Automated Port Auditing, Secret Leak Detection & Real-Time Threat Reconnaissance",
        "problem": "Small businesses and indie devs suffer data breaches due to exposed API keys and open ports.",
        "features": [
            "Continuous Codebase & Repo Secret Leak Scanners",
            "Local & Remote Open Port Reconnaissance & SSL Inspection",
            "Automated CVE & Zero-Day Threat Intelligence Feed",
            "Zero Data Storage — 100% Client-Side Private Auditing",
            "Detailed Compliance Audit PDF & JSON Export"
        ],
        "initial_monthly_price_inr": 149.0,
        "initial_annual_price_inr": 1199.0,
    },
    {
        "slug": "aether-sovereign-os",
        "name": "Aether Sovereign OS",
        "niche": "productivity_saas",
        "target_audience_type": TargetAudienceType.INDIVIDUAL_PROSUMER,
        "value_prop": "24/7 Sovereign Personal AI Assistant with Snapdragon NPU Acceleration & Dual GPU Cloud Evolution",
        "problem": "Modern AI assistants are fragmented, cloud-dependent, leak private data, and lack persistent long-term memory.",
        "features": [
            "100% Private Local Inference via Snapdragon Hexagon NPU & DirectML",
            "24/7 Dual Tesla T4 Cloud RLAIF Self-Play Evolutionary Training",
            "Hybrid Dense RAG & Semantic Triples Knowledge Graph",
            "Native Computer Vision & Screen-Grounding Actuation",
            "Zero-CPU Hardware Wake-Word Engine & Voice Interaction"
        ],
        "initial_monthly_price_inr": 99.0,
        "initial_annual_price_inr": 799.0,
    },
]


class LEONPortfolioManager:
    """
    Manages LEON's multi-venture business catalog, subscription pricing revisions,
    and autonomous marketing orchestration.
    """

    def __init__(self, workspace_root: Optional[Path] = None):
        self.workspace_root = workspace_root or Path(__file__).resolve().parent.parent.parent.parent
        self.portfolio_file = self.workspace_root / "data" / "leon_portfolio_registry.json"
        self.portfolio_file.parent.mkdir(parents=True, exist_ok=True)
        self.ventures: Dict[str, BusinessVentureSpec] = {}
        self._load_portfolio()

    def _load_portfolio(self) -> None:
        if self.portfolio_file.exists():
            try:
                data = json.loads(self.portfolio_file.read_text(encoding="utf-8"))
                for k, v in data.items():
                    v["target_audience_type"] = TargetAudienceType(v["target_audience_type"])
                    self.ventures[k] = BusinessVentureSpec(**v)
                return
            except Exception as e:
                logger.warning(f"Error loading portfolio registry: {e}")

        # Seed canonical ventures if empty
        for item in CANONICAL_PORTFOLIO_SPECS:
            spec = BusinessVentureSpec(
                slug=item["slug"],
                name=item["name"],
                niche=item["niche"],
                target_audience_type=item["target_audience_type"],
                value_prop=item["value_prop"],
                problem=item["problem"],
                features=item["features"],
                initial_monthly_price_inr=item["initial_monthly_price_inr"],
                initial_annual_price_inr=item["initial_annual_price_inr"],
                current_monthly_price_inr=item["initial_monthly_price_inr"],
                current_annual_price_inr=item["initial_annual_price_inr"],
                price_revision_history=[{
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "monthly_price_inr": item["initial_monthly_price_inr"],
                    "annual_price_inr": item["initial_annual_price_inr"],
                    "reason": "Initial Low-Cost Launch Tier (Phase 1 Acquisition)"
                }]
            )
            self.ventures[spec.slug] = spec
        self._save_portfolio()

    def _save_portfolio(self) -> None:
        data = {}
        for k, v in self.ventures.items():
            d = asdict(v)
            d["target_audience_type"] = v.target_audience_type.value
            data[k] = d
        self.portfolio_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

    # ── 1. Launch All Businesses with Low-Cost Subscriptions ──────────────────
    def launch_all_low_cost_businesses(
        self,
        provider: DeployProvider = DeployProvider.VERCEL
    ) -> List[Dict[str, Any]]:
        """
        Launches every business model in the portfolio with low-cost entry subscriptions,
        generates production landing pages with Razorpay & Stripe integration,
        and deploys them live.
        """
        results = []
        for slug, spec in self.ventures.items():
            # 1. Register with LeonVentureOS
            leon_os.create_venture(
                name=spec.name,
                problem=spec.problem,
                target_users=[spec.target_audience_type.value, "General Public"],
                mission=f"Deliver accessible, high-ROI {spec.niche} tools at low cost.",
                budget_ceiling=0.0,
                north_star=f"Subscribers (₹{int(spec.current_monthly_price_inr)}/mo)"
            )

            # 2. Deploy Live to Cloud (Vercel / Netlify)
            dep = leon_deployer.deploy_venture(
                venture_name=spec.name,
                niche=spec.niche,
                value_prop=spec.value_prop,
                provider=provider,
                monthly_price_inr=spec.current_monthly_price_inr,
                annual_price_inr=spec.current_annual_price_inr,
            )
            spec.live_url = dep.live_url
            spec.status = "live"

            # 3. Seed initial qualified leads and outreach copy
            try:
                leads = leon_growth_engine.search_and_qualify_leads(
                    venture_name=spec.name,
                    niche=spec.niche,
                    value_prop=spec.value_prop,
                    target_audience_type=spec.target_audience_type,
                    count=3,
                )
                if leads:
                    leon_growth_engine.draft_personalized_outreach(
                        lead=leads[0],
                        venture_name=spec.name,
                        value_prop=spec.value_prop,
                        offering_link=spec.live_url,
                    )
            except Exception as e:
                logger.warning(f"Lead growth seed skipped for {spec.name}: {e}")

            results.append({
                "name": spec.name,
                "slug": spec.slug,
                "niche": spec.niche,
                "monthly_price": f"₹{int(spec.current_monthly_price_inr)}/mo",
                "annual_price": f"₹{int(spec.current_annual_price_inr)}/yr",
                "live_url": spec.live_url,
                "status": "DEPLOYED_LIVE"
            })

        self._save_portfolio()
        logger.info(f"✓ Successfully launched all {len(results)} LEON low-cost business models.")
        return results

    # ── 2. Gradual Pricing Revision Engine ───────────────────────────────────
    def revise_venture_pricing(
        self,
        slug_or_name: str,
        new_monthly_price_inr: float,
        new_annual_price_inr: float,
        reason: str = "Market maturation and feature expansion.",
        provider: DeployProvider = DeployProvider.VERCEL,
    ) -> Dict[str, Any]:
        """
        Gradually updates subscription pricing for a venture, redeploys the landing page
        with revised Razorpay/Stripe amounts, and archives the revision history.
        """
        spec = self._find_venture(slug_or_name)
        if not spec:
            raise ValueError(f"Venture '{slug_or_name}' not found in portfolio registry.")

        old_monthly = spec.current_monthly_price_inr
        old_annual = spec.current_annual_price_inr

        spec.current_monthly_price_inr = float(new_monthly_price_inr)
        spec.current_annual_price_inr = float(new_annual_price_inr)

        spec.price_revision_history.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "previous_monthly_price_inr": old_monthly,
            "previous_annual_price_inr": old_annual,
            "monthly_price_inr": spec.current_monthly_price_inr,
            "annual_price_inr": spec.current_annual_price_inr,
            "reason": reason,
        })

        # Re-deploy with new pricing structure
        dep = leon_deployer.deploy_venture(
            venture_name=spec.name,
            niche=spec.niche,
            value_prop=spec.value_prop,
            provider=provider,
            monthly_price_inr=spec.current_monthly_price_inr,
            annual_price_inr=spec.current_annual_price_inr,
        )
        spec.live_url = dep.live_url

        self._save_portfolio()

        return {
            "success": True,
            "venture_name": spec.name,
            "slug": spec.slug,
            "previous_pricing": f"₹{int(old_monthly)}/mo (₹{int(old_annual)}/yr)",
            "new_pricing": f"₹{int(spec.current_monthly_price_inr)}/mo (₹{int(spec.current_annual_price_inr)}/yr)",
            "revision_reason": reason,
            "live_url": spec.live_url,
            "total_revisions": len(spec.price_revision_history)
        }

    def auto_scale_portfolio_tiers(
        self,
        increment_percent: float = 20.0,
        provider: DeployProvider = DeployProvider.VERCEL,
    ) -> List[Dict[str, Any]]:
        """
        Gradually steps up subscription prices across all mature ventures by a specified percentage.
        """
        revisions = []
        for slug, spec in self.ventures.items():
            new_mo = round(spec.current_monthly_price_inr * (1 + increment_percent / 100.0), -1)
            new_yr = round(spec.current_annual_price_inr * (1 + increment_percent / 100.0), -2)
            res = self.revise_venture_pricing(
                slug_or_name=slug,
                new_monthly_price_inr=new_mo,
                new_annual_price_inr=new_yr,
                reason=f"Systematic +{int(increment_percent)}% Portfolio Value & Demand Revision",
                provider=provider,
            )
            revisions.append(res)
        return revisions


    def get_portfolio_summary(self) -> List[Dict[str, Any]]:
        return [
            {
                "slug": spec.slug,
                "name": spec.name,
                "niche": spec.niche,
                "current_monthly_price": f"₹{int(spec.current_monthly_price_inr)}",
                "current_annual_price": f"₹{int(spec.current_annual_price_inr)}",
                "initial_monthly_price": f"₹{int(spec.initial_monthly_price_inr)}",
                "revisions_count": len(spec.price_revision_history),
                "live_url": spec.live_url or "Not Deployed",
                "status": spec.status
            }
            for spec in self.ventures.values()
        ]

    def _find_venture(self, query: str) -> Optional[BusinessVentureSpec]:
        q = query.lower().strip()
        if q in self.ventures:
            return self.ventures[q]
        for k, v in self.ventures.items():
            if q in k or q in v.name.lower():
                return v
        return None


leon_portfolio_manager = LEONPortfolioManager()


# ─── Native ReWOO Tool Wrappers ───────────────────────────────────────────────

def tool_leon_launch_all_low_cost_businesses(provider: str = "vercel") -> str:
    """
    Launch and deploy all 5 core business models (CloudFlow, LeadPulse, ApexStudio, CogniGuard, Aether OS)
    with ultra-low cost subscription tiers (₹99-₹499/mo), Razorpay UPI/Card checkout, and live URLs.
    """
    try:
        prov = DeployProvider(provider.lower().strip())
    except Exception:
        prov = DeployProvider.VERCEL

    results = leon_portfolio_manager.launch_all_low_cost_businesses(provider=prov)

    lines = [f"### 🚀 LEON Autonomous Business Empire — All {len(results)} Low-Cost Ventures Launched Live!\n"]
    lines.append("| Venture Name | Niche | Low-Cost Subscription | Live Public URL | Status |")
    lines.append("| :--- | :--- | :--- | :--- | :--- |")
    for r in results:
        lines.append(f"| **{r['name']}** | `{r['niche']}` | **{r['monthly_price']}** ({r['annual_price']}) | [{r['name']} Live]({r['live_url']}) | `{r['status']}` |")

    lines.append("\n**Integrated Payment Gateways:**")
    lines.append("- Razorpay Instant UPI (GPay, PhonePe, Paytm, QR) & Cards (`rzp_live_Tj2ag5qTYKE8Ea`)")
    lines.append("- Stripe Multi-Currency Global Checkout")
    lines.append("\n*All ventures are active and ready to receive traffic, collect subscribers, and gradually revise pricing.*")
    return "\n".join(lines)


def tool_leon_get_portfolio_status() -> str:
    """
    Get the real-time status, live URLs, subscription pricing, and revision history of all LEON business models.
    """
    summary = leon_portfolio_manager.get_portfolio_summary()
    lines = ["### 📊 LEON Multi-Venture Portfolio Status & Pricing Ledger:\n"]
    lines.append("| Venture Name | Niche | Active Pricing | Initial Launch | Revisions | Live URL |")
    lines.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
    for item in summary:
        lines.append(
            f"| **{item['name']}** | `{item['niche']}` | **{item['current_monthly_price']}/mo** | {item['initial_monthly_price']}/mo | {item['revisions_count']} | {item['live_url']} |"
        )
    return "\n".join(lines)


def tool_leon_revise_business_pricing(
    venture_name_or_slug: str,
    new_monthly_price_inr: float,
    new_annual_price_inr: float,
    reason: str = "Demand growth and feature expansion.",
    provider: str = "vercel",
) -> str:
    """
    Gradually update subscription pricing for a specific business model, updating live Razorpay checkout amounts.
    """
    try:
        prov = DeployProvider(provider.lower().strip())
    except Exception:
        prov = DeployProvider.VERCEL

    res = leon_portfolio_manager.revise_venture_pricing(
        slug_or_name=venture_name_or_slug,
        new_monthly_price_inr=float(new_monthly_price_inr),
        new_annual_price_inr=float(new_annual_price_inr),
        reason=reason,
        provider=prov,
    )
    return (
        f"📈 [LEON Pricing Revision] Updated '{res['venture_name']}':\n"
        f"• Previous Pricing: {res['previous_pricing']}\n"
        f"• New Active Pricing: **{res['new_pricing']}**\n"
        f"• Reason: {res['revision_reason']}\n"
        f"• Redeployed Live URL: {res['live_url']}\n"
        f"• Total Historical Revisions: {res['total_revisions']}"
    )



def tool_leon_auto_scale_portfolio_pricing(increment_percent: float = 20.0) -> str:
    """
    Gradually step up subscription tiers across the entire portfolio by a specified percentage (e.g. +20%).
    """
    revs = leon_portfolio_manager.auto_scale_portfolio_tiers(increment_percent=float(increment_percent))
    lines = [f"### 📈 Scaled All Portfolio Subscription Tiers (+{int(increment_percent)}%):\n"]
    for r in revs:
        lines.append(f"- **{r['venture_name']}**: {r['previous_pricing']} ➔ **{r['new_pricing']}**")
    return "\n".join(lines)
