"""
AETHER WhatsApp Assistant & Cloud Webhook Gateway
==================================================
Provides WhatsApp connectivity via Meta Cloud API / Twilio webhooks.
Enables proactive mobile alerts, status inquiries, and interactive command execution.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, Optional

import httpx
from fastapi import APIRouter, Header, Query, Request, Response
from fastapi.responses import JSONResponse, PlainTextResponse

logger = logging.getLogger("aether.channels.whatsapp")

router = APIRouter(prefix="/api/channels/whatsapp", tags=["whatsapp"])

WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "aether-sovereign-verify-token")
WHATSAPP_API_TOKEN = os.getenv("WHATSAPP_API_TOKEN", "")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")


@router.get("/webhook")
async def verify_whatsapp_webhook(
    hub_mode: Optional[str] = Query(None, alias="hub.mode"),
    hub_challenge: Optional[str] = Query(None, alias="hub.challenge"),
    hub_verify_token: Optional[str] = Query(None, alias="hub.verify_token"),
) -> Response:
    """Meta WhatsApp Cloud API Webhook verification handshake."""
    if hub_mode == "subscribe" and hub_verify_token == WHATSAPP_VERIFY_TOKEN:
        logger.info("WhatsApp webhook verified successfully!")
        return PlainTextResponse(content=hub_challenge or "")
    return PlainTextResponse(content="Forbidden", status_code=403)


class WhatsAppAssistant:
    """WhatsApp Assistant client for outbound proactive notifications and inbound message processing."""

    def __init__(self):
        self.api_token = os.getenv("WHATSAPP_API_TOKEN", "")
        self.phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
        self.owner_phone = os.getenv("WHATSAPP_OWNER_PHONE", "")

    def is_configured(self) -> bool:
        return bool(self.api_token and self.phone_number_id)

    def send_message(self, text: str, recipient: Optional[str] = None) -> bool:
        """Send a proactive WhatsApp text message to the owner or designated recipient."""
        target = recipient or self.owner_phone
        if not target or not self.is_configured():
            logger.debug("WhatsApp not configured or recipient missing; skipping message.")
            return False

        try:
            send_url = f"https://graph.facebook.com/v19.0/{self.phone_number_id}/messages"
            headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json",
            }
            # Clean HTML to WhatsApp Markdown
            clean_text = (
                text.replace("<b>", "*")
                .replace("</b>", "*")
                .replace("<i>", "_")
                .replace("</i>", "_")
                .replace("<code>", "```")
                .replace("</code>", "```")
            )
            payload = {
                "messaging_product": "whatsapp",
                "to": target,
                "type": "text",
                "text": {"body": clean_text[:4000]},
            }
            with httpx.Client(timeout=10.0) as client:
                res = client.post(send_url, headers=headers, json=payload)
                return res.status_code == 200
        except Exception as e:
            logger.error(f"Failed to send WhatsApp message: {e}")
            return False

    def send_alert(self, title: str, details: str) -> bool:
        """Send a formatted priority alert via WhatsApp."""
        msg = f"🚨 *AETHER ALERT: {title}*\n\n{details}\n\n_Sent via AETHER Cloud Sovereign Assistant_"
        return self.send_message(msg)


whatsapp_assistant = WhatsAppAssistant()


@router.post("/webhook")
async def receive_whatsapp_message(request: Request) -> JSONResponse:
    """Handle incoming messages from WhatsApp."""
    try:
        data = await request.json()
        entry = data.get("entry", [])
        if not entry:
            return JSONResponse({"status": "ignored"})

        changes = entry[0].get("changes", [])
        if not changes:
            return JSONResponse({"status": "ignored"})

        value = changes[0].get("value", {})
        messages = value.get("messages", [])
        if not messages:
            return JSONResponse({"status": "no_messages"})

        msg = messages[0]
        from_number = msg.get("from")
        text_body = msg.get("text", {}).get("body", "").strip()

        logger.info(f"Received WhatsApp message from {from_number}: {text_body[:50]}")

        # Process message via TelegramAssistant / Engine
        from aether.channels.telegram_assistant import telegram_assistant
        reply = telegram_assistant.handle_incoming_text(text_body, from_number)

        # Send reply back via WhatsApp
        whatsapp_assistant.send_message(reply, recipient=from_number)

        return JSONResponse({"status": "success", "reply": reply})

    except Exception as e:
        logger.error(f"WhatsApp webhook processing error: {e}")
        return JSONResponse({"status": "error", "detail": str(e)}, status_code=500)

