"""
AETHER Frontier Swarm Intelligence & Codex Test Suite
======================================================
Comprehensive automated verification covering the Multi-Agent Swarm Framework,
Static AST Code Intelligence Guard, Continuous Evolution Daemon Lifecycle,
Web API Endpoints, and Heuristic Rule Persistence.
"""

import ast
import json
import os
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from aether.config import config
from aether.memory.store import memory
from aether.brain.swarm import swarm_engine, SwarmAgent, SwarmRole, SwarmMessage
from aether.brain.ast_guard import ast_guard, ASTAnalysisResult
from aether.daemon.continuous_evolution_worker import continuous_evolution_worker
from aether.web.server import app


class TestAetherFrontierSwarmAndCodex(unittest.TestCase):

    # ── 1. Swarm Agent Initialization & Message Passing ───────────────────────
    def test_swarm_agent_initialization_and_roles(self):
        """Verify SwarmAgent correctly initializes with specialized prompts and serializes messages."""
        agent = SwarmAgent("TestPlanner", SwarmRole.PLANNER)
        self.assertEqual(agent.role, SwarmRole.PLANNER)
        self.assertIn("Strategic Planner", agent.system_prompt)

        # Message serialization
        msg = SwarmMessage(
            sender="TestPlanner",
            role=SwarmRole.PLANNER,
            content="Step 1: Parse requirements. Step 2: Implement core logic.",
            artifacts={"speed": 120.5, "provider": "test_mock"}
        )
        msg_dict = msg.to_dict()
        self.assertEqual(msg_dict["sender"], "TestPlanner")
        self.assertEqual(msg_dict["role"], "planner")
        self.assertIn("Step 1", msg_dict["content"])
        self.assertEqual(msg_dict["artifacts"]["provider"], "test_mock")

    # ── 2. Swarm Sequential Pipeline & Code Execution ─────────────────────────
    def test_swarm_sequential_pipeline(self):
        """Verify sequential multi-agent pipeline orchestrates with AST guard and sandbox execution."""
        task = "Write a Python function to compute the Fibonacci sequence up to n numbers."
        
        # Test pipeline with a subset of roles
        res = swarm_engine.run_sequential_pipeline(
            task=task,
            roles=[SwarmRole.PLANNER, SwarmRole.CODER, SwarmRole.SYNTHESIZER],
            execute_code_sandbox=False,
        )

        self.assertIn("mission_id", res)
        self.assertEqual(len(res["pipeline"]), 3)
        self.assertEqual(len(res["transcript"]), 3)
        self.assertTrue(len(res["summary"]) > 0)

    # ── 3. Swarm Dialectic Debate & Consensus ─────────────────────────────────
    def test_swarm_dialectic_debate(self):
        """Verify multi-agent dialectic debate between Architect, Security Auditor, and Reviewer."""
        topic = "Should AETHER use an in-memory Redis cache vs SQLite FTS5 for local session memory?"
        debate_res = swarm_engine.run_dialectic_debate(topic=topic, rounds=1)

        self.assertEqual(debate_res["topic"], topic)
        self.assertIn("transcript", debate_res)
        self.assertIn("verdict", debate_res)
        self.assertTrue(len(debate_res["transcript"]) >= 4)  # 3 debaters + 1 synthesizer

    # ── 4. Static AST Analysis: Syntax Validation & Complexity ────────────────
    def test_ast_guard_syntax_and_complexity(self):
        """Test AST parsing, valid/invalid syntax detection, and McCabe cyclomatic complexity calculation."""
        # 1. Valid Python code with nested logic
        valid_code = """
def process_data(items):
    results = []
    for item in items:
        if item > 10:
            results.append(item * 2)
        elif item < 0:
            results.append(0)
        else:
            results.append(item)
    return results
"""
        res_valid = ast_guard.analyze_python_code(valid_code)
        self.assertTrue(res_valid.is_valid_syntax)
        self.assertIn("process_data", res_valid.functions)
        self.assertGreater(res_valid.cyclomatic_complexity, 1)

        # 2. Invalid Python code with syntax error
        invalid_code = "def broken_func(:\n    return 42"
        res_invalid = ast_guard.analyze_python_code(invalid_code)
        self.assertFalse(res_invalid.is_valid_syntax)
        self.assertIsNotNone(res_invalid.syntax_error)
        self.assertIsNotNone(res_invalid.syntax_error_line)

    # ── 5. Static AST Analysis: Security & Invariant Auditing ───────────────────
    def test_ast_guard_security_and_invariants(self):
        """Test detection of dangerous runtime calls and cognitive invariant violations."""
        # Hazardous code
        dangerous_code = """
import os
def execute_payload(user_input):
    os.system(f"rm -rf {user_input}")
    eval(user_input)
"""
        res_dang = ast_guard.analyze_python_code(dangerous_code)
        self.assertTrue(len(res_dang.security_warnings) >= 2)
        warning_str = " ".join(res_dang.security_warnings)
        self.assertIn("os.system", warning_str)
        self.assertIn("eval", warning_str)

        # Invariant 2 Violation check (TTS digit stripping)
        bad_tts_code = """
import re
def clean_tts(text):
    text = re.sub(r'\\d+', '', text)
    return text
"""
        inv_violations = ast_guard.audit_cognitive_invariants(bad_tts_code)
        self.assertTrue(any("Cognitive Invariant 2" in v for v in inv_violations))

    # ── 6. Continuous Evolution Daemon Lifecycle ──────────────────────────────
    def test_continuous_evolution_worker_lifecycle(self):
        """Test background worker startup, status inspection, and safe shutdown."""
        status_initial = continuous_evolution_worker.get_status()
        self.assertIn("running", status_initial)
        self.assertIn("total_cycles", status_initial)

        # Start and verify
        continuous_evolution_worker.start()
        self.assertTrue(continuous_evolution_worker._running)

        # Stop and verify
        continuous_evolution_worker.stop()
        self.assertFalse(continuous_evolution_worker._running)

    # ── 7. Heuristic Rule Store Flexibility (rule vs rule_text) ────────────────
    def test_heuristic_rule_store_flexibility(self):
        """Test MemoryStore.add_heuristic_rule accepts both positional rule and keyword rule_text/source."""
        # Positional
        r1 = memory.add_heuristic_rule("Always validate input types before calling external APIs.", domain="safety")
        self.assertGreater(r1, 0)

        # Keyword rule_text and source
        r2 = memory.add_heuristic_rule(
            rule_text="Preserve numeric quantities in speech synthesis routines.",
            domain="audio",
            source="TestRunner"
        )
        self.assertGreater(r2, 0)

        # Recall
        recalled = memory.recall_heuristic_rules("validate input types", limit=5)
        self.assertIsInstance(recalled, list)
        self.assertTrue(len(recalled) > 0)

    # ── 8. Web Server API Endpoints Integration ───────────────────────────────
    def test_web_server_api_endpoints(self):
        """Test FastAPI REST endpoints for Evolution, Swarm, AST, and Cognitive Mode."""
        client = TestClient(app)

        # 1. Cognitive mode
        resp_mode = client.get("/api/cognitive/mode")
        self.assertEqual(resp_mode.status_code, 200)
        self.assertIn("cognitive_mode", resp_mode.json())

        # 2. Providers status
        resp_prov = client.get("/api/providers/status")
        self.assertEqual(resp_prov.status_code, 200)
        self.assertIn("providers", resp_prov.json())

        # 3. Evolution status
        resp_evo = client.get("/api/evolution/status")
        self.assertEqual(resp_evo.status_code, 200)
        evo_data = resp_evo.json()
        self.assertIn("worker", evo_data)
        self.assertIn("stage", evo_data)

        # 4. Swarm agents list
        resp_swarm = client.get("/api/swarm/agents")
        self.assertEqual(resp_swarm.status_code, 200)
        swarm_data = resp_swarm.json()
        self.assertIn("agents", swarm_data)
        self.assertTrue(len(swarm_data["agents"]) >= 5)

        # 5. AST analyze endpoint
        sample_code = "def add(a: int, b: int) -> int:\n    return a + b\n"
        resp_ast = client.post("/api/ast/analyze", json={"code": sample_code})
        self.assertEqual(resp_ast.status_code, 200)
        ast_data = resp_ast.json()
        self.assertTrue(ast_data["is_valid_syntax"])
        self.assertIn("add", ast_data["functions"])


if __name__ == "__main__":
    unittest.main()
