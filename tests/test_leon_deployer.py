import os
import unittest
from pathlib import Path
from unittest import mock
from aether.brain.leon_deployer import (
    leon_deployer,
    DeployProvider,
    DeploymentResult,
    tool_leon_deploy_venture_to_cloud,
    tool_leon_create_stripe_payment_link,
    tool_leon_create_razorpay_checkout,
    tool_leon_get_deployed_ventures,
)


class TestLEONDeployer(unittest.TestCase):
    def setUp(self):
        self.venture_name = "CloudFlow AI"
        self.niche = "developer_tools"
        self.value_prop = "Automated AI-powered infrastructure drift detection and continuous AST self-healing."

    def test_landing_page_synthesis(self):
        """Test synthesizing production-ready HTML5 + Tailwind landing page with Razorpay script."""
        html = leon_deployer.generate_production_landing_page(
            venture_name=self.venture_name,
            niche=self.niche,
            value_prop=self.value_prop,
            monthly_price_inr=1499.0,
            annual_price_inr=11999.0,
        )
        self.assertIn("<!DOCTYPE html>", html)
        self.assertIn("cdn.tailwindcss.com", html)
        self.assertIn("checkout.razorpay.com/v1/checkout.js", html)
        self.assertIn("triggerPayment", html)
        self.assertIn(self.venture_name, html)
        self.assertIn("application/ld+json", html)
        self.assertIn("Starter Pro", html)
        self.assertIn("Sovereign Growth", html)
        self.assertIn("₹1499", html)

    def test_razorpay_checkout_formulation(self):
        """Test Razorpay configuration formulation with live Key ID."""
        res = leon_deployer.formulate_razorpay_checkout(
            venture_name=self.venture_name,
            amount_inr=999.0,
            tier_name="Pro Plan",
        )
        self.assertTrue(res["success"])
        self.assertEqual(res["gateway"], "razorpay")
        self.assertEqual(res["currency"], "INR")
        self.assertEqual(res["amount_paise"], 99900)
        self.assertEqual(res["amount_inr"], 999.0)
        self.assertTrue(res["key_id"].startswith("rzp_"))
        self.assertIn("UPI", res["methods_supported"])

    def test_stripe_checkout_formulation(self):
        """Test Stripe payment link and checkout session generation."""
        res = leon_deployer.formulate_stripe_checkout(
            venture_name=self.venture_name,
            amount_inr=999.0,
            tier_name="Pro Plan",
        )
        self.assertTrue(res["success"])
        # Without a live Stripe key, checkout stays on-page (never a fake buy.stripe.com link).
        self.assertNotIn("buy.stripe.com/demo", res["checkout_url"])
        self.assertEqual(res["amount_inr"], 999.0)
        self.assertIn("webhook_endpoint", res)

    @mock.patch.dict(os.environ, {"VERCEL_TOKEN": ""})
    def test_1click_venture_deployment(self):
        """Test 1-Click deployment packaging and registry persistence (no real cloud push)."""
        dep = leon_deployer.deploy_venture(
            venture_name=self.venture_name,
            niche=self.niche,
            value_prop=self.value_prop,
            provider=DeployProvider.VERCEL,
            monthly_price_inr=999.0,
        )
        self.assertIsInstance(dep, DeploymentResult)
        self.assertEqual(dep.status, "deployed")
        self.assertIn("vercel.app", dep.live_url)
        
        # Verify files created on disk
        preview_path = Path(dep.preview_dir)
        self.assertTrue((preview_path / "index.html").exists())
        self.assertTrue((preview_path / "vercel.json").exists())
        self.assertTrue((preview_path / "netlify.toml").exists())

    def test_native_tool_wrappers(self):
        """Test ReWOO tool dispatcher functions."""
        deploy_res = tool_leon_deploy_venture_to_cloud(
            venture_name="ApexStudio",
            niche="agency_services",
            value_prop="High-converting autonomous digital studio for luxury brands.",
            provider="netlify",
        )
        self.assertIn("LEON 1-Click Cloud Deployer", deploy_res)
        self.assertIn("netlify.app", deploy_res)

        stripe_res = tool_leon_create_stripe_payment_link(
            venture_name="ApexStudio",
            tier_name="Enterprise Retainer",
            amount_inr=24999.0,
        )
        self.assertIn("LEON Stripe Gateway", stripe_res)
        self.assertIn("₹24999", stripe_res)

        razorpay_res = tool_leon_create_razorpay_checkout(
            venture_name="ApexStudio",
            tier_name="Starter Pro",
            amount_inr=1499.0,
        )
        self.assertIn("LEON Razorpay Gateway", razorpay_res)
        self.assertIn("rzp_", razorpay_res)
        self.assertIn("₹1499", razorpay_res)

        registry_res = tool_leon_get_deployed_ventures()
        self.assertIn("LEON Cloud Deployed Ventures Registry", registry_res)


if __name__ == "__main__":
    unittest.main()

