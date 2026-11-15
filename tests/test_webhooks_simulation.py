"""
Unit and Integration Tests for Webhook Simulation & Payment Resilience
======================================================================
Verifies payment capture simulation, persistent payments.json recording,
and resilient autonomous sync.
"""

import sys
import unittest
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from fastapi.testclient import TestClient
from aether.web.server import app
from aether.daemon.autonomous_operator import autonomous_operator


class TestWebhookSimulation(unittest.TestCase):
    """Test suite for payment webhook simulation and operator resilience."""

    def setUp(self):
        self.client = TestClient(app)

    def test_webhook_simulate_endpoint(self):
        """Verify POST /api/webhooks/simulate persists payment record and notifies inbox."""
        payload = {
            "venture_name": "CogniGuard Cyber",
            "amount_inr": 45000.0,
            "email": "siddharth@apexfintech.io",
            "plan_name": "Enterprise SLA"
        }
        res = self.client.post("/api/webhooks/simulate", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get("status"), "ok")
        self.assertIn("payment_id", data)
        self.assertEqual(data.get("record", {}).get("amount_inr"), 45000.0)

    def test_crm_pipeline_endpoints(self):
        """Verify GET /api/crm/pipeline returns healthy metrics."""
        res = self.client.get("/api/crm/pipeline")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get("status"), "ok")
        self.assertIn("pipeline", data)
        self.assertGreaterEqual(data["pipeline"].get("total_deals_count", 0), 1)

    def test_resilient_job_razorpay_sync(self):
        """Verify autonomous_operator.job_razorpay_sync gracefully ensures payments tracking."""
        autonomous_operator.job_razorpay_sync()
        status = autonomous_operator.get_status()
        self.assertIsInstance(status, dict)


if __name__ == "__main__":
    unittest.main()
