"""
Unit & Integration Test Suite for AETHER Cloud Omni-Agent Cortex
================================================================
Tests natural language understanding, multi-tool execution, and cross-application connections.
"""

import sys
import unittest
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from aether.channels.cloud_omni_agent import cloud_omni_agent


class TestCloudOmniAgent(unittest.TestCase):
    """Test suite for Cloud Omni-Agent multi-tool reasoning cortex."""

    def test_tool_execute_directly(self):
        """Verify tool execution engine executes native tools directly."""
        # 1. Calendar agenda
        cal_res = cloud_omni_agent.execute_tool("manage_calendar", {"action": "list_agenda"})
        self.assertIsInstance(cal_res, str)

        # 2. Tasks & Alarms
        task_res = cloud_omni_agent.execute_tool("manage_alarms", {"action": "create_reminder", "task_text": "in 10m Check server health"})
        self.assertTrue("Scheduled" in task_res or "Alarm" in task_res)

        # 3. Security Audit
        sec_res = cloud_omni_agent.execute_tool("run_security_audit", {"domain": "github.com"})
        self.assertIn("Security Audit", sec_res)
        self.assertIn("SSL Grade", sec_res)

        # 4. Code Execution Sandbox
        code_res = cloud_omni_agent.execute_tool("execute_code", {"code": "print(sum(range(1, 11)))"})
        self.assertIn("55", code_res)

        # 5. Market Radar
        radar_res = cloud_omni_agent.execute_tool("scan_market_radar", {})
        self.assertIsInstance(radar_res, str)

    def test_natural_language_orchestration(self):
        """Verify freeform natural language query processing."""
        reply = cloud_omni_agent.process_message("What is the current status of my 5 business ventures?")
        self.assertTrue(len(reply) > 20)


if __name__ == "__main__":
    unittest.main()
