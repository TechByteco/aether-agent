"""
AETHER Samsung Galaxy One UI 8 Integration Test Suite
=====================================================
Validates Samsung Android Intent generation, One UI 8 calendar links,
action cards, Modes & Routines webhook triggers, and FastAPI REST endpoints.
"""

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from fastapi.testclient import TestClient

# Ensure src is on sys.path
_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from aether.tools.samsung_android_controller import samsung_android
from aether.channels.samsung_router import router
from aether.web.server import app


class TestSamsungAndroidController(unittest.TestCase):
    """Unit tests for Samsung Android One UI 8 Deep-Link Controller."""

    def test_alarm_intent_generation_relative(self):
        """Test relative time parsing for alarm intent."""
        res = samsung_android.generate_samsung_alarm_intent("in 45m", "Morning Review")
        self.assertIn("intent:#Intent;action=android.intent.action.SET_ALARM;", res["intent_uri"])
        self.assertEqual(res["label"], "Morning Review")
        self.assertTrue(0 <= res["hour"] <= 23)
        self.assertTrue(0 <= res["minute"] <= 59)

    def test_alarm_intent_generation_absolute(self):
        """Test absolute 12h/24h time parsing."""
        res_am = samsung_android.generate_samsung_alarm_intent("06:30 AM", "Wakeup")
        self.assertEqual(res_am["hour"], 6)
        self.assertEqual(res_am["minute"], 30)

        res_pm = samsung_android.generate_samsung_alarm_intent("07:45 PM", "Evening Check")
        self.assertEqual(res_pm["hour"], 19)
        self.assertEqual(res_pm["minute"], 45)

    def test_calendar_link_generation(self):
        """Test Google / Samsung Calendar template link."""
        now = datetime(2026, 10, 7, 10, 0, 0, tzinfo=timezone.utc)
        link = samsung_android.generate_samsung_calendar_link(
            title="Executive Review",
            start_time=now,
            duration_minutes=45,
            description="High-priority portfolio review",
            location="Online"
        )
        self.assertIn("https://calendar.google.com/calendar/render?action=TEMPLATE", link)
        self.assertIn("text=Executive+Review", link)
        self.assertIn("dates=20261007T100000Z%2F20261007T104500Z", link)

    def test_phone_and_sms_links(self):
        """Test tel: and sms: link builders."""
        tel_link = samsung_android.generate_phone_call_link("+1 (555) 019-2834")
        self.assertEqual(tel_link, "tel:+15550192834")

        sms_link = samsung_android.generate_sms_link("+1 555-019-2834", "Hello from AETHER")
        self.assertTrue(sms_link.startswith("sms:+15550192834?body=Hello"))

    def test_mail_and_maps_links(self):
        """Test mailto: and Google Maps link builders."""
        mail_link = samsung_android.generate_mail_link("founder@techbyte.co", "Partnership", "Looking forward to speaking.")
        self.assertTrue(mail_link.startswith("mailto:founder@techbyte.co?"))
        self.assertIn("subject=Partnership", mail_link)

        maps_link = samsung_android.generate_maps_link("Cyber City Gurugram")
        self.assertTrue(
            "query=Cyber%20City%20Gurugram" in maps_link or "query=Cyber+City+Gurugram" in maps_link
        )

    def test_action_cards(self):
        """Test mobile action cards formatting with reply markup."""
        # Alarm card
        alarm_msg, alarm_kb = samsung_android.build_samsung_alarm_card("08:00 AM", "Morning Strategy")
        self.assertIn("Samsung One UI 8", alarm_msg)
        self.assertIn("inline_keyboard", alarm_kb)

        # Meeting card
        now = datetime.now(timezone.utc)
        mtg_msg, mtg_kb = samsung_android.build_samsung_meeting_card(
            title="VC Pitch",
            start_time=now,
            duration_minutes=30,
            meeting_url="https://meet.google.com/abc-defg-hij"
        )
        self.assertIn("VC Pitch", mtg_msg)
        self.assertIn("inline_keyboard", mtg_kb)

        # Phone card
        p_msg, p_kb = samsung_android.build_phone_action_card("+919876543210", "Chief Architect")
        self.assertIn("Chief Architect", p_msg)
        self.assertIn("inline_keyboard", p_kb)

        # Email card
        e_msg, e_kb = samsung_android.build_email_action_card("investor@fund.com", "Series A Pitch")
        self.assertIn("investor@fund.com", e_msg)
        self.assertIn("inline_keyboard", e_kb)

        # Nav card
        n_msg, n_kb = samsung_android.build_navigation_card("Bengaluru Airport")
        self.assertIn("Bengaluru Airport", n_msg)
        self.assertIn("inline_keyboard", n_kb)

    def test_modes_and_routines_triggers(self):
        """Test Samsung Modes & Routines triggers."""
        # Bedtime
        bedtime_res = samsung_android.handle_routine_trigger("bedtime")
        self.assertEqual(bedtime_res["status"], "success")
        self.assertEqual(bedtime_res["routine"], "bedtime")

        # Driving
        driving_res = samsung_android.handle_routine_trigger("driving")
        self.assertEqual(driving_res["status"], "success")

        # Work / Focus
        focus_res = samsung_android.handle_routine_trigger("focus")
        self.assertEqual(focus_res["status"], "success")

        # Battery low
        batt_res = samsung_android.handle_routine_trigger("battery_low")
        self.assertEqual(batt_res["status"], "success")


class TestSamsungRouterEndpoints(unittest.TestCase):
    """FastAPI TestClient verification for Samsung One UI 8 endpoints."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_samsung_status_endpoint(self):
        """Test GET /api/channels/samsung/status."""
        res = self.client.get("/api/channels/samsung/status")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "online")
        self.assertIn("Samsung Galaxy One UI 8", data["target_platform"])
        self.assertIn("android_intent_clock", data["protocols_supported"])

    def test_samsung_routine_endpoint(self):
        """Test POST /api/channels/samsung/routine."""
        res = self.client.post("/api/channels/samsung/routine", json={"routine": "driving", "payload": {"speed": 45}})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["routine"], "driving")

    def test_samsung_alarm_endpoint(self):
        """Test POST /api/channels/samsung/alarm."""
        res = self.client.post("/api/channels/samsung/alarm", json={"time_str": "07:00 AM", "label": "Standup"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("card_message", data)
        self.assertIn("reply_markup", data)
        self.assertIn("intent_data", data)

    def test_samsung_meeting_endpoint(self):
        """Test POST /api/channels/samsung/meeting."""
        res = self.client.post("/api/channels/samsung/meeting", json={
            "title": "Strategy Session",
            "duration_minutes": 45,
            "description": "Discuss Q4 Roadmap"
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("card_message", data)
        self.assertIn("calendar_url", data)

    def test_samsung_quick_action_endpoint(self):
        """Test POST /api/channels/samsung/quick-action for call and maps."""
        res_call = self.client.post("/api/channels/samsung/quick-action", json={
            "action_type": "call",
            "target": "+1234567890",
            "contact_name": "CTO"
        })
        self.assertEqual(res_call.status_code, 200)
        self.assertEqual(res_call.json()["action"], "call")

        res_maps = self.client.post("/api/channels/samsung/quick-action", json={
            "action_type": "navigation",
            "target": "Times Square New York"
        })
        self.assertEqual(res_maps.status_code, 200)
        self.assertEqual(res_maps.json()["action"], "navigation")


if __name__ == "__main__":
    unittest.main()
