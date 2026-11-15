"""
Unit Tests for LEON Business Portfolio & Low-Cost Subscription Manager
======================================================================
"""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import aether.brain.leon_portfolio_manager as lpm
from aether.brain.leon_portfolio_manager import (
    LEONPortfolioManager,
    tool_leon_launch_all_low_cost_businesses,
    tool_leon_get_portfolio_status,
    tool_leon_revise_business_pricing,
    tool_leon_auto_scale_portfolio_pricing,
)
from aether.brain.leon_deployer import DeployProvider


class TestLEONPortfolioManager(unittest.TestCase):
    def setUp(self):
        # Isolated registry so tests never mutate live production pricing.
        self._tmp = tempfile.TemporaryDirectory()
        self.pm = LEONPortfolioManager(workspace_root=Path(self._tmp.name))
        self._patch = mock.patch.object(lpm, "leon_portfolio_manager", self.pm)
        self._patch.start()

    def tearDown(self):
        self._patch.stop()
        self._tmp.cleanup()

    def test_canonical_portfolio_loading(self):
        """Test canonical business portfolio contains all 5 core ventures."""
        summary = self.pm.get_portfolio_summary()
        self.assertGreaterEqual(len(summary), 5)
        slugs = [s["slug"] for s in summary]
        self.assertIn("cloudflow-ai", slugs)
        self.assertIn("leadpulse-pro", slugs)
        self.assertIn("apexstudio-ai", slugs)
        self.assertIn("cogniguard-cyber", slugs)
        self.assertIn("aether-sovereign-os", slugs)

    def test_launch_all_low_cost_businesses(self):
        """Test launching all business models with low cost subscriptions."""
        results = self.pm.launch_all_low_cost_businesses(provider=DeployProvider.LOCAL_PREVIEW)
        self.assertEqual(len(results), 5)
        for r in results:
            self.assertEqual(r["status"], "DEPLOYED_LIVE")
            self.assertIn("₹", r["monthly_price"])

    def test_pricing_revision_workflow(self):
        """Test updating price of a single venture and tracking history."""
        res = self.pm.revise_venture_pricing(
            slug_or_name="aether-sovereign-os",
            new_monthly_price_inr=199.0,
            new_annual_price_inr=1599.0,
            reason="Phase 2 Feature Expansion Upgrade",
            provider=DeployProvider.LOCAL_PREVIEW,
        )
        self.assertTrue(res["success"])
        self.assertIn("₹199", res["new_pricing"])
        self.assertGreaterEqual(res["total_revisions"], 2)

    def test_auto_scale_portfolio_tiers(self):
        """Test systematically scaling portfolio subscription tiers."""
        revs = self.pm.auto_scale_portfolio_tiers(increment_percent=20.0, provider=DeployProvider.LOCAL_PREVIEW)
        self.assertEqual(len(revs), 5)
        for r in revs:
            self.assertTrue(r["success"])


    def test_rewoo_tool_wrappers(self):
        """Test ReWOO native tool wrappers."""
        status_text = tool_leon_get_portfolio_status()
        self.assertIn("LEON Multi-Venture Portfolio Status", status_text)
        self.assertIn("CloudFlow AI", status_text)

        rev_text = tool_leon_revise_business_pricing(
            venture_name_or_slug="cloudflow-ai",
            new_monthly_price_inr=249.0,
            new_annual_price_inr=1999.0,
            reason="Enterprise AST Self-Healing Release",
            provider="local",
        )
        self.assertIn("LEON Pricing Revision", rev_text)
        self.assertIn("₹249", rev_text)



if __name__ == "__main__":
    unittest.main()
