"""
AETHER Sovereign Email & Gmail FastAPI REST Gateway Router
===========================================================
Provides REST endpoints for email monitoring, AI summarization,
and secure outbound dispatch via Gmail IMAP/SMTP.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from aether.tools.cloud_email_agent import cloud_email_agent

logger = logging.getLogger("aether.web.email_router")

router = APIRouter(prefix="/api/email", tags=["Gmail & Email Operations"])


class SendEmailRequest(BaseModel):
    to: str
    subject: str
    body_text: str
    body_html: Optional[str] = None
    cc: Optional[List[str]] = None
    bcc: Optional[List[str]] = None
    in_reply_to: Optional[str] = None


class ReplyEmailRequest(BaseModel):
    original_msg_id: str
    reply_body: str
    to_sender: Optional[str] = ""
    subject: Optional[str] = ""


class SummarizeEmailRequest(BaseModel):
    sender: Optional[str] = "Unknown Sender"
    subject: Optional[str] = "No Subject"
    body_text: str


@router.get("/status")
def get_email_status() -> Dict[str, Any]:
    """Test and return Gmail IMAP/SMTP connection status."""
    return cloud_email_agent.test_connection()


@router.get("/inbox")
def get_inbox_emails(
    limit: int = Query(10, ge=1, le=50),
    unread_only: bool = Query(False)
) -> Dict[str, Any]:
    """Fetch recent or unread emails from Gmail."""
    emails = cloud_email_agent.fetch_emails(limit=limit, unread_only=unread_only)
    return {
        "count": len(emails),
        "unread_only": unread_only,
        "emails": [e.to_dict() for e in emails]
    }


@router.get("/summary")
def get_inbox_summary(
    limit: int = Query(10, ge=1, le=50),
    unread_only: bool = Query(False)
) -> Dict[str, Any]:
    """Generate an AI executive briefing and summary of the inbox."""
    return cloud_email_agent.summarize_inbox(limit=limit, unread_only=unread_only)


@router.post("/summarize")
def summarize_specific_email(req: SummarizeEmailRequest) -> Dict[str, Any]:
    """Deeply summarize a specific email and draft suggested replies."""
    return cloud_email_agent.summarize_single_email({
        "sender": req.sender,
        "subject": req.subject,
        "body_text": req.body_text
    })


@router.post("/send")
def send_outbound_email(req: SendEmailRequest) -> Dict[str, Any]:
    """Dispatch an email via Gmail SMTP."""
    res = cloud_email_agent.send_email(
        to_email=req.to,
        subject=req.subject,
        body_text=req.body_text,
        body_html=req.body_html,
        cc=req.cc,
        bcc=req.bcc,
        in_reply_to=req.in_reply_to
    )
    if not res.get("ok"):
        raise HTTPException(status_code=500, detail=res.get("error", "Email dispatch failed"))
    return res


@router.post("/reply")
def reply_to_inbound_email(req: ReplyEmailRequest) -> Dict[str, Any]:
    """Send a threaded reply to an existing email."""
    res = cloud_email_agent.reply_to_email(
        original_msg_id=req.original_msg_id,
        reply_body=req.reply_body,
        to_sender=req.to_sender or "",
        subject=req.subject or ""
    )
    if not res.get("ok"):
        raise HTTPException(status_code=500, detail=res.get("error", "Reply dispatch failed"))
    return res
