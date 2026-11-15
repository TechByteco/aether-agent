"""
AETHER Cloud Tasks, Alarms & Persistent Reminders Engine
=========================================================
Manages persistent 24/7 cloud alarms, reminders, and executive task schedules.
Fires exact-time alerts directly to the owner's Telegram / WhatsApp.

Natural parsing supported:
  • "/remind in 20m Call investor"
  • "/alarm at 07:00 AM Check server logs"
  • "/remind tomorrow at 10:00 AM Review LeadPulse B2B campaign"
"""

from __future__ import annotations

import json
import logging
import re
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("aether.tools.cloud_tasks_alarms")

_WORKSPACE = Path(__file__).resolve().parent.parent.parent.parent
_INTEL_DIR = _WORKSPACE / "data" / "leon_intelligence"
_TASKS_FILE = _INTEL_DIR / "cloud_tasks.json"

_INTEL_DIR.mkdir(parents=True, exist_ok=True)
_LOCK = threading.Lock()


@dataclass
class CloudReminder:
    id: str
    title: str
    target_time: str              # ISO 8601 UTC
    category: str                 # "alarm", "reminder", "business_followup", "habit"
    status: str                   # "scheduled", "fired", "completed", "snoozed"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat() + "Z")
    fired_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class CloudTasksAndAlarms:
    """
    Persistent alarm and task reminder scheduler for 24/7 cloud operations.
    """

    def _now_utc(self) -> datetime:
        return datetime.now(timezone.utc)

    def _read_tasks(self) -> List[Dict[str, Any]]:
        try:
            if _TASKS_FILE.exists():
                return json.loads(_TASKS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
        return []

    def _save_tasks(self, tasks: List[Dict[str, Any]]) -> None:
        with _LOCK:
            _TASKS_FILE.write_text(json.dumps(tasks, indent=2, ensure_ascii=False), encoding="utf-8")

    def create_reminder(
        self,
        title: str,
        target_time: datetime,
        category: str = "reminder"
    ) -> CloudReminder:
        """Schedule a new persistent reminder."""
        task_id = f"task_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{len(self._read_tasks())}"
        reminder = CloudReminder(
            id=task_id,
            title=title,
            target_time=target_time.isoformat() + "Z" if not target_time.tzinfo else target_time.isoformat(),
            category=category,
            status="scheduled",
        )
        tasks = self._read_tasks()
        tasks.append(reminder.to_dict())
        self._save_tasks(tasks)
        logger.info(f"⏰ Scheduled Cloud Reminder: '{title}' at {reminder.target_time}")
        return reminder

    def create_reminder_from_text(self, text: str) -> str:
        """
        Parse natural reminder text and schedule alarm.
        Examples:
          "/remind in 15m Check database"
          "/alarm in 2h Deploy release"
          "/remind at 08:30 Morning meditation"
        """
        clean = re.sub(r"^/(remind|alarm)\s*", "", text, flags=re.IGNORECASE).strip()

        now = self._now_utc()
        target = now + timedelta(minutes=30)  # default 30 min
        title = clean

        # Check for "in Xm" or "in Xh"
        match_delta = re.search(r"in\s+(\d+)\s*(m|min|mins|minutes|h|hr|hrs|hours|d|days)", clean, re.IGNORECASE)
        if match_delta:
            num = int(match_delta.group(1))
            unit = match_delta.group(2).lower()
            if unit.startswith("m"):
                target = now + timedelta(minutes=num)
            elif unit.startswith("h"):
                target = now + timedelta(hours=num)
            elif unit.startswith("d"):
                target = now + timedelta(days=num)
            # Remove the time part from title
            title = re.sub(r"in\s+\d+\s*(m|min|mins|minutes|h|hr|hrs|hours|d|days)", "", clean, flags=re.IGNORECASE).strip()

        # Check for "at HH:MM"
        match_at = re.search(r"at\s+(\d{1,2}):(\d{2})\s*(am|pm)?", clean, re.IGNORECASE)
        if match_at:
            hour = int(match_at.group(1))
            minute = int(match_at.group(2))
            ampm = match_at.group(3)
            if ampm:
                if ampm.lower() == "pm" and hour < 12:
                    hour += 12
                elif ampm.lower() == "am" and hour == 12:
                    hour = 0
            target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if target < now:
                target += timedelta(days=1)  # schedule for next day
            title = re.sub(r"at\s+\d{1,2}:\d{2}\s*(am|pm)?", "", clean, flags=re.IGNORECASE).strip()

        title = title.strip(" -:,") or "Personal Task Reminder"
        rem = self.create_reminder(title=title, target_time=target)

        return (
            f"⏰ <b>Alarm Scheduled Successfully!</b>\n\n"
            f"📌 <b>Task:</b> {rem.title}\n"
            f"⏳ <b>Target Time:</b> {target.strftime('%I:%M %p UTC')} ({target.strftime('%B %d')})\n\n"
            f"<i>You will receive a Telegram push notification when it triggers.</i>"
        )

    def check_pending_alarms(self) -> List[CloudReminder]:
        """
        Check all scheduled alarms, fire notifications for due alarms,
        and update their status. (Invoked every 60s by AutonomousOperator).
        """
        now = self._now_utc()
        tasks = self._read_tasks()
        fired_list: List[CloudReminder] = []
        updated = False

        for t in tasks:
            if t.get("status") == "scheduled":
                target_str = t.get("target_time", "")
                try:
                    # Clean target_str for parsing
                    clean_ts = target_str.replace("Z", "+00:00")
                    target_dt = datetime.fromisoformat(clean_ts)
                    if target_dt <= now:
                        t["status"] = "fired"
                        t["fired_at"] = now.isoformat() + "Z"
                        updated = True

                        reminder_obj = CloudReminder(
                            id=t.get("id"),
                            title=t.get("title"),
                            target_time=t.get("target_time"),
                            category=t.get("category", "alarm"),
                            status="fired",
                            fired_at=t["fired_at"],
                        )
                        fired_list.append(reminder_obj)

                        # Trigger Telegram alert
                        try:
                            from aether.channels.telegram_assistant import \
                                telegram_assistant
                            telegram_assistant.send_alarm_alert(
                                title=reminder_obj.title,
                                details=f"Scheduled for {target_str[:16]}"
                            )
                        except Exception as e:
                            logger.warning(f"Failed to push Telegram alarm: {e}")

                except Exception as e:
                    logger.debug(f"Alarm timestamp parse error for {t}: {e}")

        if updated:
            self._save_tasks(tasks)

        return fired_list

    def list_active_tasks(self) -> List[Dict[str, Any]]:
        """Return all scheduled reminders and pending tasks."""
        tasks = self._read_tasks()
        return [t for t in tasks if t.get("status") in ("scheduled", "snoozed")]


cloud_tasks = CloudTasksAndAlarms()
cloud_tasks_alarms = cloud_tasks
