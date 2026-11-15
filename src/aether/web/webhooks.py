"""
AETHER Razorpay Webhook Handler
================================
Receives and verifies Razorpay payment events.
On payment.captured: auto-sends a confirmation email to the buyer
and logs the payment to the owner inbox.

Mount in server.py:
    from aether.web.webhooks import router as webhooks_router
    app.include_router(webhooks_router)
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import smtplib
import ssl
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logger = logging.getLogger("aether.webhooks")

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])

_WORKSPACE   = Path(__file__).resolve().parent.parent.parent.parent
_PAYMENTS_F  = _WORKSPACE / "data" / "leon_intelligence" / "payments.json"
_PAYMENTS_F.parent.mkdir(parents=True, exist_ok=True)
_LOCK_PATH   = _PAYMENTS_F  # used as lock reference


def _load_payments() -> list:
    try:
        if _PAYMENTS_F.exists():
            return json.loads(_PAYMENTS_F.read_text(encoding="utf-8"))
    except Exception:
        pass
    return []


def _save_payments(payments: list) -> None:
    _PAYMENTS_F.write_text(json.dumps(payments[-1000:], indent=2), encoding="utf-8")


def _verify_signature(body: bytes, signature: str, secret: str) -> bool:
    """Verify Razorpay HMAC-SHA256 webhook signature."""
    try:
        expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)
    except Exception:
        return False


def _send_confirmation_email(recipient_email: str, venture_name: str,
                              amount_inr: float, payment_id: str, plan_name: str) -> bool:
    """Send a professional HTML confirmation email via Gmail SMTP."""
    sender = os.getenv("OWNER_EMAIL", "saalimin21@gmail.com")
    app_password = os.getenv("GMAIL_APP_PASSWORD", "")

    if not app_password or "FILL_IN" in app_password:
        logger.warning("GMAIL_APP_PASSWORD not configured — skipping confirmation email")
        return False

    subject = f"Your {venture_name} subscription is active! 🎉"
    html_body = f"""
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#0A0B0E;font-family:Inter,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#0A0B0E;padding:40px 0;">
    <tr><td align="center">
      <table width="560" cellpadding="0" cellspacing="0" style="background:#12141A;border-radius:16px;border:1px solid #1E2028;overflow:hidden;">
        <!-- Header -->
        <tr><td style="background:linear-gradient(135deg,#4F46E5,#6366F1);padding:32px;text-align:center;">
          <div style="font-size:28px;font-weight:800;color:#fff;letter-spacing:-0.5px;">{venture_name}</div>
          <div style="font-size:14px;color:#C7D2FE;margin-top:6px;">Payment Confirmed</div>
        </td></tr>
        <!-- Body -->
        <tr><td style="padding:32px;">
          <p style="color:#94A3B8;font-size:14px;margin:0 0 20px;">Hi there,</p>
          <p style="color:#F1F5F9;font-size:16px;margin:0 0 28px;">
            Your <strong style="color:#818CF8;">{plan_name}</strong> subscription to <strong>{venture_name}</strong> is now <strong style="color:#34D399;">active</strong>. Thank you for trusting us!
          </p>
          <!-- Amount card -->
          <table width="100%" style="background:#1E2028;border-radius:12px;margin-bottom:28px;">
            <tr>
              <td style="padding:20px;">
                <div style="color:#64748B;font-size:12px;font-family:monospace;text-transform:uppercase;letter-spacing:1px;margin-bottom:4px;">Amount Paid</div>
                <div style="color:#34D399;font-size:32px;font-weight:800;">₹{amount_inr:.0f}</div>
              </td>
              <td style="padding:20px;text-align:right;">
                <div style="color:#64748B;font-size:12px;font-family:monospace;text-transform:uppercase;letter-spacing:1px;margin-bottom:4px;">Payment ID</div>
                <div style="color:#94A3B8;font-size:13px;font-family:monospace;">{payment_id}</div>
              </td>
            </tr>
          </table>
          <!-- Next steps -->
          <div style="color:#94A3B8;font-size:14px;margin-bottom:8px;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;">Next Steps</div>
          <ul style="color:#CBD5E1;font-size:14px;padding-left:20px;margin:0 0 28px;line-height:1.8;">
            <li>Your account is being activated — you'll receive access details within 30 minutes.</li>
            <li>For any questions, reply directly to this email.</li>
            <li>Save your Payment ID for reference: <code style="color:#818CF8;">{payment_id}</code></li>
          </ul>
          <p style="color:#64748B;font-size:12px;margin:0;">
            Powered by {venture_name} · saalimin21@gmail.com
          </p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = sender
        msg["To"] = recipient_email
        msg.attach(MIMEText(html_body, "html"))

        context = ssl.create_default_context()
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.ehlo()
            server.starttls(context=context)
            server.login(sender, app_password)
            server.sendmail(sender, recipient_email, msg.as_string())
        logger.info(f"Confirmation email sent to {recipient_email} for {payment_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to send confirmation email: {e}")
        return False


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/health")
async def webhook_health() -> JSONResponse:
    """Verify the webhook endpoint is reachable."""
    return JSONResponse({"webhook_server": "online", "timestamp": datetime.now(timezone.utc).isoformat()})


@router.post("/razorpay")
async def razorpay_webhook(request: Request) -> JSONResponse:
    """
    Receive and process Razorpay payment webhooks.
    Verifies HMAC-SHA256 signature, auto-fulfills on payment.captured.
    """
    webhook_secret = os.getenv("RAZORPAY_WEBHOOK_SECRET", "")
    body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature", "")

    # Signature verification (skip if secret not yet configured)
    if webhook_secret and "FILL_IN" not in webhook_secret:
        if not _verify_signature(body, signature, webhook_secret):
            logger.warning(f"Invalid Razorpay webhook signature from {request.client.host}")
            raise HTTPException(status_code=400, detail="Invalid webhook signature")
    else:
        logger.warning("RAZORPAY_WEBHOOK_SECRET not configured — accepting webhook without verification")

    try:
        event: Dict[str, Any] = json.loads(body.decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    event_type = event.get("event", "")
    logger.info(f"Razorpay webhook received: {event_type}")

    if event_type == "payment.captured":
        payload = event.get("payload", {}).get("payment", {}).get("entity", {})
        payment_id  = payload.get("id", "")
        amount_inr  = payload.get("amount", 0) / 100
        email       = payload.get("email", "")
        description = payload.get("description", "LEON Venture Subscription")
        venture_name = description.split(" - ")[0] if " - " in description else description
        plan_name   = description.split(" - ")[1] if " - " in description else "Pro Plan"

        # Build payment record
        record: Dict[str, Any] = {
            "payment_id": payment_id,
            "amount_inr": amount_inr,
            "currency": payload.get("currency", "INR"),
            "email": email,
            "description": description,
            "venture_name": venture_name,
            "plan_name": plan_name,
            "status": "captured",
            "razorpay_method": payload.get("method", ""),
            "created_at": datetime.fromtimestamp(payload.get("created_at", 0), tz=timezone.utc).isoformat(),
            "received_at": datetime.now(timezone.utc).isoformat(),
        }

        # Persist payment
        payments = _load_payments()
        if not any(p.get("payment_id") == payment_id for p in payments):
            payments.append(record)
            _save_payments(payments)

        # ── Automated MicroSaaS Product Fulfillment ───────────────────────────
        fulfillment_res = {}
        if email:
            try:
                from aether.growth.fulfillment_engine import fulfillment_engine
                fulfillment_res = fulfillment_engine.fulfill_order(
                    venture_slug_or_name=venture_name,
                    customer_email=email,
                    payment_id=payment_id,
                    amount_inr=amount_inr,
                )
            except Exception as fe:
                logger.error(f"Fulfillment error for {payment_id}: {fe}")

        # Auto-send confirmation receipt email
        email_sent = fulfillment_res.get("email_sent", False)
        if not email_sent and email:
            email_sent = _send_confirmation_email(email, venture_name, amount_inr, payment_id, plan_name)

        # Add to owner inbox with fulfillment telemetry
        try:
            from aether.daemon.autonomous_operator import autonomous_operator
            autonomous_operator.add_to_inbox(
                "payment",
                f"💰 ₹{amount_inr:.0f} captured & fulfilled — {venture_name} ({email or 'no email'})",
                {**record, "fulfillment": fulfillment_res, "email_confirmation_sent": email_sent},
                requires_approval=False,
            )
        except Exception as e:
            logger.warning(f"Could not add payment to inbox: {e}")

        # Proactive push to Telegram & WhatsApp
        try:
            from aether.channels.telegram_assistant import telegram_assistant
            telegram_assistant.send_payment_alert(record)
        except Exception as e:
            logger.debug(f"Telegram payment alert note: {e}")

        try:
            from aether.channels.whatsapp_assistant import whatsapp_assistant
            whatsapp_assistant.send_alert(
                f"Payment Received ₹{amount_inr:.0f}",
                f"Venture: {venture_name}\nCustomer: {email}\nPayment ID: {payment_id}"
            )
        except Exception as e:
            logger.debug(f"WhatsApp payment alert note: {e}")

        logger.info(f"Payment captured & fulfilled: {payment_id} ₹{amount_inr:.0f} for {venture_name} ({email})")

        return JSONResponse({"status": "ok", "payment_id": payment_id,
                             "email_sent": email_sent, "amount_inr": amount_inr,
                             "fulfillment": fulfillment_res})

    # Acknowledge all other events
    return JSONResponse({"status": "ok", "event": event_type, "processed": False})


class SimulatePaymentRequest(BaseModel):
    venture_name: Optional[str] = "CogniGuard Cyber"
    amount_inr: Optional[float] = 45000.0
    email: Optional[str] = "siddharth@apexfintech.io"
    plan_name: Optional[str] = "Enterprise SLA"


@router.post("/simulate")
async def simulate_payment_webhook(req: SimulatePaymentRequest) -> JSONResponse:
    """Manually simulate a captured payment webhook for testing and UI automation."""
    pid = f"pay_sim_{int(datetime.now(timezone.utc).timestamp())}"
    sim_event = {
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": pid,
                    "amount": int(req.amount_inr * 100),
                    "currency": "INR",
                    "email": req.email,
                    "description": f"{req.venture_name} - {req.plan_name}",
                    "method": "upi",
                    "created_at": int(datetime.now(timezone.utc).timestamp()),
                }
            }
        }
    }
    # Persist and fulfill directly
    record = {
        "payment_id": pid,
        "amount_inr": req.amount_inr,
        "currency": "INR",
        "email": req.email,
        "description": f"{req.venture_name} - {req.plan_name}",
        "venture_name": req.venture_name,
        "plan_name": req.plan_name,
        "status": "captured",
        "razorpay_method": "upi",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "received_at": datetime.now(timezone.utc).isoformat(),
    }
    payments = _load_payments()
    payments.append(record)
    _save_payments(payments)

    try:
        from aether.daemon.autonomous_operator import autonomous_operator
        autonomous_operator.add_to_inbox(
            "payment",
            f"💰 Simulated payment ₹{req.amount_inr:.0f} captured — {req.venture_name}",
            record,
            requires_approval=False
        )
    except Exception:
        pass

    return JSONResponse({
        "status": "ok",
        "simulated": True,
        "payment_id": pid,
        "record": record
    })
