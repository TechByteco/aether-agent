"""
AETHER Samsung One UI 8 & Android HTTP Gateway Router
======================================================
Provides REST endpoints to connect Samsung Galaxy One UI 8 devices,
Samsung Modes & Routines webhooks, and Android 1-tap intent builders.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from aether.tools.samsung_android_controller import samsung_android

logger = logging.getLogger("aether.channels.samsung_router")

router = APIRouter(prefix="/api/channels/samsung", tags=["Samsung One UI 8"])


class RoutineTriggerRequest(BaseModel):
    routine: str
    payload: Optional[Dict[str, Any]] = None


class AlarmRequest(BaseModel):
    time_str: str
    label: Optional[str] = "AETHER Alarm"


class MeetingRequest(BaseModel):
    title: str
    start_time_iso: Optional[str] = None
    duration_minutes: Optional[int] = 30
    description: Optional[str] = ""
    meeting_url: Optional[str] = None


class QuickActionRequest(BaseModel):
    action_type: str  # "call", "sms", "email", "navigation"
    target: str       # phone number, email address, or search query
    subject: Optional[str] = ""
    body: Optional[str] = ""
    contact_name: Optional[str] = "Contact"


@router.get("/status")
def get_samsung_integration_status() -> Dict[str, Any]:
    """Return status and supported protocols for Samsung One UI 8 integration."""
    return {
        "status": "online",
        "target_platform": "Samsung Galaxy One UI 8 (Android 15/16)",
        "protocols_supported": [
            "android_intent_clock",
            "google_samsung_calendar_template",
            "tel_dialer",
            "sms_protocol",
            "mailto_protocol",
            "google_maps_navigation"
        ],
        "routines_supported": [
            "bedtime",
            "wake_up",
            "driving",
            "work_focus",
            "battery_low",
            "custom"
        ],
        "timestamp": datetime.now(timezone.utc).isoformat() + "Z"
    }


@router.post("/routine")
def trigger_samsung_routine(req: RoutineTriggerRequest) -> Dict[str, Any]:
    """
    Receive webhook trigger from Samsung Modes & Routines / Bixby / Tasker.
    """
    if not req.routine.strip():
        raise HTTPException(status_code=400, detail="routine name required")
    res = samsung_android.handle_routine_trigger(routine_name=req.routine, payload=req.payload)
    return res


@router.post("/alarm")
def create_samsung_alarm_card(req: AlarmRequest) -> Dict[str, Any]:
    """Generate 1-tap Samsung Clock / Calendar alarm action card."""
    card_msg, keyboard = samsung_android.build_samsung_alarm_card(time_str=req.time_str, label=req.label or "AETHER Alarm")
    intent_data = samsung_android.generate_samsung_alarm_intent(time_str=req.time_str, label=req.label or "AETHER Alarm")
    return {
        "card_message": card_msg,
        "reply_markup": keyboard,
        "intent_data": intent_data
    }


@router.post("/meeting")
def create_samsung_meeting_card(req: MeetingRequest) -> Dict[str, Any]:
    """Generate 1-tap Samsung Calendar meeting action card."""
    if req.start_time_iso:
        try:
            start_dt = datetime.fromisoformat(req.start_time_iso.replace("Z", "+00:00"))
        except Exception:
            start_dt = datetime.now(timezone.utc)
    else:
        start_dt = datetime.now(timezone.utc)

    card_msg, keyboard = samsung_android.build_samsung_meeting_card(
        title=req.title,
        start_time=start_dt,
        duration_minutes=req.duration_minutes or 30,
        description=req.description or "",
        meeting_url=req.meeting_url
    )
    cal_link = samsung_android.generate_samsung_calendar_link(
        title=req.title,
        start_time=start_dt,
        duration_minutes=req.duration_minutes or 30,
        description=req.description or ""
    )
    return {
        "card_message": card_msg,
        "reply_markup": keyboard,
        "calendar_url": cal_link
    }


@router.post("/quick-action")
def create_samsung_quick_action(req: QuickActionRequest) -> Dict[str, Any]:
    """Generate 1-tap deep links for phone, sms, email, or navigation."""
    action = req.action_type.lower()
    if action == "call":
        msg, kb = samsung_android.build_phone_action_card(phone_number=req.target, contact_name=req.contact_name or "Contact")
        return {"action": "call", "card_message": msg, "reply_markup": kb}
    elif action == "sms":
        msg, kb = samsung_android.build_sms_action_card(phone_number=req.target, message=req.body or "", contact_name=req.contact_name or "Contact")
        return {"action": "sms", "card_message": msg, "reply_markup": kb}
    elif action == "email":
        msg, kb = samsung_android.build_email_action_card(to_email=req.target, subject=req.subject or "", body=req.body or "")
        return {"action": "email", "card_message": msg, "reply_markup": kb}
    elif action in ["navigation", "maps", "location"]:
        msg, kb = samsung_android.build_navigation_card(query=req.target, label=req.contact_name or "Destination")
        return {"action": "navigation", "card_message": msg, "reply_markup": kb}
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported action_type: {req.action_type}")
