"""
AETHER Desktop Vision & Application Automation Test Suite
=========================================================
Verifies screen capture, active application discovery, UI mouse/keyboard interactions,
and Windows service management.
"""

from pathlib import Path
import unittest

from aether.tools.desktop_controller import (
    tool_list_running_applications,
    tool_launch_or_focus_app,
    tool_manage_windows_service,
    tool_capture_desktop_display,
    tool_interact_ui,
    tool_see_screen_and_analyze,
)


class TestDesktopControllerSuite(unittest.TestCase):

    def test_list_running_applications(self):
        """Test listing active processes and applications."""
        res = tool_list_running_applications()
        self.assertEqual(res["status"], "success")
        self.assertGreater(res["total_active_apps"], 0)
        apps = [a["name"] for a in res["applications"]]
        self.assertTrue(any("exe" in a.lower() for a in apps))

    def test_manage_windows_service_status(self):
        """Test querying Windows background service status."""
        res = tool_manage_windows_service("wuauserv", action="status")
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["service"], "wuauserv")
        self.assertIn("SERVICE_NAME", res["output"].upper())

    def test_capture_desktop_display(self):
        """Test screen capture and resolution calculation."""
        res = tool_capture_desktop_display()
        self.assertEqual(res["status"], "success")
        self.assertTrue(Path(res["image_path"]).exists())
        self.assertGreater(res["width"], 100)
        self.assertGreater(res["height"], 100)

    def test_interact_ui_mouse_move_and_scroll(self):
        """Test safe mouse movement and scroll actions."""
        # Test move
        res_move = tool_interact_ui(action="move", x=100, y=100)
        self.assertEqual(res_move["status"], "success")
        self.assertEqual(res_move["target"], {"x": 100, "y": 100})

        # Test scroll
        res_scroll = tool_interact_ui(action="scroll", scroll_amount=-120)
        self.assertEqual(res_scroll["status"], "success")
        self.assertEqual(res_scroll["amount"], -120)

    def test_see_screen_and_analyze(self):
        """Test unified display perception and app context extraction."""
        res = tool_see_screen_and_analyze(prompt="Summarize open windows.")
        self.assertEqual(res["status"], "success")
        self.assertTrue(Path(res["image_path"]).exists())
        self.assertGreater(len(res["active_applications"]), 0)
        self.assertIn("Screen captured at", res["visual_summary"])


if __name__ == "__main__":
    unittest.main()
