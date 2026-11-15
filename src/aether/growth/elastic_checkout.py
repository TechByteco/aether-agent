"""
AETHER Elastic Checkout & Dynamic Pricing Engine (Evolution #2)
===============================================================
Generates dynamic payment links, discounted impulse tiers, and UPI QR payloads
for all 5 active LEON MicroSaaS ventures:

1. CogniGuard Cyber (₹149 / ₹49 impulse)
2. CloudFlow AI (₹199 / ₹79 impulse)
3. LeadPulse Pro (₹299 / ₹99 impulse)
4. Aether Sovereign OS (₹99 / ₹39 impulse)
5. ApexStudio AI (₹499 / ₹149 impulse)
"""

from __future__ import annotations

import json
import logging
import os
import urllib.parse
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("aether.growth.elastic_checkout")

VENTURE_PRICING_PLANS: Dict[str, Dict[str, Any]] = {
    "cogniguard-cyber": {
        "name": "CogniGuard Cyber",
        "standard_price_inr": 149,
        "impulse_price_inr": 49,
        "enterprise_price_inr": 999,
        "live_url": "https://cogniguard-cyber.vercel.app",
        "currency": "INR",
        "description": "Comprehensive domain security & vulnerability audit",
    },
    "cloudflow-ai": {
        "name": "CloudFlow AI",
        "standard_price_inr": 199,
        "impulse_price_inr": 79,
        "enterprise_price_inr": 1499,
        "live_url": "https://cloudflow-ai.vercel.app",
        "currency": "INR",
        "description": "Automated cloud cost reduction & architecture refactor plan",
    },
    "leadpulse-pro": {
        "name": "LeadPulse Pro",
        "standard_price_inr": 299,
        "impulse_price_inr": 99,
        "enterprise_price_inr": 1999,
        "live_url": "https://leadpulse-pro.vercel.app",
        "currency": "INR",
        "description": "50 verified niche B2B buyer leads & outreach scripts",
    },
    "aether-sovereign-os": {
        "name": "Aether Sovereign OS",
        "standard_price_inr": 99,
        "impulse_price_inr": 39,
        "enterprise_price_inr": 499,
        "live_url": "https://aether-os.vercel.app",
        "currency": "INR",
        "description": "Cryptographic offline personal AI software license",
    },
    "apexstudio-ai": {
        "name": "ApexStudio AI",
        "standard_price_inr": 499,
        "impulse_price_inr": 149,
        "enterprise_price_inr": 2999,
        "live_url": "https://apexstudio-ai.vercel.app",
        "currency": "INR",
        "description": "Agency-grade design tokens & landing page component kit",
    },
}


@dataclass
class CheckoutPayload:
    venture_slug: str
    venture_name: str
    plan_tier: str              # "standard", "impulse_discount", "enterprise"
    amount_inr: float
    checkout_url: str
    upi_intent_uri: str
    discount_pct: int
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat() + "Z")

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ElasticCheckoutEngine:
    """
    Constructs dynamic pricing and one-click checkout links.
    """

    def generate_checkout(
        self,
        venture_slug: str,
        tier: str = "standard",
        customer_email: Optional[str] = None
    ) -> CheckoutPayload:
        """Create a targeted checkout payload with dynamic pricing."""
        info = VENTURE_PRICING_PLANS.get(venture_slug, VENTURE_PRICING_PLANS["cogniguard-cyber"])
        standard = info["standard_price_inr"]

        if tier == "impulse_discount":
            price = info["impulse_price_inr"]
            discount = int(((standard - price) / standard) * 100)
        elif tier == "enterprise":
            price = info["enterprise_price_inr"]
            discount = 0
        else:
            price = standard
            discount = 0

        # Construct checkout URL
        params = {"plan": tier, "amount": str(price)}
        if customer_email:
            params["email"] = customer_email
        query_str = urllib.parse.urlencode(params)
        checkout_url = f"{info['live_url']}?{query_str}"

        # Standard UPI intent URI for instant mobile payments
        merchant_vpa = os.getenv("UPI_VPA", "aether.sovereign@upi")
        upi_params = {
            "pa": merchant_vpa,
            "pn": info["name"],
            "am": f"{price:.2f}",
            "cu": "INR",
            "tn": f"Payment for {info['name']} {tier.upper()}",
        }
        upi_uri = f"upi://pay?{urllib.parse.urlencode(upi_params)}"

        return CheckoutPayload(
            venture_slug=venture_slug,
            venture_name=info["name"],
            plan_tier=tier,
            amount_inr=price,
            checkout_url=checkout_url,
            upi_intent_uri=upi_uri,
            discount_pct=discount,
        )


elastic_checkout = ElasticCheckoutEngine()
