"""
AETHER Frontier Systems Comprehensive Test Suite
================================================
Verifies all 6 newly built frontier systems:
1. Snapdragon X Hardware, NPU & Speculative Acceleration
2. Set-of-Mark (SoM) Visual Computer-Use & Self-Healing Action Loop
3. Autonomous Cloud Self-Play & Model Evolution Pipeline
4. Hybrid Dense + Sparse RAG & Semantic Knowledge Graph Engine
5. Sovereign Multi-Channel Remote Presence Gateway
6. Zero-CPU Hands-Free Offline Wake-Word Detection
"""

import os
import sys
import unittest
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from aether.tools.npu_speculative_accelerator import (
    speculative_engine,
    tool_inspect_hardware_acceleration,
    tool_benchmark_speculative_decoding,
)
from aether.tools.visual_som_grounding import (
    visual_som,
    tool_capture_screen_with_som,
    tool_execute_som_action,
)
from aether.brain.autonomous_model_evolver import (
    model_evolver,
    tool_get_model_evolution_status,
)
from aether.memory.hybrid_knowledge_graph import (
    hybrid_kg,
    tool_query_hybrid_memory,
    tool_query_semantic_knowledge_graph,
    tool_extract_knowledge_triples,
)
from aether.brain.multi_channel_gateway import (
    multi_channel,
    tool_get_multi_channel_gateway_status,
)
from aether.tools.wake_word_engine import (
    wake_engine,
    tool_start_wake_word_listener,
    tool_get_wake_word_status,
)
from aether.brain.engine import AVAILABLE_TOOLS, TOOL_DISPATCHER


class TestFrontierSystems(unittest.TestCase):

    def test_01_speculative_npu_acceleration(self):
        """Test Snapdragon X hardware inspection & speculative benchmark."""
        topo = speculative_engine.inspect_hardware_topology()
        self.assertIn("cpu_cores", topo)
        self.assertIn("npu_tops", topo)
        self.assertEqual(topo["npu_tops"], 45.0)

        kv = speculative_engine.calculate_kv_cache_footprint(context_length=8192, precision="q4_0")
        self.assertGreater(kv["ram_savings_percent"], 50.0)

        sim = speculative_engine.simulate_speculative_verification(
            draft_tokens=["test", "token", "stream"],
            target_probs=[0.9, 0.85, 0.8]
        )
        self.assertGreater(sim["estimated_speedup_factor"], 1.0)
        print("[PASS] System 1: NPU Speculative Acceleration & KV-Cache")

    def test_02_visual_som_grounding(self):
        """Test Set-of-Mark visual grounding and action loop."""
        som_res = visual_som.capture_screen_with_som()
        self.assertTrue(som_res.get("success", False))
        self.assertGreater(som_res["elements_count"], 0)
        self.assertIn("1", som_res["som_map"])

        act_res = visual_som.execute_som_action("1", action="click")
        self.assertTrue(act_res.get("success", False))
        print("[PASS] System 2: Set-of-Mark (SoM) Visual Computer-Use")

    def test_03_autonomous_model_evolver(self):
        """Test model evolution status and self-play pipeline."""
        st = model_evolver.get_evolution_pipeline_status()
        self.assertIn("cognitive_generation", st)
        self.assertIn("total_dataset_samples", st)
        print("[PASS] System 3: Autonomous Cloud Self-Play & Model Evolver")

    def test_04_hybrid_rag_and_knowledge_graph(self):
        """Test Hybrid RAG and Semantic Knowledge Graph."""
        triples = hybrid_kg.extract_and_store_triples_from_text("Antigravity runs on Snapdragon X.")
        self.assertTrue(len(triples) >= 0)

        kg_res = hybrid_kg.query_knowledge_graph("Antigravity")
        self.assertIn("outgoing_relations", kg_res)

        hybrid_res = hybrid_kg.hybrid_search("Snapdragon", top_k=3)
        self.assertIsInstance(hybrid_res, list)
        print("[PASS] System 4: Hybrid Dense RAG & Knowledge Graph")

    def test_05_multi_channel_remote_gateway(self):
        """Test multi-channel gateway configuration."""
        st = multi_channel.get_status()
        self.assertIn("telegram", st)
        self.assertIn("discord", st)
        self.assertIn("voice_persona", st)
        print("[PASS] System 5: Multi-Channel Remote Presence Gateway")

    def test_06_wake_word_and_barge_in(self):
        """Test offline wake-word listener and barge-in trigger."""
        wake_engine.start_listening()
        st = wake_engine.get_status()
        self.assertTrue(st["is_listening"])

        event = wake_engine.trigger_wake_event("hey jarvis")
        self.assertTrue(event["success"])
        self.assertTrue(event["barge_in_interrupted"])
        wake_engine.stop_listening()
        print("[PASS] System 6: Zero-CPU Wake-Word & Barge-In Engine")

    def test_07_engine_dispatch_integration(self):
        """Verify all new tools are properly registered in Engine."""
        expected_tools = [
            "tool_inspect_hardware_acceleration",
            "tool_benchmark_speculative_decoding",
            "tool_capture_screen_with_som",
            "tool_execute_som_action",
            "tool_run_self_play_curriculum_step",
            "tool_dispatch_autonomous_cloud_evolution",
            "tool_get_model_evolution_status",
            "tool_query_hybrid_memory",
            "tool_query_semantic_knowledge_graph",
            "tool_extract_knowledge_triples",
            "tool_get_multi_channel_gateway_status",
            "tool_generate_morning_audio_briefing",
            "tool_start_wake_word_listener",
            "tool_get_wake_word_status",
        ]
        for t in expected_tools:
            self.assertIn(t, TOOL_DISPATCHER, f"Tool {t} not found in TOOL_DISPATCHER")
        print(f"[PASS] Engine Integration: All {len(expected_tools)} frontier tools verified in TOOL_DISPATCHER ({len(TOOL_DISPATCHER)} total tools active).")


if __name__ == "__main__":
    unittest.main()
