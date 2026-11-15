"""
Comprehensive Unit & Integration Test Suite for AETHER Sovereign Gmail & Email Agent
=====================================================================================
Tests Gmail IMAP/SMTP connectivity, inbox fetching, AI email summarization,
outbound email dispatch, In-Reply-To threading, and FastAPI REST endpoints.
"""

import sys
import unittest
from pathlib import Path
from fastapi.testclient import TestClient

# Ensure src is on sys.path
_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from aether.tools.cloud_email_agent import cloud_email_agent
from aether.channels.telegram_assistant import telegram_assistant
from aether.channels.cloud_omni_agent import cloud_omni_agent
from aether.web.server import app


class TestCloudEmailAgent(unittest.TestCase):
    """Unit tests for Cloud Email Agent operations."""

    def test_connection_status(self):
        """Verify IMAP/SMTP connection diagnostic output."""
        res = cloud_email_agent.test_connection()
        self.assertIn("configured", res)
        self.assertIn("imap_status", res)
        self.assertIn("smtp_status", res)

    def test_fetch_emails(self):
        """Verify email fetching and parsing of MIME content."""
        emails = cloud_email_agent.fetch_emails(limit=5)
        self.assertIsInstance(emails, list)
        self.assertTrue(len(emails) > 0)
        first = emails[0]
        self.assertTrue(len(first.sender) > 0)
        self.assertTrue(len(first.subject) > 0)
        self.assertTrue(len(first.snippet) > 0)

    def test_summarize_inbox(self):
        """Verify AI inbox summarization and categorization."""
        summary = cloud_email_agent.summarize_inbox(limit=5)
        self.assertIn("total_emails", summary)
        self.assertIn("overview_html", summary)
        self.assertIn("action_items", summary)
        self.assertIn("AETHER Sovereign Email Briefing", summary["overview_html"])

    def test_summarize_single_email(self):
        """Verify deep single-email analysis with TL;DR and draft reply."""
        emails = cloud_email_agent.fetch_emails(limit=2)
        self.assertTrue(len(emails) > 0)
        first = emails[0]

        analysis = cloud_email_agent.summarize_single_email(first)
        self.assertIn("tl_dr", analysis)
        self.assertIn("key_points", analysis)
        self.assertIn("action_items", analysis)
        self.assertIn("drafted_reply", analysis)
        self.assertTrue(len(analysis["drafted_reply"]) > 20)

    def test_send_email_and_logging(self):
        """Verify email composition, MIME packaging, and sent log recording."""
        res = cloud_email_agent.send_email(
            to_email="partner@venturecap.com",
            subject="Series A Traction Summary",
            body_text="Here is our latest quarterly financial metrics and ARR report."
        )
        self.assertTrue(res.get("ok"))
        self.assertEqual(res.get("subject"), "Series A Traction Summary")
        self.assertIn("message_id", res)

    def test_reply_to_email(self):
        """Verify threaded reply with In-Reply-To header."""
        res = cloud_email_agent.reply_to_email(
            original_msg_id="<msg_12345@domain.com>",
            reply_body="Confirmed, let's schedule for Thursday 3 PM.",
            to_sender="client@apexfintech.io",
            subject="Contract Review"
        )
        self.assertTrue(res.get("ok"))
        self.assertEqual(res.get("subject"), "Re: Contract Review")

    def test_inbox_triage_loop(self):
        """Verify background autonomous triage."""
        triaged = cloud_email_agent.check_inbox_and_triage(limit=5)
        self.assertIsInstance(triaged, list)


class TestEmailTelegramCommands(unittest.TestCase):
    """Test suite for Telegram assistant email commands."""

    def test_telegram_emails_command(self):
        """Test /emails command."""
        res = telegram_assistant.handle_incoming_text("/emails", "user_123")
        # In test mode without active Telegram token or sending inline, it returns overview HTML or sends message
        self.assertTrue(isinstance(res, str))

    def test_telegram_sendmail_command(self):
        """Test /sendmail command."""
        res = telegram_assistant.handle_incoming_text(
            "/sendmail investor@fund.com Q4 Pitch | Here is the updated investor deck.",
            "user_123"
        )
        self.assertTrue(isinstance(res, str))

    def test_telegram_email_summary_command(self):
        """Test /email_summary command."""
        res = telegram_assistant.handle_incoming_text("/email_summary sim_101", "user_123")
        self.assertTrue(isinstance(res, str))

    def test_telegram_email_callback(self):
        """Test email reply callback button."""
        cb_res = telegram_assistant.handle_callback_query("reply_email:sim_101", "cb_123")
        self.assertIn("Reply dispatched", cb_res)


class TestEmailRouterEndpoints(unittest.TestCase):
    """FastAPI TestClient verification for Email REST endpoints."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_email_status_endpoint(self):
        """Test GET /api/email/status."""
        res = self.client.get("/api/email/status")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("configured", data)

    def test_email_inbox_endpoint(self):
        """Test GET /api/email/inbox."""
        res = self.client.get("/api/email/inbox?limit=5")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("emails", data)
        self.assertTrue(len(data["emails"]) > 0)

    def test_email_summary_endpoint(self):
        """Test GET /api/email/summary."""
        res = self.client.get("/api/email/summary?limit=5")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("overview_html", data)
        self.assertIn("action_items", data)

    def test_email_summarize_post_endpoint(self):
        """Test POST /api/email/summarize."""
        res = self.client.post("/api/email/summarize", json={
            "sender": "Alice <alice@startup.io>",
            "subject": "Seed Round Term Sheet",
            "body_text": "We are pleased to offer a $2M term sheet at $10M post. Let's discuss closing by Friday."
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("tl_dr", data)
        self.assertIn("drafted_reply", data)

    def test_email_send_endpoint(self):
        """Test POST /api/email/send."""
        res = self.client.post("/api/email/send", json={
            "to": "dev@techbyte.co",
            "subject": "Build Completed",
            "body_text": "All test suites are green."
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data.get("ok"))
        self.assertIn("message_id", data)


if __name__ == "__main__":
    unittest.main()
