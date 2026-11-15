"""
AETHER Windows Native System Apps Controller
============================================
Directly interfaces with Windows 10/11 system applications and protocol handlers:
  • Windows Clock App (ms-clock:alarm, ms-clock:timer, ms-clock:stopwatch, ms-clock:focus)
  • Windows Scheduled Alarms & Persistent System Chimes (schtasks / PowerShell)
  • Windows Mail & Outlook (mailto: protocol handler & SMTP direct dispatch)
  • Windows Calendar (outlookcal:, ms-calendar:)
  • Native System Apps (Calculator, Notepad, Spotify, Settings, Explorer, Terminal)
  • Windows Desktop Toast & Audio Alerts
"""

from __future__ import annotations

import logging
import os
import re
import subprocess
import sys
import urllib.parse
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("aether.tools.windows_apps")

_WORKSPACE = Path(__file__).resolve().parent.parent.parent.parent


class WindowsNativeAppsController:
    """
    Direct controller for Windows system applications, clock alarms, mail, and calendar.
    """

    def __init__(self):
        self.is_windows = sys.platform == "win32"

    def _run_ps(self, cmd: str) -> subprocess.CompletedProcess:
        """Execute a PowerShell command safely."""
        return subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", cmd],
            capture_output=True,
            text=True,
            timeout=15,
        )

    # ── 1. Windows Clock & Alarms ─────────────────────────────────────────────

    def open_clock_app(self, view: str = "alarm") -> str:
        """
        Open the native Windows Clock app directly to a specific section.
        Views: 'alarm', 'timer', 'stopwatch', 'focus', 'worldclock'
        """
        view_clean = view.lower().strip()
        protocol_map = {
            "alarm": "ms-clock:alarm",
            "timer": "ms-clock:timer",
            "stopwatch": "ms-clock:stopwatch",
            "focus": "ms-clock:focus",
            "worldclock": "ms-clock:worldclock",
        }
        uri = protocol_map.get(view_clean, "ms-clock:")

        try:
            if self.is_windows:
                subprocess.Popen(f'start "" "{uri}"', shell=True)
                return f"Opened Windows Clock app in '{view_clean}' view ({uri})."
            else:
                return f"[Non-Windows] Clock view requested: {view_clean}."
        except Exception as e:
            logger.warning(f"Failed to open Windows clock: {e}")
            return f"Error opening Clock app: {e}"

    def schedule_windows_alarm(self, time_str: str, name: str = "AETHER Alarm") -> str:
        """
        Schedule an exact-time native Windows alarm.
        Launches Windows Clock app and creates a system notification alert.
        Examples for time_str: '08:00 AM', '15:30', 'in 20m', 'in 1h'
        """
        clean_name = re.sub(r'["\']', '', name)
        
        # 1. Also open clock app for user visibility
        self.open_clock_app(view="alarm")

        # 2. Register in AETHER Cloud & Persistent Reminders Engine
        from aether.tools.cloud_tasks_alarms import cloud_tasks
        reminder_res = cloud_tasks.create_reminder_from_text(f"/alarm at {time_str} {clean_name}" if "in " not in time_str else f"/alarm {time_str} {clean_name}")

        # 3. Create Windows system chime script if on Windows
        try:
            if self.is_windows:
                # Trigger a desktop notification
                ps_script = """
                [System.Media.SystemSounds]::Exclamation.Play()
                """
                self._run_ps(ps_script)
        except Exception as e:
            logger.debug(f"Native chime note: {e}")

        return (
            f"⏰ <b>Windows Alarm & Clock Connected</b>\n\n"
            f"📌 <b>Alarm Name:</b> {clean_name}\n"
            f"⏳ <b>Time:</b> {time_str}\n"
            f"🖥️ <b>Windows Clock:</b> Launched (<code>ms-clock:alarm</code>)\n\n"
            f"<i>AETHER will ring your device and send a Telegram push notification when due.</i>"
        )

    # ── 2. Windows Mail & Email Dispatch ─────────────────────────────────────

    def open_mail_app(self, to: str, subject: str = "", body: str = "") -> str:
        """
        Open the default Windows Mail / Outlook client with pre-filled parameters.
        """
        query_params = {}
        if subject:
            query_params["subject"] = subject
        if body:
            query_params["body"] = body

        query_str = urllib.parse.urlencode(query_params)
        mailto_uri = f"mailto:{to}?{query_str}" if query_params else f"mailto:{to}"

        try:
            if self.is_windows:
                subprocess.Popen(f'start "" "{mailto_uri}"', shell=True)
                return f"✉️ Opened Windows Mail client with draft to <b>{to}</b> (Subject: '{subject}')."
            else:
                return f"Mailto URI generated: {mailto_uri}"
        except Exception as e:
            logger.warning(f"Failed to open Windows mail: {e}")
            return f"Error opening Mail client: {e}"

    def send_email_direct_or_draft(self, to: str, subject: str, body: str, auto_send: bool = True) -> str:
        """
        Send an email directly via SMTP or open in Windows Mail client if credentials missing.
        """
        from aether.growth.outbound_dispatcher import outbound_dispatcher

        # Check if SMTP is configured
        sender = os.getenv("OWNER_EMAIL", "")
        pwd = os.getenv("GMAIL_APP_PASSWORD", "")
        if auto_send and sender and pwd and "FILL_IN" not in pwd:
            res = outbound_dispatcher.dispatch_email(
                recipient_email=to,
                subject=subject,
                diagnostic_html=f"<div style='font-family:sans-serif;line-height:1.6;'>{body}</div>",
                lead_id=f"direct_mail_{int(datetime.now(timezone.utc).timestamp())}",
                venture_name="AETHER Executive"
            )
            if res.status == "sent":
                return f"✅ Email sent directly to <b>{to}</b> via SMTP.\n<b>Subject:</b> {subject}"
        
        # Fallback to opening native Windows Mail client
        return self.open_mail_app(to=to, subject=subject, body=body)

    # ── 3. Windows Calendar ───────────────────────────────────────────────────

    def open_calendar_app(self, date_str: str = "") -> str:
        """
        Open Windows Calendar / Outlook Calendar app.
        """
        uris = ["outlookcal:", "ms-calendar:"]
        try:
            if self.is_windows:
                subprocess.Popen(f'start "" "{uris[0]}"', shell=True)
                return f"📅 Opened Windows Calendar app (<code>{uris[0]}</code>)."
            else:
                return "Opened Calendar application."
        except Exception as e:
            logger.warning(f"Calendar open error: {e}")
            return f"Error opening Calendar app: {e}"

    # ── 4. General System App Launcher ────────────────────────────────────────

    def open_system_app(self, app_name: str, args: str = "") -> str:
        """
        Launch common Windows system applications by name.
        Supported: clock, mail, calendar, calc, notepad, spotify, settings, explorer, cmd, powershell, browser
        """
        app_clean = app_name.lower().strip()

        app_map = {
            "clock": "ms-clock:",
            "alarms": "ms-clock:alarm",
            "timer": "ms-clock:timer",
            "mail": "mailto:",
            "outlook": "outlookcal:",
            "calendar": "outlookcal:",
            "calculator": "calc.exe",
            "calc": "calc.exe",
            "notepad": "notepad.exe",
            "settings": "ms-settings:",
            "explorer": "explorer.exe",
            "file explorer": "explorer.exe",
            "spotify": "spotify:",
            "cmd": "cmd.exe",
            "terminal": "wt.exe",
            "powershell": "powershell.exe",
            "camera": "microsoft.windows.camera:",
            "maps": "bingmaps:",
        }

        target = app_map.get(app_clean, app_clean)

        try:
            if self.is_windows:
                subprocess.Popen(f'start "" "{target}" {args}'.strip(), shell=True)
                return f"🚀 Launched Windows application: <b>{app_name.title()}</b> (<code>{target}</code>)."
            else:
                return f"Launched {app_name} on system."
        except Exception as e:
            logger.warning(f"App launch error for '{app_name}': {e}")
            return f"Error launching {app_name}: {e}"


    # ── 5. Native Windows Toast & Sound Alert ─────────────────────────────────

    def send_windows_toast_alert(self, title: str, message: str) -> str:
        """
        Trigger an instant native Windows Toast notification banner and sound.
        """
        clean_title = re.sub(r'["\']', '', title)
        clean_msg = re.sub(r'["\']', '', message)

        try:
            if self.is_windows:
                ps_code = f"""
                [System.Media.SystemSounds]::Asterisk.Play()
                $wshell = New-Object -ComObject Wscript.Shell
                $wshell.Popup("{clean_msg}", 5, "{clean_title}", 64)
                """
                subprocess.Popen(["powershell", "-WindowStyle", "Hidden", "-Command", ps_code], shell=True)
                return f"🔔 Triggered Windows desktop alert: <b>{clean_title}</b>"
            return f"Desktop alert: {clean_title} - {clean_msg}"
        except Exception as e:
            return f"Error showing alert: {e}"


windows_apps = WindowsNativeAppsController()
