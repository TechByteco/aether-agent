import unittest
import sys
import time
from pathlib import Path

# Ensure UTF-8 output on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "src"))

from aether.brain.claude_agent import claude_agent


class TestClaudeLiveInference(unittest.TestCase):
    def test_model_resolution(self):
        active_model = claude_agent.resolve_active_model()
        self.assertTrue(bool(active_model))

    def test_agent_structure(self):
        self.assertTrue(hasattr(claude_agent, "execute_turn"))


if __name__ == "__main__":
    unittest.main()

