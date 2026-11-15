"""
AETHER Cloud Calendar Agent & Pre-Meeting Executive Briefing System
===================================================================
Connects to Google Calendar / Apple iCloud / Outlook via ICS feed URLs or direct schedule entries.
Monitors daily agendas 24/7 and proactively pushes 10-minute pre-meeting intelligence briefings
to Telegram / WhatsApp with one-tap meeting join links.
"""

from __future__ import annotations

import json
import logging
import os
import re
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger("aether.tools.cloud_calendar")

_WORKSPACE = Path(__file__).resolve().parent.parent.parent.parent
_INTEL_DIR = _WORKSPACE / "data" / "leon_intelligence"
_EVENTS_FILE = _INTEL_DIR / "calendar_events.json"
_ALERTED_FILE = _INTEL_DIR / "alerted_meeting_ids.json"

_INTEL_DIR.mkdir(parents=True, exist_ok=True)
_LOCK = threading.Lock()


@dataclass
class CalendarEvent:
    id: str
    title: str
    start_time: str               # ISO 8601 UTC
    end_time: str                 # ISO 8601 UTC
    description: str = ""
    location: str = ""
    meeting_url: Optional[str] = None
    organizer: str = ""
    status: str = "confirmed"     # "confirmed", "cancelled", "completed"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat() + "Z")

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class CloudCalendarAgent:
    """
    24/7 Cloud Calendar Monitoring & Pre-Meeting Briefing Agent.
    """

    def __init__(self):
        self.ics_feed_url = os.getenv("CALENDAR_ICS_URL", "").strip()

    def _now_utc(self) -> datetime:
        return datetime.now(timezone.utc)

    def _read_events(self) -> List[Dict[str, Any]]:
        try:
            if _EVENTS_FILE.exists():
                return json.loads(_EVENTS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
        return []

    def _save_events(self, events: List[Dict[str, Any]]) -> None:
        with _LOCK:
            _EVENTS_FILE.write_text(json.dumps(events[-500:], indent=2, ensure_ascii=False), encoding="utf-8")

    def _get_alerted_ids(self) -> set:
        try:
            if _ALERTED_FILE.exists():
                return set(json.loads(_ALERTED_FILE.read_text(encoding="utf-8")))
        except Exception:
            pass
        return set()

    def _mark_alerted(self, event_id: str) -> None:
        with _LOCK:
            alerted = self._get_alerted_ids()
            alerted.add(event_id)
            _ALERTED_FILE.write_text(json.dumps(list(alerted)[-500:]), encoding="utf-8")

    def add_event(
        self,
        title: str,
        start_time: datetime,
        duration_minutes: int = 30,
        description: str = "",
        meeting_url: Optional[str] = None,
        location: str = ""
    ) -> CalendarEvent:
        """Manually or programmatically register a calendar meeting."""
        end_time = start_time + timedelta(minutes=duration_minutes)
        event_id = f"evt_{start_time.strftime('%Y%m%d%H%M')}_{len(self._read_events())}"

        # Detect meeting URL in description if not explicitly provided
        if not meeting_url:
            meet_match = re.search(r"https?://(meet\.google\.com|zoom\.us|teams\.microsoft\.com)/[^\s]+", description)
            if meet_match:
                meeting_url = meet_match.group(0)

        evt = CalendarEvent(
            id=event_id,
            title=title,
            start_time=start_time.isoformat() + ("Z" if not start_time.tzinfo else ""),
            end_time=end_time.isoformat() + ("Z" if not end_time.tzinfo else ""),
            description=description,
            location=location,
            meeting_url=meeting_url,
        )

        events = self._read_events()
        events.append(evt.to_dict())
        self._save_events(events)
        logger.info(f"📅 Added calendar event: '{title}' at {evt.start_time}")
        return evt

    def sync_ics_feed(self) -> int:
        """
        Fetch and parse external iCalendar (.ics) feed URL (e.g. Google Calendar secret link).
        """
        if not self.ics_feed_url or "http" not in self.ics_feed_url:
            return 0

        try:
            with httpx.Client(timeout=15.0) as client:
                res = client.get(self.ics_feed_url)
                if res.status_code != 200:
                    logger.warning(f"Failed to fetch ICS feed: HTTP {res.status_code}")
                    return 0

                raw_ics = res.text
                return self._parse_and_merge_ics(raw_ics)
        except Exception as e:
            logger.warning(f"ICS sync error: {e}")
            return 0

    def _parse_and_merge_ics(self, ics_content: str) -> int:
        """Lightweight pure-python ICS parser with no external C dependencies."""
        events_found = 0
        raw_blocks = ics_content.split("BEGIN:VEVENT")
        existing_events = self._read_events()
        existing_ids = {e.get("id") for e in existing_events}

        for block in raw_blocks[1:]:
            summary_m = re.search(r"SUMMARY:(.*?)(?:\r?\n[A-Z]|\r?\nEND:)", block, re.DOTALL)
            dtstart_m = re.search(r"DTSTART(?:;[^:]+)?:(\d{8}T\d{6}Z?)", block)
            dtend_m = re.search(r"DTEND(?:;[^:]+)?:(\d{8}T\d{6}Z?)", block)
            uid_m = re.search(r"UID:(.*?)(?:\r?\n)", block)
            desc_m = re.search(r"DESCRIPTION:(.*?)(?:\r?\n[A-Z]|\r?\nEND:)", block, re.DOTALL)
            url_m = re.search(r"https?://(meet\.google\.com|zoom\.us|teams\.microsoft\.com)/[^\s]+", block)

            title = summary_m.group(1).strip().replace("\\,", ",") if summary_m else "Scheduled Meeting"
            uid = uid_m.group(1).strip() if uid_m else f"ics_{events_found}"
            desc = desc_m.group(1).strip().replace("\\n", "\n") if desc_m else ""
            meet_url = url_m.group(0) if url_m else None

            if dtstart_m:
                dt_str = dtstart_m.group(1)
                try:
                    # Parse YYYYMMDDTHHMMSS
                    st = datetime.strptime(dt_str.replace("Z", ""), "%Y%m%dT%H%M%S").replace(tzinfo=timezone.utc)
                    end_st = st + timedelta(minutes=30)
                    if dtend_m:
                        end_str = dtend_m.group(1)
                        end_st = datetime.strptime(end_str.replace("Z", ""), "%Y%m%dT%H%M%S").replace(tzinfo=timezone.utc)

                    if uid not in existing_ids:
                        new_evt = CalendarEvent(
                            id=uid,
                            title=title,
                            start_time=st.isoformat() + "Z",
                            end_time=end_st.isoformat() + "Z",
                            description=desc[:500],
                            meeting_url=meet_url,
                        )
                        existing_events.append(new_evt.to_dict())
                        events_found += 1
                except Exception as e:
                    logger.debug(f"ICS date parse error: {e}")

        if events_found > 0:
            self._save_events(existing_events)
            logger.info(f"✅ Synced {events_found} new events from ICS calendar feed.")

        return events_found

    def check_upcoming_meetings_and_alert(self) -> List[CalendarEvent]:
        """
        Check for meetings starting in the next 10 minutes.
        Pushes proactive Telegram briefing with join link.
        """
        now = self._now_utc()
        ten_mins_later = now + timedelta(minutes=10)
        events = self._read_events()
        alerted_ids = self._get_alerted_ids()
        upcoming: List[CalendarEvent] = []

        for e in events:
            eid = e.get("id", "")
            if eid in alerted_ids:
                continue

            start_str = e.get("start_time", "")
            try:
                clean_ts = start_str.replace("Z", "+00:00")
                start_dt = datetime.fromisoformat(clean_ts)

                # If meeting is between now and next 10 minutes (or within last 2 minutes)
                if now - timedelta(minutes=2) <= start_dt <= ten_mins_later:
                    evt_obj = CalendarEvent(
                        id=eid,
                        title=e.get("title", "Meeting"),
                        start_time=start_str,
                        end_time=e.get("end_time", ""),
                        description=e.get("description", ""),
                        meeting_url=e.get("meeting_url"),
                        location=e.get("location", ""),
                    )
                    upcoming.append(evt_obj)
                    self._mark_alerted(eid)

                    # Trigger proactive Telegram push
                    try:
                        from aether.channels.telegram_assistant import \
                            telegram_assistant
                        mins_left = max(1, int((start_dt - now).total_seconds() / 60))
                        briefing_text = (
                            f"🗓️ <b>UPCOMING MEETING IN {mins_left} MINS</b>\n\n"
                            f"📌 <b>{evt_obj.title}</b>\n"
                            f"⏰ <b>Start Time:</b> {start_dt.strftime('%I:%M %p UTC')}\n"
                        )
                        if evt_obj.description:
                            briefing_text += f"📝 <b>Agenda:</b> {evt_obj.description[:200]}\n"

                        keyboard = None
                        if evt_obj.meeting_url:
                            keyboard = {
                                "inline_keyboard": [
                                    [{"text": "📹 Join Video Call", "url": evt_obj.meeting_url}],
                                ]
                            }

                        telegram_assistant.send_message(briefing_text, reply_markup=keyboard)
                    except Exception as ex:
                        logger.warning(f"Telegram meeting push error: {ex}")

            except Exception as ex:
                logger.debug(f"Calendar check parse error for {e}: {ex}")

        return upcoming

    def get_daily_agenda(self, target_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Get all meetings scheduled for a given date (defaults to today)."""
        date_target = (target_date or self._now_utc()).strftime("%Y-%m-%d")
        events = self._read_events()
        return [e for e in events if e.get("start_time", "").startswith(date_target)]


cloud_calendar_agent = CloudCalendarAgent()
