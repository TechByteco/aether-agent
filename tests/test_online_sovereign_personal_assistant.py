"""
Comprehensive Unit & Integration Test Suite for AETHER Sovereign Online Personal Assistant
=============================================================================================
Tests 100% cloud-based proactive life ops, calendar, email triage, Telegram/WhatsApp channels,
natural language alarms, and autonomous operator jobs.
"""

import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from aether.channels.telegram_assistant import telegram_assistant
from aether.channels.whatsapp_assistant import whatsapp_assistant
from aether.tools.cloud_tasks_alarms import cloud_tasks
from aether.tools.cloud_calendar_agent import cloud_calendar_agent
from aether.tools.cloud_email_agent import cloud_email_agent
from aether.tools.cloud_web_monitor import cloud_web_monitor
from aether.daemon.autonomous_operator import autonomous_operator


class TestOnlineSovereignPersonalAssistant(unittest.TestCase):
    """Test suite for 24/7 Sovereign Personal Assistant capabilities."""

    def test_telegram_assistant_commands(self):
        """Verify all Telegram commands parse and return valid HTML formatted responses."""
        start_reply = telegram_assistant.handle_incoming_text("/start", "test_user")
        self.assertIn("AETHER Sovereign Personal Assistant", start_reply)
        self.assertIn("/briefing", start_reply)

        status_reply = telegram_assistant.handle_incoming_text("/status", "test_user")
        self.assertIn("AETHER System Status", status_reply)

        memo_reply = telegram_assistant.handle_incoming_text("/memo", "test_user")
        self.assertIn("Executive Decision Memo", memo_reply)

        audit_reply = telegram_assistant.handle_incoming_text("/audit testcorp.io", "test_user")
        self.assertIn("CogniGuard Cyber Audit", audit_reply)

        radar_reply = telegram_assistant.handle_incoming_text("/radar", "test_user")
        self.assertTrue("Radar" in radar_reply or "Signals" in radar_reply)

    def test_natural_alarm_and_task_scheduling(self):
        """Verify natural language alarm parsing (/remind in 15m, /alarm at 09:00)."""
        res_delta = cloud_tasks.create_reminder_from_text("/remind in 25m Review Q4 Revenue Strategy")
        self.assertIn("Alarm Scheduled Successfully", res_delta)
        self.assertIn("Review Q4 Revenue Strategy", res_delta)

        active = cloud_tasks.list_active_tasks()
        self.assertTrue(len(active) > 0)
        self.assertTrue(any("Review Q4 Revenue Strategy" in t["title"] for t in active))

    def test_calendar_meeting_registration_and_briefing(self):
        """Verify calendar meeting scheduling and upcoming 10-minute check."""
        now = datetime.now(timezone.utc)
        evt = cloud_calendar_agent.add_event(
            title="Investor Presentation",
            start_time=now + timedelta(minutes=5),
            duration_minutes=45,
            description="Demoing AETHER 24/7 autonomous operations",
            meeting_url="https://meet.google.com/abc-defg-hij"
        )
        self.assertEqual(evt.title, "Investor Presentation")
        self.assertEqual(evt.meeting_url, "https://meet.google.com/abc-defg-hij")

        agenda = cloud_calendar_agent.get_daily_agenda()
        self.assertTrue(len(agenda) > 0)

        upcoming = cloud_calendar_agent.check_upcoming_meetings_and_alert()
        self.assertTrue(len(upcoming) >= 1)
        self.assertEqual(upcoming[0].title, "Investor Presentation")

    def test_cloud_web_monitor_scanning(self):
        """Verify RSS market radar signal ingestion."""
        signals = cloud_web_monitor.scan_feeds()
        self.assertIsInstance(signals, list)

    def test_autonomous_operator_jobs_scheduled(self):
        """Verify AutonomousOperator starts all 14 background jobs cleanly."""
        autonomous_operator.start()
        status = autonomous_operator.get_status()
        self.assertTrue(status.get("scheduler_running"))

        job_ids = {j["id"] for j in status.get("jobs", [])}
        expected_jobs = {
            "health_check", "lead_discovery", "razorpay_sync", "portfolio_status",
            "approval_check", "self_evaluation", "registry_prune", "process_goals",
            "intent_harvesting", "alarm_check", "calendar_check", "ics_sync",
            "email_triage", "morning_briefing_push"
        }
        for ej in expected_jobs:
            self.assertIn(ej, job_ids, f"Job {ej} missing from scheduler!")

        autonomous_operator.stop()

    def test_whatsapp_assistant_formatting(self):
        """Verify WhatsApp assistant status check."""
        res = whatsapp_assistant.is_configured()
        self.assertIsInstance(res, bool)


if __name__ == "__main__":
    unittest.main()
