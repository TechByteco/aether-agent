"""
AETHER Executive Triage & Priority Matrix Engine (Evolution #18)
================================================================
Classifies inbound messages, customer requests, and system alerts into the
4 Eisenhower-Executive Matrix quadrants and synthesizes one-touch draft responses:

  • Q1 (Urgent & Important)     — Paying customers, downtime alerts, security incidents (Instant Alert)
  • Q2 (Important & Non-Urgent) — Strategic venture scaling, Kaggle model training, architecture refactors
  • Q3 (Urgent & Non-Important) — Routine notifications, unsolicited sales pitches (Auto-archive)
  • Q4 (Non-Urgent & Non-Important) — Automated bulk digests, marketing newsletters (Mute)
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("aether.tools.executive_triage")


@dataclass
class TriageItem:
    id: str
    sender: str
    subject: str
    body_snippet: str
    quadrant: str                 # "Q1_URGENT_IMPORTANT", "Q2_STRATEGIC", "Q3_DELEGATE", "Q4_MUTE"
    priority_score: int           # 1 (Highest) to 5 (Lowest)
    suggested_action: str
    drafted_reply: Optional[str]
    triaged_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat() + "Z")

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ExecutiveTriageEngine:
    """
    Classifies incoming communications and protects executive bandwidth.
    """

    def triage_message(self, sender: str, subject: str, body: str) -> TriageItem:
        """Categorize an incoming message and draft an executive response."""
        text = f"{subject} {body}".lower()
        item_id = f"triage_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

        # 1. Check for Q1 (Paying customers, security, site down)
        if any(w in text for w in ["payment captured", "refund", "site down", "500 internal", "security vulnerability", "breach", "urgent bug"]):
            return TriageItem(
                id=item_id,
                sender=sender,
                subject=subject,
                body_snippet=body[:200],
                quadrant="Q1_URGENT_IMPORTANT",
                priority_score=1,
                suggested_action="Immediate Review & Automated Customer Fulfillment",
                drafted_reply=(
                    f"Hello {sender.split('@')[0] if '@' in sender else sender},\n\n"
                    "Thank you for contacting us. We have received your inquiry and our automated systems "
                    "are already verifying the details. You will receive a resolution update shortly.\n\n"
                    "Best regards,\nAETHER Executive Operations"
                ),
            )

        # 2. Check for Q2 (Strategic partnerships, model training, features)
        if any(w in text for w in ["partnership", "api integration", "enterprise license", "consulting", "fine-tuning", "proposal"]):
            return TriageItem(
                id=item_id,
                sender=sender,
                subject=subject,
                body_snippet=body[:200],
                quadrant="Q2_STRATEGIC",
                priority_score=2,
                suggested_action="Schedule for Deep Work Block & Executive Decision Card",
                drafted_reply=(
                    f"Hi {sender.split('@')[0] if '@' in sender else sender},\n\n"
                    "Thank you for reaching out regarding this opportunity. "
                    "We are reviewing the proposal against our current institutional roadmap and will get back to you with next steps.\n\n"
                    "Sincerely,\nAETHER Executive Office"
                ),
            )

        # 3. Check for Q4 (Newsletters, marketing promos)
        if any(w in text for w in ["unsubscribe", "newsletter", "weekly digest", "promotions", "no-reply"]):
            return TriageItem(
                id=item_id,
                sender=sender,
                subject=subject,
                body_snippet=body[:200],
                quadrant="Q4_MUTE",
                priority_score=5,
                suggested_action="Auto-Mute & Archive to Background Storage",
                drafted_reply=None,
            )

        # 4. Default Q3 (Routine notifications)
        return TriageItem(
            id=item_id,
            sender=sender,
            subject=subject,
            body_snippet=body[:200],
            quadrant="Q3_DELEGATE",
            priority_score=3,
            suggested_action="Log to Intelligence Stream; No Immediate Action Required",
            drafted_reply=None,
        )


executive_triage = ExecutiveTriageEngine()
