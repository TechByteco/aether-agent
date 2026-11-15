"""
AETHER 24/7 Cloud Keep-Alive Daemon
====================================
Pings the public AETHER Cloud Assistant instance every 14 minutes to ensure
zero-cost hosting tiers (Render / Koyeb / Hugging Face Spaces) never sleep.
"""

import logging
import os
import sys
import time
from datetime import datetime, timezone
import httpx

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("aether.keepalive")

DEFAULT_TARGET_URL = os.getenv("AETHER_CLOUD_URL", "http://localhost:8000")
PING_INTERVAL_SECONDS = int(os.getenv("PING_INTERVAL_SECONDS", "840"))  # 14 minutes


def ping_endpoint(base_url: str) -> bool:
    """Send heartbeat GET requests to health and status endpoints."""
    target_clean = base_url.rstrip("/")
    endpoints = [
        f"{target_clean}/api/owner/health",
        f"{target_clean}/api/owner/status",
    ]

    success = True
    with httpx.Client(timeout=20.0, follow_redirects=True) as client:
        for ep in endpoints:
            try:
                res = client.get(ep)
                if res.status_code == 200:
                    logger.info(f"🟢 Heartbeat OK -> {ep} (HTTP 200, {len(res.content)} bytes)")
                else:
                    logger.warning(f"🟡 Heartbeat returned HTTP {res.status_code} -> {ep}")
                    success = False
            except Exception as e:
                logger.error(f"🔴 Heartbeat failed for {ep}: {e}")
                success = False
    return success


def run_daemon():
    url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_TARGET_URL
    logger.info(f"🚀 Starting AETHER 24/7 Cloud Keep-Alive Daemon for target: {url}")
    logger.info(f"⏱️ Interval: every {PING_INTERVAL_SECONDS}s ({PING_INTERVAL_SECONDS/60:.1f} mins)")

    # Immediate initial ping
    ping_endpoint(url)

    while True:
        try:
            time.sleep(PING_INTERVAL_SECONDS)
            now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            logger.info(f"⏰ Keepalive tick at {now_str}")
            ping_endpoint(url)
        except KeyboardInterrupt:
            logger.info("Keepalive daemon terminated by user.")
            break
        except Exception as e:
            logger.error(f"Keepalive loop exception: {e}")
            time.sleep(30)


if __name__ == "__main__":
    run_daemon()
