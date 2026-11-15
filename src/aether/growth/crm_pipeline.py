"""
AETHER Sovereign CRM & Enterprise Sales Pipeline Engine
=======================================================
Tracks inbound and outbound high-value deals across life-cycle stages:
  • lead -> contacted -> demo_scheduled -> proposal_sent -> negotiation -> closed_won -> closed_lost

Features:
  • Auto-booking calendar meetings via cloud_calendar_agent
  • Auto-drafting and dispatching customized confirmation emails via cloud_email_agent
  • Real-time weighted pipeline valuation & MRR forecasting
  • Direct sync with Razorpay payments and owner dashboard
"""

from __future__ import annotations

import json
import logging
import os
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("aether.growth.crm_pipeline")

_WORKSPACE = Path(__file__).resolve().parent.parent.parent.parent
_INTEL_DIR = _WORKSPACE / "data" / "leon_intelligence"
_CRM_FILE = _INTEL_DIR / "crm_pipeline.json"

_INTEL_DIR.mkdir(parents=True, exist_ok=True)
_LOCK = threading.Lock()

DEAL_STAGE_WEIGHTS = {
    "lead": 0.10,
    "contacted": 0.25,
    "demo_scheduled": 0.50,
    "proposal_sent": 0.75,
    "negotiation": 0.90,
    "closed_won": 1.00,
    "closed_lost": 0.00,
}


@dataclass
class CRMDeal:
    id: str
    company_name: str
    contact_name: str
    contact_email: str
    venture_name: str
    stage: str                     # "lead", "demo_scheduled", etc.
    deal_value_inr: float
    probability: float
    notes: str = ""
    meeting_time_iso: Optional[str] = None
    meeting_url: Optional[str] = None
    last_contact_at: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat() + "Z")
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat() + "Z")

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class CRMPipelineEngine:
    """
    Autonomous Enterprise Deal Tracker and Pipeline Acceleration Engine.
    """

    def __init__(self):
        self._ensure_seed_pipeline()

    def _ensure_seed_pipeline(self) -> None:
        """Seed default high-intent enterprise prospect if not present."""
        deals = self._load_deals()
        if not any(d.get("id") == "deal_apexfintech_101" for d in deals):
            seed_deal = CRMDeal(
                id="deal_apexfintech_101",
                company_name="ApexFintech",
                contact_name="Siddharth Mehta",
                contact_email="siddharth@apexfintech.io",
                venture_name="CogniGuard Cyber",
                stage="demo_scheduled",
                deal_value_inr=180000.0,
                probability=0.50,
                notes="Inquiry for 15-domain continuous vulnerability monitoring & Enterprise SLA.",
                meeting_time_iso="2026-10-22T09:30:00Z", # Thursday 3:00 PM IST (09:30 UTC)
                meeting_url="https://meet.google.com/aet-cgn-fin",
                last_contact_at=datetime.now(timezone.utc).isoformat() + "Z",
            )
            deals.append(seed_deal.to_dict())
            self._save_deals(deals)

    def _load_deals(self) -> List[Dict[str, Any]]:
        with _LOCK:
            try:
                if _CRM_FILE.exists():
                    return json.loads(_CRM_FILE.read_text(encoding="utf-8"))
            except Exception as e:
                logger.warning(f"Failed to load CRM pipeline: {e}")
        return []

    def _save_deals(self, deals: List[Dict[str, Any]]) -> None:
        with _LOCK:
            _CRM_FILE.write_text(json.dumps(deals[-200:], indent=2, ensure_ascii=False), encoding="utf-8")

    def list_deals(self) -> List[Dict[str, Any]]:
        return self._load_deals()

    def get_deal(self, deal_id: str) -> Optional[Dict[str, Any]]:
        deals = self._load_deals()
        for d in deals:
            if d.get("id") == deal_id:
                return d
        return None

    def create_deal(
        self,
        company_name: str,
        contact_name: str,
        contact_email: str,
        venture_name: str,
        deal_value_inr: float,
        stage: str = "lead",
        notes: str = ""
    ) -> Dict[str, Any]:
        """Create a new enterprise opportunity."""
        clean_stage = stage.lower() if stage.lower() in DEAL_STAGE_WEIGHTS else "lead"
        deal_id = f"deal_{int(datetime.now(timezone.utc).timestamp())}_{company_name.lower().replace(' ', '_')[:8]}"
        deal = CRMDeal(
            id=deal_id,
            company_name=company_name,
            contact_name=contact_name,
            contact_email=contact_email,
            venture_name=venture_name,
            stage=clean_stage,
            deal_value_inr=deal_value_inr,
            probability=DEAL_STAGE_WEIGHTS.get(clean_stage, 0.1),
            notes=notes,
            last_contact_at=datetime.now(timezone.utc).isoformat() + "Z",
        )
        deals = self._load_deals()
        deals.append(deal.to_dict())
        self._save_deals(deals)
        return deal.to_dict()

    def advance_stage(self, deal_id: str, new_stage: str) -> Dict[str, Any]:
        """Move a deal to a new stage and adjust win probability."""
        deals = self._load_deals()
        target = None
        for d in deals:
            if d.get("id") == deal_id:
                target = d
                break
        if not target:
            return {"error": "Deal not found"}

        clean_stage = new_stage.lower()
        if clean_stage not in DEAL_STAGE_WEIGHTS:
            return {"error": f"Invalid stage. Allowed: {list(DEAL_STAGE_WEIGHTS.keys())}"}

        target["stage"] = clean_stage
        target["probability"] = DEAL_STAGE_WEIGHTS[clean_stage]
        target["updated_at"] = datetime.now(timezone.utc).isoformat() + "Z"
        self._save_deals(deals)
        return {"status": "ok", "deal": target}

    def schedule_enterprise_meeting(
        self,
        deal_id: str,
        meeting_datetime: datetime,
        duration_minutes: int = 30,
        meeting_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Schedule calendar meeting and automatically dispatch confirmation email.
        """
        deals = self._load_deals()
        target = None
        for d in deals:
            if d.get("id") == deal_id or d.get("contact_email") == deal_id:
                target = d
                break
        if not target:
            return {"error": "Deal not found"}

        meet_link = meeting_url or f"https://meet.google.com/aet-{target['company_name'][:3].lower()}-{int(meeting_datetime.timestamp()) % 1000}"

        # 1. Register in Cloud Calendar
        from aether.tools.cloud_calendar_agent import cloud_calendar_agent
        event = cloud_calendar_agent.add_event(
            title=f"Enterprise Onboarding: {target['company_name']} x {target['venture_name']}",
            start_time=meeting_datetime,
            duration_minutes=duration_minutes,
            description=f"Strategic onboarding and SLA contract discussion with {target['contact_name']}.",
            meeting_url=meet_link,
            location="Google Meet"
        )

        # 2. Update Deal status
        target["stage"] = "demo_scheduled"
        target["probability"] = DEAL_STAGE_WEIGHTS["demo_scheduled"]
        target["meeting_time_iso"] = meeting_datetime.isoformat() + "Z"
        target["meeting_url"] = meet_link
        target["updated_at"] = datetime.now(timezone.utc).isoformat() + "Z"
        self._save_deals(deals)

        # 3. Auto-Dispatch Confirmation Email
        email_sent = False
        email_err = None
        try:
            from aether.tools.cloud_email_agent import cloud_email_agent
            time_formatted = meeting_datetime.strftime("%A, %B %d at %I:%M %p UTC")
            body_text = (
                f"Hi {target['contact_name']},\n\n"
                f"Thank you for connecting! I'm pleased to confirm our call regarding {target['venture_name']} "
                f"and your 15-domain Enterprise SLA requirements.\n\n"
                f"📅 Scheduled Time: {time_formatted}\n"
                f"📹 Meeting Link: {meet_link}\n\n"
                f"Agenda:\n"
                f"1. CogniGuard Cyber Architecture & Continuous Staging Scan Telemetry\n"
                f"2. Multi-Domain SLA Coverage & Custom Webhook Alerting\n"
                f"3. Enterprise Pricing, Terms & Seamless Onboarding\n\n"
                f"Looking forward to speaking with you!\n\n"
                f"Best regards,\n"
                f"Saalim\nAETHER Executive Systems"
            )
            email_res = cloud_email_agent.send_email(
                to_email=target["contact_email"],
                subject=f"Confirmed: {target['company_name']} x {target['venture_name']} Onboarding Call",
                body_text=body_text
            )
            email_sent = not email_res.get("simulated", False)
        except Exception as e:
            email_err = str(e)
            logger.warning(f"Meeting confirmation email note: {e}")

        return {
            "status": "ok",
            "calendar_event": event.to_dict(),
            "meeting_url": meet_link,
            "deal": target,
            "email_dispatched": email_sent,
            "email_note": email_err or "Dispatched successfully"
        }

    def get_pipeline_summary(self) -> Dict[str, Any]:
        """Compute aggregated metrics for Web UI Dashboard."""
        deals = self._load_deals()
        total_val = sum(d.get("deal_value_inr", 0) for d in deals)
        weighted_val = sum(d.get("deal_value_inr", 0) * d.get("probability", 0.1) for d in deals)
        
        stages_count = {}
        for s in DEAL_STAGE_WEIGHTS.keys():
            stages_count[s] = 0
        for d in deals:
            st = d.get("stage", "lead")
            stages_count[st] = stages_count.get(st, 0) + 1

        active_deals = [d for d in deals if d.get("stage") not in ("closed_won", "closed_lost")]

        return {
            "total_deals_count": len(deals),
            "active_deals_count": len(active_deals),
            "total_pipeline_value_inr": total_val,
            "weighted_pipeline_value_inr": round(weighted_val, 2),
            "stage_breakdown": stages_count,
            "deals": deals,
        }


crm_pipeline = CRMPipelineEngine()
