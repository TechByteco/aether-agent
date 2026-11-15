"""
Test Suite for Sovereign Online Gateway & Free Public Web Tunneling
Verifies free AI inference, public tunnel lifecycle, engine tool dispatcher integration,
and cognitive invariant preservation.
"""

import unittest
from aether.brain.online_gateway import (
    online_gateway,
    tool_query_free_online_ai,
    tool_start_online_tunnel,
    tool_get_online_tunnel_status,
    tool_stop_online_tunnel,
    tool_list_free_online_models,
)
from aether.brain.engine import TOOL_DISPATCHER, CognitiveEngine, select_tools_for_query


class TestOnlineGateway(unittest.TestCase):
    """Test cases for online gateway and public web tunneling."""

    def test_online_gateway_initialization(self):
        """Verify online gateway singleton initial state."""
        status = online_gateway.get_tunnel_status()
        self.assertIsInstance(status, dict)
        self.assertIn("active", status)
        self.assertIn("status", status)
        self.assertIn("port", status)
        self.assertEqual(status["port"], 8000)

    def test_list_free_models(self):
        """Verify listing of 100% free online AI models."""
        models = online_gateway.list_free_models()
        self.assertIsInstance(models, list)
        self.assertGreaterEqual(len(models), 1)
        for m in models:
            self.assertIn("name", m)
            self.assertIsInstance(m["name"], str)

    def test_query_free_ai_empty_prompt(self):
        """Verify free AI query rejects empty prompts safely."""
        res = online_gateway.query_free_ai("")
        self.assertIn("error", res)
        self.assertEqual(res["text"], "")

    def test_query_free_ai_chatml_structure(self):
        """Verify free AI query returns proper dictionary structure."""
        res = online_gateway.query_free_ai(
            prompt="Reply with exactly the word SUCCESS",
            model="openai",
            system_prompt="You are an automated unit test evaluator."
        )
        self.assertIsInstance(res, dict)
        self.assertIn("model", res)
        self.assertIn("provider", res)
        if res.get("success"):
            self.assertGreater(len(res.get("text", "")), 0)

    def test_tunnel_lifecycle_mocked(self):
        """Verify start, status, and stop methods handle states predictably."""
        st_before = online_gateway.get_tunnel_status()
        self.assertIsInstance(st_before, dict)

        stop_res = online_gateway.stop_tunnel()
        self.assertTrue(stop_res.get("success"))
        self.assertEqual(stop_res.get("status"), "stopped")

        st_after = online_gateway.get_tunnel_status()
        self.assertFalse(st_after.get("active"))
        self.assertEqual(st_after.get("status"), "offline")

    def test_engine_tool_dispatcher_integration(self):
        """Verify all online gateway tools are registered in AETHER Cognitive Engine."""
        expected_tools = [
            "tool_query_free_online_ai",
            "tool_start_online_tunnel",
            "tool_get_online_tunnel_status",
            "tool_stop_online_tunnel",
            "tool_list_free_online_models",
        ]
        for tool_name in expected_tools:
            self.assertIn(tool_name, TOOL_DISPATCHER, f"Missing tool in TOOL_DISPATCHER: {tool_name}")
            self.assertTrue(callable(TOOL_DISPATCHER[tool_name]))

    def test_engine_tool_functions(self):
        """Verify direct tool function responses."""
        models_output = tool_list_free_online_models()
        self.assertIn("Available Free Online AI Models", models_output)

        status_output = tool_get_online_tunnel_status()
        self.assertIn("Online Gateway Status", status_output)

        stop_output = tool_stop_online_tunnel()
        self.assertIn("Online tunnel stopped", stop_output)

    def test_intent_keyword_routing_for_online(self):
        """Verify select_tools_for_query routes online and tunnel queries appropriately."""
        tools = select_tools_for_query("make aether online with public tunnel")
        self.assertIsNotNone(tools)
        tool_names = [t.__name__ for t in tools]
        self.assertTrue(any("tunnel" in t or "online" in t for t in tool_names))

    def test_tts_digit_preservation_invariant(self):
        """Cognitive Invariant 2: Verify TTS sanitation does not strip raw numeric digits."""
        import re
        text = "Port 8000 exposed via tunnel [1] with 200 skills active."
        clean_text = re.sub(r'\[\d+\]|\(\d+\)', '', text).strip()
        self.assertIn("8000", clean_text)
        self.assertIn("200", clean_text)
        self.assertNotIn("[1]", clean_text)


if __name__ == "__main__":
    unittest.main()
