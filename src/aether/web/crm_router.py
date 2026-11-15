"""
AETHER CRM & Enterprise Sales Web Router
========================================
Endpoints for managing sales pipeline, enterprise deals, auto-reply scheduling,
and real-time deal stage transitions.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from aether.growth.crm_pipeline import crm_pipeline

router = APIRouter(prefix="/api/crm", tags=["crm"])


class CreateDealRequest(BaseModel):
    company_name: str
    contact_name: str
    contact_email: str
    venture_name: str
    deal_value_inr: float
    stage: Optional[str] = "lead"
    notes: Optional[str] = ""


class AdvanceStageRequest(BaseModel):
    deal_id: str
    stage: str


class ScheduleMeetingRequest(BaseModel):
    deal_id: str
    meeting_datetime_iso: Optional[str] = None
    duration_minutes: Optional[int] = 30
    meeting_url: Optional[str] = None


class AutoReplyInquiryRequest(BaseModel):
    deal_id_or_email: str
    reply_type: Optional[str] = "schedule_demo" # "schedule_demo" or "custom_proposal"
    custom_message: Optional[str] = None


@router.get("/pipeline")
async def get_crm_pipeline() -> Dict[str, Any]:
    """Get complete CRM pipeline metrics, stage distributions, and deals."""
    return {"status": "ok", "pipeline": crm_pipeline.get_pipeline_summary()}


@router.post("/deal")
async def create_deal_endpoint(req: CreateDealRequest) -> Dict[str, Any]:
    """Create a new enterprise sales deal."""
    deal = crm_pipeline.create_deal(
        company_name=req.company_name,
        contact_name=req.contact_name,
        contact_email=req.contact_email,
        venture_name=req.venture_name,
        deal_value_inr=req.deal_value_inr,
        stage=req.stage or "lead",
        notes=req.notes or "",
    )
    return {"status": "ok", "deal": deal}


@router.post("/advance_stage")
async def advance_deal_stage_endpoint(req: AdvanceStageRequest) -> Dict[str, Any]:
    """Move deal to next stage."""
    res = crm_pipeline.advance_stage(deal_id=req.deal_id, new_stage=req.stage)
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res


@router.post("/schedule_meeting")
async def schedule_meeting_endpoint(req: ScheduleMeetingRequest) -> Dict[str, Any]:
    """Schedule meeting, register calendar event, and auto-dispatch confirmation email."""
    if req.meeting_datetime_iso:
        dt = datetime.fromisoformat(req.meeting_datetime_iso.replace("Z", "+00:00"))
    else:
        # Default next Thursday 3:00 PM IST (09:30 UTC)
        dt = datetime.now(timezone.utc)
    res = crm_pipeline.schedule_enterprise_meeting(
        deal_id=req.deal_id,
        meeting_datetime=dt,
        duration_minutes=req.duration_minutes or 30,
        meeting_url=req.meeting_url,
    )
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res


@router.post("/reply_inquiry")
async def reply_inquiry_endpoint(req: AutoReplyInquiryRequest) -> Dict[str, Any]:
    """Execute 1-click auto-reply for enterprise inquiry."""
    deal = crm_pipeline.get_deal(req.deal_id_or_email)
    if not deal:
        deals = crm_pipeline.list_deals()
        deal = next((d for d in deals if d.get("contact_email") == req.deal_id_or_email), None)
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    from aether.tools.cloud_email_agent import cloud_email_agent
    if req.reply_type == "schedule_demo":
        time_iso = deal.get("meeting_time_iso") or "2026-10-22T09:30:00Z"
        dt = datetime.fromisoformat(time_iso.replace("Z", "+00:00"))
        res = crm_pipeline.schedule_enterprise_meeting(
            deal_id=deal["id"],
            meeting_datetime=dt,
            duration_minutes=30
        )
        return {"status": "ok", "action": "demo_scheduled", "details": res}
    else:
        # Send proposal email
        body = req.custom_message or (
            f"Hi {deal['contact_name']},\n\n"
            f"Here is our Enterprise SLA proposal for {deal['venture_name']}. "
            f"We are excited to support {deal['company_name']} with continuous vulnerability defense.\n\n"
            f"Best regards,\nSaalim"
        )
        email_res = cloud_email_agent.send_email(
            to_email=deal["contact_email"],
            subject=f"Enterprise Proposal: {deal['company_name']} x {deal['venture_name']}",
            body_text=body
        )
        crm_pipeline.advance_stage(deal["id"], "proposal_sent")
        return {"status": "ok", "action": "proposal_sent", "email": email_res}
