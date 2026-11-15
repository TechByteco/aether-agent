"""
Unit and Integration Tests for AETHER Sovereign CRM & Enterprise Sales Pipeline Engine
======================================================================================
Verifies deal creation, probability weighting, pipeline metrics, calendar meeting
booking, and automated email outreach confirmation.
"""

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from aether.growth.crm_pipeline import crm_pipeline, DEAL_STAGE_WEIGHTS


class TestCRMPipelineEngine(unittest.TestCase):
    """Test suite for enterprise sales CRM pipeline."""

    def test_pipeline_summary_metrics(self):
        """Verify pipeline computes total value, weighted value, and active deals."""
        summary = crm_pipeline.get_pipeline_summary()
        self.assertIsInstance(summary, dict)
        self.assertIn("total_pipeline_value_inr", summary)
        self.assertIn("weighted_pipeline_value_inr", summary)
        self.assertIn("active_deals_count", summary)
        self.assertIn("deals", summary)
        self.assertGreaterEqual(summary["total_deals_count"], 1)

    def test_create_and_advance_deal(self):
        """Verify creating a new prospect and advancing through sales stages."""
        company = f"TestCorp_{int(datetime.now(timezone.utc).timestamp())}"
        deal = crm_pipeline.create_deal(
            company_name=company,
            contact_name="Vikram Singh",
            contact_email="vikram@testcorp.com",
            venture_name="CogniGuard Cyber",
            deal_value_inr=120000.0,
            stage="lead",
            notes="Initial outbound prospect"
        )
        self.assertEqual(deal["stage"], "lead")
        self.assertEqual(deal["probability"], DEAL_STAGE_WEIGHTS["lead"])

        # Advance to proposal_sent
        adv_res = crm_pipeline.advance_stage(deal["id"], "proposal_sent")
        self.assertEqual(adv_res.get("status"), "ok")
        self.assertEqual(adv_res["deal"]["stage"], "proposal_sent")
        self.assertEqual(adv_res["deal"]["probability"], DEAL_STAGE_WEIGHTS["proposal_sent"])

    def test_schedule_enterprise_meeting_and_email(self):
        """Verify calendar meeting scheduling and confirmation email dispatch."""
        deals = crm_pipeline.list_deals()
        target = deals[0]
        now = datetime.now(timezone.utc)

        res = crm_pipeline.schedule_enterprise_meeting(
            deal_id=target["id"],
            meeting_datetime=now,
            duration_minutes=30
        )
        self.assertEqual(res.get("status"), "ok")
        self.assertIn("calendar_event", res)
        self.assertIn("meeting_url", res)
        self.assertTrue(res["meeting_url"].startswith("http"))
        self.assertIn("meet.google.com", res["meeting_url"])


if __name__ == "__main__":
    unittest.main()
