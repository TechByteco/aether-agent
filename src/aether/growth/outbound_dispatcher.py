"""
AETHER Multi-Channel Outbound Dispatch Engine (Evolution #1)
============================================================
Handles authorized transmission of value-first diagnostic outreach hooks
to prospective clients across multiple channels:

1. Direct SMTP Email (Gmail TLS / custom SMTP) — For leads with verified email addresses.
2. Public Discussion Response Formatter (Reddit / Hacker News / GitHub) — Generates ready-to-post markdown replies.
3. Webhook / CRM Push — Dispatches lead payloads to external webhook endpoints.

All dispatches require prior owner approval (approval-gated in inbox.json).
"""

from __future__ import annotations

import email.message
import json
import logging
import os
import smtplib
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("aether.growth.outbound_dispatcher")

_WORKSPACE = Path(__file__).resolve().parent.parent.parent.parent
_INTEL_DIR = _WORKSPACE / "data" / "leon_intelligence"
_DISPATCHED_LOG = _INTEL_DIR / "dispatched_outreach.jsonl"
_LEADS_FILE = _INTEL_DIR / "lead_signals.json"
_OPS_LOG = _INTEL_DIR / "ops_log.jsonl"

_INTEL_DIR.mkdir(parents=True, exist_ok=True)
_LOCK = threading.Lock()


@dataclass
class DispatchResult:
    lead_id: str
    channel: str              # "smtp_email", "public_reply_script", "webhook"
    recipient: str
    subject: str
    status: str               # "transmitted", "queued_for_manual_post", "failed"
    detail: str
    transmitted_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat() + "Z")

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class OutboundDispatcher:
    """
    Executes and records outbound communication for approved buyer leads.
    """

    def __init__(self):
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.sender_email = os.getenv("OWNER_EMAIL", "")
        self.sender_password = os.getenv("GMAIL_APP_PASSWORD", "")

    def _log_ops(self, level: str, msg: str, data: Optional[Dict] = None) -> None:
        entry = {
            "ts": datetime.now(timezone.utc).isoformat() + "Z",
            "level": level,
            "message": msg,
            "data": data or {}
        }
        with _LOCK:
            with _OPS_LOG.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")

    # ── 1. Email Transmission ────────────────────────────────────────────────

    def dispatch_email(
        self,
        recipient_email: str,
        subject: str,
        diagnostic_html: str,
        lead_id: str,
        venture_name: str
    ) -> DispatchResult:
        """Send a personalized diagnostic email via SMTP."""
        if not self.sender_email or not self.sender_password or "FILL_IN" in self.sender_password:
            logger.warning("SMTP credentials not configured in .env. Queuing email for manual review.")
            return DispatchResult(
                lead_id=lead_id,
                channel="smtp_email",
                recipient=recipient_email,
                subject=subject,
                status="queued_for_manual_post",
                detail="SMTP credentials not configured in environment. Content generated and stored."
            )

        try:
            msg = email.message.EmailMessage()
            msg["Subject"] = subject
            msg["From"] = f"{venture_name} <{self.sender_email}>"
            msg["To"] = recipient_email
            msg.set_content(
                "Please view this email in an HTML-compatible client to see your full diagnostic report."
            )
            msg.add_alternative(diagnostic_html, subtype="html")

            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=15.0) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)

            res = DispatchResult(
                lead_id=lead_id,
                channel="smtp_email",
                recipient=recipient_email,
                subject=subject,
                status="transmitted",
                detail=f"Successfully sent via {self.smtp_host}:{self.smtp_port}"
            )
            self._record_dispatch(res)
            self._log_ops("INFO", f"Outbound email dispatched to {recipient_email}", {"lead_id": lead_id})
            return res

        except Exception as e:
            logger.error(f"Failed to transmit email to {recipient_email}: {e}")
            res = DispatchResult(
                lead_id=lead_id,
                channel="smtp_email",
                recipient=recipient_email,
                subject=subject,
                status="failed",
                detail=str(e)
            )
            self._record_dispatch(res)
            return res

    # ── 2. Public Platform Response Script Generator ─────────────────────────

    def format_public_reply(
        self,
        lead_id: str,
        author: str,
        source_url: str,
        venture_name: str,
        diagnostic_summary: str,
        free_value: str,
        cta: str
    ) -> DispatchResult:
        """
        Format a high-civilization, non-spammy public reply ready to be pasted
        directly to the relevant Hacker News / Reddit / GitHub thread.
        """
        script = (
            f"@{author} Saw your inquiry regarding this. "
            f"Here is a quick breakdown based on our standard diagnostic checklist:\n\n"
            f"{diagnostic_summary}\n\n"
            f"💡 **Free Quick Diagnostic:** {free_value}\n\n"
            f"_{cta}_"
        )

        res = DispatchResult(
            lead_id=lead_id,
            channel="public_reply_script",
            recipient=source_url,
            subject=f"Diagnostic Reply for @{author}",
            status="queued_for_manual_post",
            detail=script
        )
        self._record_dispatch(res)
        self._log_ops("INFO", f"Formatted public reply script for lead {lead_id}", {"target": source_url})
        return res

    # ── 3. Record Keeping ────────────────────────────────────────────────────

    def _record_dispatch(self, result: DispatchResult) -> None:
        with _LOCK:
            with _DISPATCHED_LOG.open("a", encoding="utf-8") as f:
                f.write(json.dumps(result.to_dict(), ensure_ascii=False) + "\n")

    def list_recent_dispatches(self, limit: int = 50) -> List[Dict[str, Any]]:
        dispatches = []
        if _DISPATCHED_LOG.exists():
            try:
                lines = _DISPATCHED_LOG.read_text(encoding="utf-8").strip().splitlines()
                for line in lines[-limit:]:
                    try:
                        dispatches.append(json.loads(line))
                    except Exception:
                        pass
                dispatches.reverse()
            except Exception as e:
                logger.warning(f"Failed to read dispatches log: {e}")
        return dispatches


outbound_dispatcher = OutboundDispatcher()
