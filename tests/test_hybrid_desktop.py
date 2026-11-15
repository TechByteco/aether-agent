"""
AETHER Hybrid Edge-Cloud Desktop Agent Test Suite
=================================================
Verifies automated task decomposition, visual state perception,
step execution, and closed-loop verification.
"""

from pathlib import Path
import tempfile
import unittest

from aether.brain.hybrid_desktop_agent import HybridDesktopAgent, DesktopTaskStep


class TestHybridDesktopSuite(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.tmpdir.name)
        self.agent = HybridDesktopAgent(workspace_root=self.workspace)

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_perceive_current_state(self):
        """Test capturing screen state and running processes."""
        state = self.agent.perceive_current_state()
        self.assertIn("screen_path", state)
        self.assertIn("active_applications", state)
        self.assertGreater(state["total_running_apps"], 0)
        self.assertTrue(Path(state["screen_path"]).exists())

    def test_plan_desktop_task_browser(self):
        """Test task decomposition for browser assignment."""
        steps = self.agent.plan_desktop_task("Open Chrome and navigate to https://github.com")
        self.assertGreaterEqual(len(steps), 2)
        self.assertEqual(steps[0].action_type, "launch")
        self.assertEqual(steps[0].params["app_name"], "chrome")
        self.assertEqual(steps[-1].action_type, "verify")

    def test_plan_desktop_task_terminal(self):
        """Test task decomposition for terminal assignment."""
        steps = self.agent.plan_desktop_task("Open PowerShell terminal and inspect system")
        self.assertGreaterEqual(len(steps), 2)
        self.assertEqual(steps[0].action_type, "launch")
        self.assertEqual(steps[0].params["app_name"], "powershell")

    def test_execute_step_verify(self):
        """Test executing verification step."""
        step = DesktopTaskStep(
            step_id=1,
            action_type="verify",
            params={"prompt": "Test screen verification"}
        )
        res = self.agent.execute_step(step)
        self.assertEqual(res["status"], "success")
        self.assertEqual(step.status, "success")
        self.assertIsNotNone(step.output)

    def test_execute_autonomous_desktop_mission(self):
        """Test end-to-end autonomous mission execution."""
        mission_res = self.agent.execute_autonomous_desktop_mission("Inspect current display and verify running apps")
        self.assertEqual(mission_res["status"], "success")
        self.assertGreater(mission_res["total_steps"], 0)
        self.assertIn("initial_state", mission_res)
        self.assertIn("final_state", mission_res)


if __name__ == "__main__":
    unittest.main()
