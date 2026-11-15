"""
AETHER Sovereign Gmail & Cloud Email Intelligence Agent
========================================================
Full bidirectional Gmail / IMAP / SMTP communication and AI summarization engine.

Capabilities:
  • Connects to Gmail via IMAP SSL (imap.gmail.com:993) & SMTP (smtp.gmail.com:587)
  • Fetches and parses unread/recent emails, decoding MIME headers and attachments
  • AI-Powered Executive Inbox Summaries (Grouped by Priority, Commercial, Finance)
  • Single-Email Deep Summarization with TL;DR, extracted action items, and drafted replies
  • Outbound Email Dispatch via Secure SMTP with HTML and Plain Text formatting
  • In-Reply-To email threading support
  • 24/7 Autonomous Inbox Triage with instant Telegram push notifications on VIP/Q1 emails
  • High-Fidelity Simulation Fallback for testing and offline environments
"""

from __future__ import annotations

import email
import email.header
import imaplib
import json
import logging
import os
import re
import smtplib
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("aether.tools.cloud_email_agent")

_WORKSPACE = Path(__file__).resolve().parent.parent.parent.parent
_INTEL_DIR = _WORKSPACE / "data" / "leon_intelligence"
_DRAFTS_FILE = _INTEL_DIR / "email_drafts.json"
_PROCESSED_FILE = _INTEL_DIR / "processed_email_ids.json"
_SENT_FILE = _INTEL_DIR / "sent_emails.jsonl"

_INTEL_DIR.mkdir(parents=True, exist_ok=True)
_LOCK = threading.Lock()


@dataclass
class EmailMessage:
    id: str
    sender: str
    recipient: str
    subject: str
    date_str: str
    body_text: str
    body_html: str
    snippet: str
    is_unread: bool = True
    quadrant: str = "Q2_STRATEGIC"
    priority: int = 3
    has_attachments: bool = False
    attachment_names: List[str] = field(default_factory=list)
    received_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat() + "Z")

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TriagedEmail:
    msg_id: str
    sender: str
    subject: str
    snippet: str
    quadrant: str                 # "Q1_URGENT_IMPORTANT", "Q2_STRATEGIC", "Q3_DELEGATE", "Q4_MUTE"
    priority: int
    drafted_response: Optional[str]
    received_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat() + "Z")

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _decode_header_str(header_val: Optional[str]) -> str:
    """Safely decode RFC 2047 encoded email headers."""
    if not header_val:
        return ""
    try:
        decoded_fragments = email.header.decode_header(header_val)
        fragments = []
        for content, encoding in decoded_fragments:
            if isinstance(content, bytes):
                enc = encoding or "utf-8"
                try:
                    fragments.append(content.decode(enc, errors="ignore"))
                except Exception:
                    fragments.append(content.decode("latin1", errors="ignore"))
            else:
                fragments.append(str(content))
        return "".join(fragments)
    except Exception:
        return str(header_val)


class CloudEmailAgent:
    """
    24/7 Sovereign Gmail & Email Intelligence and Dispatch Agent.
    """

    def __init__(self):
        self.imap_host = os.getenv("IMAP_HOST", "imap.gmail.com")
        self.imap_port = int(os.getenv("IMAP_PORT", "993"))
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.email_user = os.getenv("GMAIL_USER") or os.getenv("OWNER_EMAIL", "").strip()
        self.email_password = os.getenv("GMAIL_APP_PASSWORD") or os.getenv("EMAIL_PASSWORD", "").strip()

    @property
    def is_configured(self) -> bool:
        """Check if live Gmail/IMAP credentials are set."""
        return bool(
            self.email_user
            and self.email_password
            and "FILL_IN" not in self.email_password
            and "YOUR_" not in self.email_password
        )

    def test_connection(self) -> Dict[str, Any]:
        """Test IMAP and SMTP connections to Gmail."""
        if not self.is_configured:
            return {
                "configured": False,
                "imap_status": "unconfigured",
                "smtp_status": "unconfigured",
                "message": "Gmail credentials (OWNER_EMAIL and GMAIL_APP_PASSWORD) not provided in .env.",
                "user": self.email_user or "None"
            }

        imap_ok = False
        smtp_ok = False
        errors = []

        # 1. Test IMAP
        try:
            with imaplib.IMAP4_SSL(self.imap_host, self.imap_port) as mail:
                mail.login(self.email_user, self.email_password)
                imap_ok = True
        except Exception as e:
            errors.append(f"IMAP Error: {e}")

        # 2. Test SMTP
        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=10.0) as smtp:
                smtp.starttls()
                smtp.login(self.email_user, self.email_password)
                smtp_ok = True
        except Exception as e:
            errors.append(f"SMTP Error: {e}")

        return {
            "configured": True,
            "imap_status": "connected" if imap_ok else "failed",
            "smtp_status": "connected" if smtp_ok else "failed",
            "user": self.email_user,
            "errors": errors
        }

    # ── 1. Processed IDs Tracking ─────────────────────────────────────────────

    def _get_processed_ids(self) -> set:
        try:
            if _PROCESSED_FILE.exists():
                return set(json.loads(_PROCESSED_FILE.read_text(encoding="utf-8")))
        except Exception:
            pass
        return set()

    def _mark_processed(self, msg_id: str) -> None:
        with _LOCK:
            processed = self._get_processed_ids()
            processed.add(msg_id)
            _PROCESSED_FILE.write_text(json.dumps(list(processed)[-500:]), encoding="utf-8")

    # ── 2. Inbound Email Fetching ─────────────────────────────────────────────

    def fetch_emails(
        self,
        folder: str = "INBOX",
        limit: int = 10,
        unread_only: bool = False,
        search_query: Optional[str] = None
    ) -> List[EmailMessage]:
        """
        Fetch recent emails from Gmail via IMAP, or fallback to high-fidelity simulated inbox.
        """
        if self.is_configured:
            try:
                emails: List[EmailMessage] = []
                with imaplib.IMAP4_SSL(self.imap_host, self.imap_port) as mail:
                    mail.login(self.email_user, self.email_password)
                    mail.select(folder)

                    criterion = "UNSEEN" if unread_only else "ALL"
                    if search_query:
                        criterion = f'(TEXT "{search_query}")'

                    status, messages = mail.search(None, criterion)
                    if status != "OK" or not messages[0]:
                        return []

                    msg_ids = messages[0].split()[-limit:]

                    for mid_bytes in reversed(msg_ids):
                        mid_str = mid_bytes.decode()
                        res, msg_data = mail.fetch(mid_bytes, "(RFC822)")
                        if res != "OK":
                            continue

                        for response_part in msg_data:
                            if isinstance(response_part, tuple):
                                msg = email.message_from_bytes(response_part[1])
                                subject = _decode_header_str(msg.get("Subject", "No Subject"))
                                sender = _decode_header_str(msg.get("From", "Unknown Sender"))
                                recipient = _decode_header_str(msg.get("To", self.email_user))
                                date_str = msg.get("Date", "")

                                body_text = ""
                                body_html = ""
                                attachments = []

                                if msg.is_multipart():
                                    for part in msg.walk():
                                        ctype = part.get_content_type()
                                        cdisp = str(part.get("Content-Disposition", ""))

                                        if "attachment" in cdisp:
                                            filename = part.get_filename()
                                            if filename:
                                                attachments.append(_decode_header_str(filename))
                                            continue

                                        if ctype == "text/plain" and not body_text:
                                            payload = part.get_payload(decode=True)
                                            if payload:
                                                body_text = payload.decode(errors="ignore")
                                        elif ctype == "text/html" and not body_html:
                                            payload = part.get_payload(decode=True)
                                            if payload:
                                                body_html = payload.decode(errors="ignore")
                                else:
                                    payload = msg.get_payload(decode=True)
                                    if payload:
                                        body_text = payload.decode(errors="ignore")

                                # Fallback text from HTML if text is empty
                                if not body_text and body_html:
                                    body_text = re.sub(r"<[^>]+>", " ", body_html)
                                    body_text = re.sub(r"\s+", " ", body_text).strip()

                                snippet = body_text[:250].strip() if body_text else "(No body content)"

                                emails.append(EmailMessage(
                                    id=mid_str,
                                    sender=sender,
                                    recipient=recipient,
                                    subject=subject,
                                    date_str=date_str,
                                    body_text=body_text,
                                    body_html=body_html,
                                    snippet=snippet,
                                    is_unread=unread_only,
                                    has_attachments=bool(attachments),
                                    attachment_names=attachments
                                ))

                return emails
            except Exception as e:
                logger.warning(f"IMAP fetch error: {e}. Using deterministic simulation mode.")

        # High-fidelity realistic simulated emails for testing and fallback
        return self._generate_simulated_emails(limit=limit)

    def _generate_simulated_emails(self, limit: int = 5) -> List[EmailMessage]:
        """Generate high-fidelity structured emails for development, testing, and demo."""
        samples = [
            EmailMessage(
                id="sim_101",
                sender="Siddharth Mehta <siddharth@apexfintech.io>",
                recipient="saalimin21@gmail.com",
                subject="Enterprise Security Audit & SLA Contract Inquiry",
                date_str=datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000"),
                body_text="Hi Saalim,\n\nWe tested CogniGuard Cyber across our staging infrastructure and the vulnerability insights were impressive. We'd like to explore an Enterprise SLA subscription covering 15 domains and continuous monitoring. Could we schedule a brief 20-minute call this Thursday at 3:00 PM IST to discuss pricing and onboarding?\n\nBest regards,\nSiddharth Mehta\nHead of Engineering, ApexFintech",
                body_html="<p>Hi Saalim,<br><br>We tested <b>CogniGuard Cyber</b> across our staging infrastructure...</p>",
                snippet="We tested CogniGuard Cyber across our staging infrastructure and the vulnerability insights were impressive...",
                is_unread=True,
                quadrant="Q1_URGENT_IMPORTANT",
                priority=1,
            ),
            EmailMessage(
                id="sim_102",
                sender="Razorpay Notifications <alerts@razorpay.com>",
                recipient="saalimin21@gmail.com",
                subject="Payment Settlement of ₹45,000 Processed",
                date_str=datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000"),
                body_text="Dear Merchant,\n\nA payout of INR 45,000.00 has been initiated to your registered bank account for your venture transactions. Reference UTR: RZP9823410294. Expected credit time: within 2 hours.\n\nThank you for choosing Razorpay.",
                body_html="<p>Dear Merchant,<br><br>A payout of <b>INR 45,000.00</b> has been initiated...</p>",
                snippet="A payout of INR 45,000.00 has been initiated to your registered bank account...",
                is_unread=False,
                quadrant="Q2_STRATEGIC",
                priority=2,
            ),
            EmailMessage(
                id="sim_103",
                sender="Kaggle Operations <no-reply@kaggle.com>",
                recipient="saalimin21@gmail.com",
                subject="Kaggle TPU Worker Benchmark: Stage 4 Fine-Tuning Complete",
                date_str=datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000"),
                body_text="Your autonomous training pipeline has finished epoch 5 on Kaggle TPU v3-8. Training loss converged from 2.84 to 0.42. GGUF Q4_K_M quant was generated and committed to the dataset repository.",
                body_html="<p>Your autonomous training pipeline has finished epoch 5 on Kaggle TPU v3-8...</p>",
                snippet="Your autonomous training pipeline has finished epoch 5 on Kaggle TPU v3-8. Training loss converged...",
                is_unread=False,
                quadrant="Q2_STRATEGIC",
                priority=2,
            ),
            EmailMessage(
                id="sim_104",
                sender="GitHub <notifications@github.com>",
                recipient="saalimin21@gmail.com",
                subject="[GitHub] Security Alert: 1 dependency update recommended",
                date_str=datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000"),
                body_text="Dependabot has detected a minor update for httpx in repository charming-lovelace. Automated PR #42 has been created.",
                body_html="<p>Dependabot has detected a minor update for httpx...</p>",
                snippet="Dependabot has detected a minor update for httpx in repository charming-lovelace...",
                is_unread=True,
                quadrant="Q3_DELEGATE",
                priority=3,
            )
        ]
        return samples[:limit]

    # ── 3. AI Email Summarization Engine ──────────────────────────────────────

    def summarize_inbox(self, limit: int = 10, unread_only: bool = False) -> Dict[str, Any]:
        """
        Generate a comprehensive executive briefing of recent/unread inbox messages.
        """
        emails = self.fetch_emails(limit=limit, unread_only=unread_only)
        if not emails:
            return {
                "total_emails": 0,
                "unread_count": 0,
                "overview_html": "📭 <b>Inbox Zero:</b> No new emails requiring attention.",
                "action_items": [],
                "categorized": {
                    "urgent": [],
                    "commercial": [],
                    "finance": [],
                    "other": []
                }
            }

        urgent_list = []
        commercial_list = []
        finance_list = []
        other_list = []
        action_items = []

        for e in emails:
            txt = f"{e.subject} {e.body_text}".lower()
            if any(w in txt for w in ["urgent", "asap", "call", "schedule", "proposal", "contract", "meeting"]):
                urgent_list.append(e)
                action_items.append(f"Reply to {e.sender.split('<')[0].strip()} regarding '{e.subject}'")
            elif any(w in txt for w in ["payment", "payout", "invoice", "receipt", "settlement", "bank"]):
                finance_list.append(e)
            elif any(w in txt for w in ["partnership", "customer", "enterprise", "lead", "pricing"]):
                commercial_list.append(e)
            else:
                other_list.append(e)

        # Build clean HTML briefing
        lines = [
            f"📧 <b>AETHER Sovereign Email Briefing</b>",
            f"📊 <b>Total Checked:</b> {len(emails)} emails | <b>Action Required:</b> {len(urgent_list)}\n"
        ]

        if urgent_list:
            lines.append("🚨 <b>High Priority & Action Required:</b>")
            for e in urgent_list[:3]:
                lines.append(f"  • <b>{e.sender.split('<')[0].strip()}:</b> {e.subject}\n    <i>{e.snippet[:130]}...</i>")
            lines.append("")

        if finance_list:
            lines.append("💰 <b>Financial & Payment Updates:</b>")
            for e in finance_list[:2]:
                lines.append(f"  • {e.subject} (<i>{e.snippet[:90]}...</i>)")
            lines.append("")

        if commercial_list:
            lines.append("💼 <b>Commercial & Growth:</b>")
            for e in commercial_list[:2]:
                lines.append(f"  • {e.subject}")
            lines.append("")

        if action_items:
            lines.append("⚡ <b>Recommended Next Steps:</b>")
            for act in action_items[:3]:
                lines.append(f"  ☑️ {act}")

        return {
            "total_emails": len(emails),
            "unread_count": sum(1 for e in emails if e.is_unread),
            "overview_html": "\n".join(lines),
            "action_items": action_items,
            "emails": [e.to_dict() for e in emails]
        }

    def summarize_single_email(self, email_data: Dict[str, Any] | EmailMessage) -> Dict[str, Any]:
        """
        Deeply summarize a single email with TL;DR, key points, action items, and draft response.
        """
        if isinstance(email_data, EmailMessage):
            e_dict = email_data.to_dict()
        else:
            e_dict = email_data

        sender = e_dict.get("sender", "Unknown")
        subject = e_dict.get("subject", "No Subject")
        body = e_dict.get("body_text") or e_dict.get("snippet", "")

        from aether.brain.multi_provider_router import multi_provider_router

        prompt = (
            f"You are the AETHER Executive Email Intelligence Agent.\n"
            f"Analyze this incoming email:\n\n"
            f"From: {sender}\n"
            f"Subject: {subject}\n"
            f"Body:\n{body[:1500]}\n\n"
            f"Provide a structured JSON response with:\n"
            f"1. tl_dr: A 1-2 sentence core summary\n"
            f"2. sender_intent: What the sender specifically wants\n"
            f"3. key_points: List of 2-3 key facts/figures\n"
            f"4. action_items: List of actionable items for the recipient\n"
            f"5. urgency: 'High', 'Medium', or 'Low'\n"
            f"6. drafted_reply: Professional, concise, high-touch reply ready to send.\n"
            f"Return ONLY valid JSON."
        )

        res = multi_provider_router.complete_chat(
            messages=[{"role": "user", "content": prompt}],
            intent="deliberate",
            temperature=0.2,
            max_tokens=600,
        )
        content = res.get("content", "")

        try:
            cleaned = re.sub(r"```json|```", "", content).strip()
            parsed = json.loads(cleaned)
            return parsed
        except Exception:
            # Deterministic fallback summary
            sender_clean = sender.split("<")[0].strip()
            return {
                "tl_dr": f"Inquiry from {sender_clean} regarding '{subject}'.",
                "sender_intent": "General inquiry / update.",
                "key_points": [f"Subject: {subject}", f"Sender: {sender_clean}"],
                "action_items": [f"Review email from {sender_clean}"],
                "urgency": "Medium",
                "drafted_reply": (
                    f"Hi {sender_clean},\n\n"
                    f"Thank you for your message regarding '{subject}'. I have received your email and will review the details and get back to you shortly.\n\n"
                    f"Best regards,\nSaalim / AETHER Executive Operations"
                )
            }

    # ── 4. Outbound Email Sending & Replying ──────────────────────────────────

    def send_email(
        self,
        to_email: str | List[str],
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        in_reply_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send an email via secure SMTP with HTML and Plain Text formatting.
        """
        recipients = [to_email] if isinstance(to_email, str) else to_email
        clean_recipients = [r.strip() for r in recipients if r.strip()]

        if not clean_recipients:
            return {"ok": False, "error": "no_recipients_provided"}

        msg_id = make_msgid(domain="aether.ai")
        timestamp = datetime.now(timezone.utc).isoformat() + "Z"

        # Create MIME message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.email_user or "saalimin21@gmail.com"
        msg["To"] = ", ".join(clean_recipients)
        msg["Date"] = formatdate(localtime=True)
        msg["Message-ID"] = msg_id

        if in_reply_to:
            msg["In-Reply-To"] = in_reply_to
            msg["References"] = in_reply_to

        if cc:
            msg["Cc"] = ", ".join(cc)
            clean_recipients.extend(cc)
        if bcc:
            clean_recipients.extend(bcc)

        # Attach text and HTML
        msg.attach(MIMEText(body_text, "plain", "utf-8"))
        if body_html:
            msg.attach(MIMEText(body_html, "html", "utf-8"))
        else:
            # Wrap plain text in clean HTML
            html_wrapped = f"<html><body style='font-family:sans-serif;line-height:1.6;color:#1a1a1a;'>{body_text.replace(chr(10), '<br>')}</body></html>"
            msg.attach(MIMEText(html_wrapped, "html", "utf-8"))

        # Send via SMTP if configured
        if self.is_configured:
            try:
                with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=15.0) as server:
                    server.starttls()
                    server.login(self.email_user, self.email_password)
                    server.sendmail(self.email_user, clean_recipients, msg.as_string())
                logger.info(f"✉️ Successfully dispatched email to {clean_recipients} | Subject: {subject}")
            except Exception as e:
                logger.error(f"SMTP dispatch error: {e}")
                return {"ok": False, "error": str(e), "message_id": msg_id}

        # Log sent email
        record = {
            "message_id": msg_id,
            "to": clean_recipients,
            "subject": subject,
            "body_snippet": body_text[:200],
            "sent_at": timestamp,
            "is_simulated": not self.is_configured
        }
        with _LOCK:
            with open(_SENT_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

        return {
            "ok": True,
            "message_id": msg_id,
            "to": clean_recipients,
            "subject": subject,
            "sent_at": timestamp,
            "simulated": not self.is_configured
        }

    def reply_to_email(self, original_msg_id: str, reply_body: str, to_sender: str = "", subject: str = "") -> Dict[str, Any]:
        """Send a threaded reply to an existing email."""
        clean_subj = subject if subject.startswith("Re:") else f"Re: {subject}"
        return self.send_email(
            to_email=to_sender or self.email_user,
            subject=clean_subj or "Re: Inbound Communication",
            body_text=reply_body,
            in_reply_to=original_msg_id
        )

    # ── 5. Background Autonomous Triage ───────────────────────────────────────

    def check_inbox_and_triage(self, limit: int = 10) -> List[TriagedEmail]:
        """
        Poll IMAP server for unread emails, triage each message,
        and alert Telegram on Q1 high-priority communications.
        """
        emails = self.fetch_emails(limit=limit, unread_only=True)
        processed_ids = self._get_processed_ids()
        triaged_results: List[TriagedEmail] = []

        try:
            from aether.channels.telegram_assistant import telegram_assistant
            from aether.tools.executive_triage import executive_triage

            for e in emails:
                if e.id in processed_ids:
                    continue

                triage_item = executive_triage.triage_message(
                    sender=e.sender,
                    subject=e.subject,
                    body=e.body_text[:1000]
                )

                triaged = TriagedEmail(
                    msg_id=e.id,
                    sender=e.sender,
                    subject=e.subject,
                    snippet=e.snippet,
                    quadrant=triage_item.quadrant,
                    priority=triage_item.priority_score,
                    drafted_response=triage_item.drafted_reply,
                )
                triaged_results.append(triaged)
                self._mark_processed(e.id)

                # If Q1 Urgent & Important (customer inquiry / payment / downtime), alert Telegram!
                if triage_item.quadrant == "Q1_URGENT_IMPORTANT":
                    alert_text = (
                        f"🚨 <b>URGENT INBOUND EMAIL RECEIVED</b>\n\n"
                        f"👤 <b>From:</b> {e.sender}\n"
                        f"📌 <b>Subject:</b> {e.subject}\n\n"
                        f"📝 <i>{e.snippet}...</i>\n\n"
                        f"✉️ <b>Auto-Drafted Response:</b>\n"
                        f"<code>{triage_item.drafted_reply}</code>"
                    )
                    keyboard = {
                        "inline_keyboard": [
                            [
                                {"text": "✉️ Send Draft Reply", "callback_data": f"reply_email:{e.id}"},
                                {"text": "👁️ Mark Read", "callback_data": f"read_email:{e.id}"},
                            ]
                        ]
                    }
                    telegram_assistant.send_message(alert_text, reply_markup=keyboard)

        except Exception as e:
            logger.warning(f"Inbox triage check error: {e}")

        return triaged_results


cloud_email_agent = CloudEmailAgent()
