"""
AETHER Windows System Guardian & Ambient Context Sensor (Evolution #5)
======================================================================
Proactive desktop observer for Windows ARM64 that monitors:
  1. Active foreground window title and focused application.
  2. Clipboard contents (code snippets, URLs, errors) for automatic contextual assistance.
  3. Battery status and thermal profile for dynamic throttle adjustment.

Runs using standard Python standard libraries and ctypes to avoid heavy external dependencies.
"""

from __future__ import annotations

import ctypes
import json
import logging
import os
import re
import threading
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("aether.daemon.windows_system_guardian")

_WORKSPACE = Path(__file__).resolve().parent.parent.parent.parent
_INTEL_DIR = _WORKSPACE / "data" / "leon_intelligence"
_GUARDIAN_LOG = _INTEL_DIR / "guardian_context.json"

_INTEL_DIR.mkdir(parents=True, exist_ok=True)
_LOCK = threading.Lock()


@dataclass
class AmbientSnapshot:
    active_window_title: str
    active_process_name: str
    clipboard_preview: str
    clipboard_type: str         # "code", "url", "error_trace", "plain_text", "empty"
    battery_percent: int
    is_ac_plugged: bool
    should_throttle_background: bool
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat() + "Z")

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class WindowsSystemGuardian:
    """
    Ambient desktop guardian sensing context and system health.
    """

    def __init__(self):
        self._last_clipboard: str = ""

    def get_active_window_title(self) -> str:
        """Get the title of the currently focused window on Windows."""
        try:
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buff = ctypes.create_unicode_buffer(length + 1)
                ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)
                return buff.value
        except Exception:
            pass
        return "Desktop / Workspace"

    def read_clipboard_text(self) -> str:
        """Safely retrieve text from the Windows clipboard using ctypes."""
        try:
            import tkinter as tk
            root = tk.Tk()
            root.withdraw()
            text = root.clipboard_get()
            root.destroy()
            return (text or "").strip()
        except Exception:
            pass
        return ""

    def classify_clipboard(self, text: str) -> str:
        """Classify the content type of text copied to clipboard."""
        if not text:
            return "empty"
        if text.startswith("http://") or text.startswith("https://"):
            return "url"
        if "Traceback (most recent call last)" in text or "Error:" in text or "Exception:" in text:
            return "error_trace"
        if re.search(r"(def |class |import |function |const |let |var |\{|\})", text):
            return "code"
        return "plain_text"

    def get_power_status(self) -> Tuple[int, bool]:
        """Inspect battery percentage and AC connection via psutil or system vitals."""
        try:
            import psutil
            battery = psutil.sensors_battery()
            if battery:
                return int(battery.percent), bool(battery.power_plugged)
        except Exception:
            pass
        return 100, True

    def capture_ambient_snapshot(self) -> AmbientSnapshot:
        """Generate a complete ambient observation snapshot."""
        win_title = self.get_active_window_title()
        clip_text = self.read_clipboard_text()
        clip_type = self.classify_clipboard(clip_text)
        bat_pct, is_plugged = self.get_power_status()

        # Throttle background evolution if battery is low (< 25%) and not plugged in
        should_throttle = (not is_plugged) and (bat_pct < 25)

        snapshot = AmbientSnapshot(
            active_window_title=win_title,
            active_process_name=win_title.split("-")[-1].strip() if "-" in win_title else "System",
            clipboard_preview=clip_text[:150] if clip_text else "",
            clipboard_type=clip_type,
            battery_percent=bat_pct,
            is_ac_plugged=is_plugged,
            should_throttle_background=should_throttle,
        )

        with _LOCK:
            _GUARDIAN_LOG.write_text(json.dumps(snapshot.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")

        return snapshot


windows_guardian = WindowsSystemGuardian()
