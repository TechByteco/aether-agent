"""
Unit & Integration Test Suite for AETHER Windows Native Apps Controller
=======================================================================
Tests direct connections to Windows Clock, Mail, Calendar, Calculator, Notepad,
and desktop toast audio alerts.
"""

import sys
import unittest
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from aether.tools.windows_native_apps import windows_apps
from aether.channels.cloud_omni_agent import cloud_omni_agent


class TestWindowsNativeApps(unittest.TestCase):
    """Test suite for Windows Native Application Deep-Link Controller."""

    def test_windows_clock_app_integration(self):
        """Verify Windows clock app protocol generation."""
        res = windows_apps.open_clock_app(view="alarm")
        self.assertTrue("Clock" in res or "ms-clock" in res)

        # Schedule Windows alarm
        sched = windows_apps.schedule_windows_alarm(time_str="07:30 AM", name="Executive Standup")
        self.assertIn("Windows Alarm", sched)
        self.assertIn("Executive Standup", sched)

    def test_windows_mail_integration(self):
        """Verify Windows mail app protocol and drafting."""
        res = windows_apps.open_mail_app(
            to="founder@company.com",
            subject="Growth Review",
            body="Here is the latest financial report."
        )
        self.assertIn("Mail", res)
        self.assertIn("founder@company.com", res)

    def test_windows_calendar_integration(self):
        """Verify Windows calendar app launch."""
        res = windows_apps.open_calendar_app()
        self.assertIn("Calendar", res)

    def test_windows_system_app_launcher(self):
        """Verify launching common Windows apps."""
        for app in ["calculator", "notepad", "settings"]:
            res = windows_apps.open_system_app(app)
            self.assertTrue(app.title() in res or "Launched" in res)

    def test_omni_agent_windows_tool_dispatch(self):
        """Verify CloudOmniAgent can trigger Windows tools via natural language or tool call."""
        tool_res = cloud_omni_agent.execute_tool("open_clock_app", {"view": "timer"})
        self.assertIn("Clock", tool_res)

        mail_res = cloud_omni_agent.execute_tool("open_mail_app", {"to": "test@domain.com", "subject": "Hi"})
        self.assertIn("Mail", mail_res)


if __name__ == "__main__":
    unittest.main()
