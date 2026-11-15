"""
AETHER Kaggle Autonomous Cloud Training Controller Test Suite
==============================================================
Verifies Kaggle API credential loading, kernel script bundling,
situational curriculum formatting, and FastAPI endpoints.
"""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient

from aether.brain.kaggle_controller import kaggle_controller, KaggleController
from aether.web.server import app


class TestKaggleControllerSuite(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.tmpdir.name)
        self.controller = KaggleController(workspace_root=self.workspace)

    def tearDown(self):
        self.tmpdir.cleanup()

    # ── 1. Credential Management & Persistence ────────────────────────────────
    def test_credential_persistence_and_loading(self):
        """Verify KaggleController sets and retrieves credentials from disk and environment."""
        username = "test_kaggle_engineer"
        key = "a1b2c3d4e5f678901234567890abcdef"

        success = self.controller.set_credentials(username, key, persist_to_disk=True)
        self.assertTrue(success)

        # Retrieve
        u, k = self.controller.get_credentials()
        self.assertEqual(u, username)
        self.assertEqual(k, key)
        self.assertTrue(self.controller.is_configured())

    # ── 2. Auth Header Generation ─────────────────────────────────────────────
    def test_auth_header_encoding(self):
        """Verify HTTP Basic Auth and Bearer Token generation for Kaggle REST API v1."""
        # 1. Test Bearer Token
        with patch.object(self.controller, "get_api_token", return_value="KGAT_sample_token_123"):
            headers_bearer = self.controller._get_auth_header()
            self.assertEqual(headers_bearer["Authorization"], "Bearer KGAT_sample_token_123")

        # 2. Test Basic Auth fallback
        with patch.object(self.controller, "get_api_token", return_value=""):
            self.controller.set_credentials("user123", "secretkey456", persist_to_disk=False)
            headers = self.controller._get_auth_header()
            self.assertIn("Authorization", headers)
            self.assertTrue(headers["Authorization"].startswith("Basic "))
            self.assertEqual(headers["User-Agent"], "AETHER-Autonomous-Agent/1.0")

    # ── 3. Situational Curriculum Dataset Formatting ──────────────────────────
    def test_situational_curriculum_dataset(self):
        """Verify that the generated situational dataset exists and conforms to ChatML structure."""
        from scripts.generate_frontier_situational_curriculum import generate_situational_dataset
        samples = generate_situational_dataset()

        self.assertGreater(len(samples), 10)
        first = samples[0]
        self.assertIn("messages", first)
        self.assertEqual(len(first["messages"]), 3)
        self.assertEqual(first["messages"][0]["role"], "system")
        self.assertEqual(first["messages"][1]["role"], "user")
        self.assertEqual(first["messages"][2]["role"], "assistant")

    # ── 4. Web Server Kaggle API Endpoints ────────────────────────────────────
    def test_kaggle_web_endpoints(self):
        """Test /api/kaggle/status and /api/kaggle/credentials endpoints."""
        client = TestClient(app)

        # 1. Status endpoint
        resp_status = client.get("/api/kaggle/status")
        self.assertEqual(resp_status.status_code, 200)
        data = resp_status.json()
        self.assertIn("configured", data)
        self.assertIn("connection", data)

        # 2. Credentials save endpoint (with saalimin)
        with patch.object(kaggle_controller, "set_credentials", return_value=True):
            resp_creds = client.post(
                "/api/kaggle/credentials",
                json={"username": "saalimin", "key": "mock_api_key_12345"}
            )
            self.assertEqual(resp_creds.status_code, 200)
            creds_data = resp_creds.json()
            self.assertEqual(creds_data["status"], "ok")



if __name__ == "__main__":
    unittest.main()
