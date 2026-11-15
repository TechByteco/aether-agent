"""
AETHER Cross-Device Mobile Bridge (Telegram)
Enables secure, private interaction with your PC-based assistant from your phone.
Uses Telegram Long-Polling: Zero open ports or port-forwarding needed.
"""

import os
import sys
import time
from typing import Optional

import httpx

from aether.brain.engine import engine
from aether.config import config
from aether.tools.guardrails import format_vitals_summary, get_system_vitals


class TelegramBridge:
    def __init__(self, bot_token: Optional[str] = None, allowed_user_id: Optional[int] = None):
        self.bot_token = bot_token or os.environ.get("TELEGRAM_BOT_TOKEN", "")
        self.allowed_user_id = allowed_user_id or int(os.environ.get("TELEGRAM_ALLOWED_USER_ID", "0"))
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}"
        self.offset = 0

    def is_configured(self) -> bool:
        return bool(self.bot_token)

    def send_message(self, chat_id: int, text: str) -> None:
        """Send a markdown response back to the user's phone."""
        try:
            with httpx.Client(timeout=15.0) as client:
                client.post(
                    f"{self.api_url}/sendMessage",
                    json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
                )
        except Exception as e:
            print(f"[TelegramBridge] Error sending message: {e}", file=sys.stderr)

    def poll_once(self) -> None:
        """Poll for new messages from your phone and process through AETHER."""
        if not self.is_configured():
            return

        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.get(
                    f"{self.api_url}/getUpdates",
                    params={"offset": self.offset, "timeout": 20},
                )
                data = resp.json()
                if not data.get("ok"):
                    return

                for update in data.get("result", []):
                    self.offset = update["update_id"] + 1
                    message = update.get("message")
                    if not message or "text" not in message:
                        continue

                    user_id = message.get("from", {}).get("id")
                    chat_id = message["chat"]["id"]
                    text = message["text"].strip()

                    # Security guard: restrict only to the device owner if set
                    if self.allowed_user_id and user_id != self.allowed_user_id:
                        self.send_message(chat_id, "⛔ Unauthorized device.")
                        continue

                    if text == "/status":
                        self.send_message(chat_id, f"💻 *PC Status*:\n{format_vitals_summary()}")
                        continue

                    # Process query with local brain
                    reply = engine.process_query(text, session_id="mobile")
                    self.send_message(chat_id, reply)

        except Exception as e:
            print(f"[TelegramBridge] Polling exception: {e}", file=sys.stderr)

    def run_polling_loop(self) -> None:
        """Run long-polling daemon."""
        if not self.is_configured():
            print("To enable phone access, set TELEGRAM_BOT_TOKEN in your environment.")
            return

        print("AETHER Mobile Bridge active. Listening for phone messages...")
        while True:
            self.poll_once()
            time.sleep(1)


bridge = TelegramBridge()
