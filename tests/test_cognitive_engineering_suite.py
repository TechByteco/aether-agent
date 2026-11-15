"""
AETHER Cognitive Engineering Test Suite
========================================
Comprehensive automated test harness validating all cognitive invariants,
architectural boundaries, and tool executors.
"""

import os
import re
import tempfile
import time
import unittest
from pathlib import Path

from aether.config import config
from aether.memory.store import memory
from aether.tools.voice import voice
from aether.brain.thinking_cortex import thinking_cortex
from aether.brain.antigravity_codex_agent import antigravity_codex_agent
from aether.brain.multi_provider_router import multi_provider_router
from aether.tools.claude_tools import claude_view, claude_edit, claude_write, claude_grep, claude_find
from aether.tools.cybersecurity import hunt_exposed_secrets, audit_active_connections
from aether.tools.code_sandbox import execute_python_code
from aether.brain.tool_genesis import tool_genesis


class TestCognitiveEngineeringSuite(unittest.TestCase):
    
    # ── 1. Cognitive Invariant 1: SQLite FTS5 BM25 Query Sanitization ──────────
    def test_invariant_fts5_bm25_tokenization(self):
        """Invariant: NEVER pass raw multi-word prompts directly into MATCH; tokenize, strip stop-words, OR-join."""
        query = "what is the best and fast way to please tell me the battery status"
        # Test search_episodes execution
        episodes = memory.search_episodes(query, limit=3)
        self.assertIsInstance(episodes, list, "FTS5 search_episodes must return a list")

    # ── 2. Cognitive Invariant 2: Text-to-Speech (TTS) Sanitation ───────────────
    def test_invariant_tts_sanitation(self):
        """Invariant: NEVER strip raw numeric digits (\d+). Only strip citation markers like [1] or (2)."""
        raw_text = "CPU load is 85% at 3.4 GHz with [1] memory usage of 4096 MB (2) and battery at 100%."
        cleaned = voice.clean_text_for_speech(raw_text)
        
        # Digits MUST be preserved
        self.assertIn("85", cleaned, "TTS cleaner must preserve percentages and numbers")
        self.assertIn("3.4", cleaned, "TTS cleaner must preserve float decimals")
        self.assertIn("4096", cleaned, "TTS cleaner must preserve integers")
        self.assertIn("100", cleaned, "TTS cleaner must preserve battery level")
        
        # Citation markers MUST be stripped
        self.assertNotIn("[1]", cleaned, "TTS cleaner must strip citation bracket [1]")
        self.assertNotIn("(2)", cleaned, "TTS cleaner must strip citation bracket (2)")

    # ── 3. Cognitive Invariant 3: ChatML Alternation & Ollama Parameters ────────
    def test_invariant_chatml_role_alternation(self):
        """Invariant: Local chat models require strict role alternation (system -> user -> assistant -> user)."""
        from aether.brain.engine import engine
        messages = engine._prepare_turn_messages("Test message for role alternation validation.")
        
        # First message MUST be system
        self.assertEqual(messages[0]["role"], "system")
        
        # Check no consecutive identical roles
        for i in range(1, len(messages)):
            prev_role = messages[i - 1]["role"]
            curr_role = messages[i]["role"]
            self.assertNotEqual(
                prev_role, curr_role,
                f"Consecutive identical role '{curr_role}' found at index {i}"
            )
        
        # Last message MUST be user
        self.assertEqual(messages[-1]["role"], "user")

    # ── 4. Antigravity Codex Surgical Tools ────────────────────────────────────
    def test_codex_surgical_file_tools(self):
        """Test surgical view, edit, write, grep, and find tools."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "sample_service.py"
            
            # 1. Write
            code = "def calculate_tax(amount: float) -> float:\n    rate = 0.05\n    return amount * rate\n"
            w_res = claude_write(str(test_file), code)
            self.assertIn("Successfully wrote", w_res)
            self.assertTrue(test_file.exists())
            
            # 2. View
            v_res = claude_view(str(test_file), start_line=1, end_line=3)
            self.assertIn("def calculate_tax", v_res)
            self.assertIn("rate = 0.05", v_res)
            
            # 3. Edit (Surgical Replacement)
            e_res = claude_edit(str(test_file), "rate = 0.05", "rate = 0.10  # Updated")
            self.assertIn("Successfully replaced", e_res)
            updated_content = test_file.read_text(encoding="utf-8")
            self.assertIn("rate = 0.10", updated_content)
            
            # 4. Grep
            g_res = claude_grep("calculate_tax", path=tmpdir)
            self.assertIn("sample_service.py", g_res)
            
            # 5. Find
            f_res = claude_find("*.py", path=tmpdir)
            self.assertIn("sample_service.py", f_res)

    # ── 5. Traceback-Guided Code Sandbox & Self-Healing ─────────────────────────
    def test_code_sandbox_execution(self):
        """Test python code sandbox execution and error capture."""
        # Success case
        ok_code = "print(sum([x * 2 for x in range(5)]))"
        ok_res = execute_python_code(ok_code)
        self.assertIn("20", ok_res)
        
        # Error / Traceback capture
        err_code = "raise ValueError('Intentional diagnostic exception for self-healing')"
        err_res = execute_python_code(err_code)
        self.assertIn("ValueError", err_res)
        self.assertIn("Intentional diagnostic exception", err_res)

    # ── 6. Multi-Provider Router Connectivity Matrix ───────────────────────────
    def test_multi_provider_router_matrix(self):
        """Test MultiProviderRouter provider detection and local fallback."""
        status = multi_provider_router.get_active_providers_status()
        self.assertIn("ollama", status, "Local Ollama must be in provider status")
        self.assertIn("groq", status, "Groq must be in provider status")
        self.assertIn("gemini", status, "Gemini must be in provider status")
        self.assertTrue(status["ollama"]["configured"], "Ollama should be configured locally")

    # ── 7. Cybersecurity Reconnaissance Tools ──────────────────────────────────
    def test_cybersecurity_reconnaissance(self):
        """Test active network auditing and secret detection."""
        # 1. Audit active connections
        conn_res = audit_active_connections(filter_state="ALL")
        self.assertIsInstance(conn_res, str)
        self.assertIn("Network Connection Audit", conn_res)
        
        # 2. Hunt exposed secrets
        with tempfile.TemporaryDirectory() as tmpdir:
            secret_file = Path(tmpdir) / "leaked_config.py"
            secret_file.write_text("AWS_SECRET_KEY = 'AKIA1234567890123456'\n", encoding="utf-8")
            hunt_res = hunt_exposed_secrets(target_dir=tmpdir)
            self.assertIn("Potential Exposed Secrets Detected", hunt_res)

    # ── 8. Dynamic Tool Genesis Engine ─────────────────────────────────────────
    def test_dynamic_tool_genesis_registry(self):
        """Test runtime tool genesis loading and listing."""
        gen_tools = tool_genesis.list_generated_tools()
        self.assertIsInstance(gen_tools, list)

    # ── 9. Dual-Process Cognitive Deliberation ──────────────────────────────────
    def test_cognitive_deliberation_classifier(self):
        """Test System 1 Reflex vs System 2 Deliberation classifier."""
        # Complex architectural query -> Deliberation required
        should_delib, reason = thinking_cortex.should_deliberate("Refactor the distributed consensus actor system to prevent deadlock.")
        self.assertTrue(should_delib, "Complex architectural prompt should trigger deliberation")
        
        # Simple casual query -> System 1 fast path
        should_fast, reason_fast = thinking_cortex.should_deliberate("What time is it in Tokyo?")
        self.assertFalse(should_fast, "Simple conversational prompt should use System 1")

    # ── 10. Cognitive Stage Progression ─────────────────────────────────────────
    def test_stage_progression_tracker(self):
        """Verify AETHER is operating at Stage 3 Scholar or Stage 4 Sovereign maturity."""
        from aether.brain.teacher_student_engine import teacher_student_engine
        stage_info = teacher_student_engine.get_current_stage_info()
        curr = stage_info.get("current_stage", "")
        self.assertTrue(any(s in curr for s in ["Scholar", "Stage 4", "Sovereign", "Stage 3"]), f"AETHER must be at advanced cognitive maturity, got {curr}")


if __name__ == "__main__":
    unittest.main()
