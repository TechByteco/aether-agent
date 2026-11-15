"""
Test Suite for LEON Autonomous Venture OS & Sub-Agent Swarm Integration in AETHER.
Verifies:
1. Venture creation and stage transitions.
2. 6 Sub-agent role directives and swarm dispatching.
3. Constitutional training dataset ingestion into AETHER unified dataset.
4. Tool dispatcher registration in cognitive engine.
"""

import os
import sys
import unittest
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from aether.brain.leon_venture_os import (
    leon_os,
    VentureStage,
    SubAgentRole,
    SUBAGENT_DIRECTIVES,
    tool_leon_create_venture,
    tool_leon_dispatch_subagent_swarm,
    tool_train_leon_venture_model,
    tool_leon_get_venture_ledger,
)
from aether.brain.engine import TOOL_DISPATCHER, AVAILABLE_TOOLS, resolve_fast_path


class TestLeonIntegration(unittest.TestCase):

    def test_01_subagent_directives(self):
        """Verify all 6 subagent roles have concrete system directives."""
        self.assertEqual(len(SUBAGENT_DIRECTIVES), 6)
        roles = [
            SubAgentRole.OPPORTUNITY_DISCOVERY,
            SubAgentRole.UNIT_ECONOMICS,
            SubAgentRole.VALIDATION_EXPERIMENT,
            SubAgentRole.PRODUCT_ARCHITECT,
            SubAgentRole.GROWTH_DISTRIBUTION,
            SubAgentRole.TREASURY_AUDITOR,
        ]
        for r in roles:
            self.assertIn(r, SUBAGENT_DIRECTIVES)
            self.assertIn("title", SUBAGENT_DIRECTIVES[r])
            self.assertIn("system_prompt", SUBAGENT_DIRECTIVES[r])
            self.assertGreater(len(SUBAGENT_DIRECTIVES[r]["system_prompt"]), 20)

    def test_02_venture_lifecycle(self):
        """Verify venture creation, ledger recording, and state persistence."""
        v = leon_os.create_venture(
            name="MicroSaaS Analytics",
            problem="Indie hackers lack real-time privacy-friendly analytics",
            target_users=["indie hackers", "solopreneurs"],
            mission="Build a $0-cost open-source analytics dashboard",
            budget_ceiling=0.0
        )
        self.assertEqual(v["name"], "MicroSaaS Analytics")
        self.assertEqual(v["stage"], "idea")
        self.assertEqual(v["budget_ceiling"], 0.0)

        ledger_str = tool_leon_get_venture_ledger()
        self.assertIn("MicroSaaS Analytics", ledger_str)

    def test_03_subagent_swarm_dispatch(self):
        """Verify subagent swarm execution and synthesis across 6 roles."""
        swarm_report = tool_leon_dispatch_subagent_swarm(
            venture_name="MicroSaaS Analytics",
            task_objective="Validate demand and architect MVP for privacy analytics widget"
        )
        self.assertIn("LEON Sub-Agent Swarm Report", swarm_report)
        self.assertIn("Market Opportunity Discovery Agent", swarm_report)
        self.assertIn("Unit Economics & Pricing Strategist", swarm_report)
        self.assertIn("Product & Micro-Tool Architect", swarm_report)
        self.assertIn("Zero-Cost Validation Experimenter", swarm_report)
        self.assertIn("Growth & Organic Distribution Agent", swarm_report)
        self.assertIn("Treasury & Metrics Auditor", swarm_report)

    def test_04_dataset_ingestion(self):
        """Verify ingestion of LEON's constitutional dataset."""
        res = leon_os.ingest_leon_training_dataset()
        self.assertIn("samples_imported", res)
        self.assertGreaterEqual(res["samples_imported"], 0)
        self.assertTrue(os.path.exists(res["target_unified_dataset"]))

    def test_05_engine_tool_registration(self):
        """Verify that all LEON tools are in TOOL_DISPATCHER and AVAILABLE_TOOLS."""
        leon_tool_names = [
            "tool_leon_create_venture",
            "tool_leon_dispatch_subagent_swarm",
            "tool_train_leon_venture_model",
            "tool_leon_get_venture_ledger",
        ]
        for name in leon_tool_names:
            self.assertIn(name, TOOL_DISPATCHER, f"Missing {name} in TOOL_DISPATCHER")

        avail_names = [fn.__name__ for fn in AVAILABLE_TOOLS]
        for name in leon_tool_names:
            self.assertIn(name, avail_names, f"Missing {name} in AVAILABLE_TOOLS")

    def test_06_fast_path_routing(self):
        """Verify fast-path instant resolution for /leon and /train-leon commands."""
        res = resolve_fast_path("/leon")
        self.assertIsNotNone(res)
        self.assertEqual(res["tool"], "tool_leon_get_venture_ledger")

        res_train = resolve_fast_path("/train-leon")
        self.assertIsNotNone(res_train)
        self.assertEqual(res_train["tool"], "tool_train_leon_venture_model")

    def test_07_leon_in_continuous_training_loops(self):
        """Verify LEON is integrated into Curriculum, Self-Play RLAIF, and Evolution loops."""
        from aether.brain.curriculum_learner import FRONTIER_DISCIPLINES
        from aether.brain.self_play_rlaif_engine import self_play_engine
        from aether.brain.evolution import FRONTIER_TOPICS
        from aether.brain.autonomous_model_evolver import model_evolver, EVOLUTION_TOPICS

        # 1. Curriculum discipline verification
        self.assertIn("leon_venture_builder", FRONTIER_DISCIPLINES)
        self.assertIn("title", FRONTIER_DISCIPLINES["leon_venture_builder"])

        # 2. Self-play challenge generation
        challenge = self_play_engine.generate_challenge("leon_venture_builder")
        self.assertIn("starter_code", challenge)
        self.assertIn("score_leon_action", challenge["starter_code"])

        # 3. Evolution topics verification
        self.assertTrue(any("leon" in t.lower() for t in FRONTIER_TOPICS))
        self.assertIn("leon_venture_discovery", EVOLUTION_TOPICS)

        # 4. Evolver self-play pair generation
        pair = model_evolver.generate_synthetic_self_play_pair(topic="leon_venture_discovery")
        self.assertEqual(pair["topic"], "leon_venture_discovery")
        self.assertTrue(os.path.exists(model_evolver.unified_dataset))


if __name__ == "__main__":
    unittest.main()

