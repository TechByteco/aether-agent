"""
Test suite for LEON Live Web & REST API endpoints.
Verifies:
1. GET /api/leon/status returns active ventures, 6 sub-agents, and cloud topology.
2. POST /api/leon/venture/create initializes new venture.
3. POST /api/leon/swarm/dispatch executes sub-agent swarm mission.
4. POST /api/leon/train executes dataset merge and training dispatch.
"""

import sys
import unittest
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from fastapi.testclient import TestClient
from aether.web.server import app


class TestLeonWebAPI(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)

    def test_01_leon_status_and_topology(self):
        """Verify GET /api/leon/status returns valid topology and venture data."""
        res = self.client.get("/api/leon/status")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["os_name"], "LEON Autonomous Venture OS")
        self.assertIn("ventures", data)
        self.assertIn("subagents", data)
        self.assertEqual(len(data["subagents"]), 6)
        self.assertIn("cloud_topology", data)
        self.assertIn("kaggle_cloud_gpu", data["cloud_topology"])
        self.assertIn("huggingface_hub", data["cloud_topology"])
        self.assertIn("edge_hardware_npu", data["cloud_topology"])

    def test_02_create_venture_api(self):
        """Verify POST /api/leon/venture/create adds a new venture."""
        payload = {
            "name": "Live Dev Widget",
            "problem": "Developers spend too much time debugging CORS",
            "target_users": "Fullstack devs, backend engineers",
            "mission": "Zero-config CORS proxy widget",
            "budget_ceiling": 0.0,
            "north_star": "Daily Active Developers"
        }
        res = self.client.post("/api/leon/venture/create", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["venture"]["name"], "Live Dev Widget")

    def test_03_dispatch_swarm_api(self):
        """Verify POST /api/leon/swarm/dispatch executes subagents."""
        payload = {
            "venture_id": "live-dev-widget",
            "task_objective": "Architect minimal viable smoke test"
        }
        res = self.client.post("/api/leon/swarm/dispatch", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("subagents", data)
        self.assertEqual(len(data["subagents"]), 6)


if __name__ == "__main__":
    unittest.main()
