"""
Unit Tests for AETHER Self-Play RLAIF & Autonomous Curriculum Synthesizer
"""

import unittest
from pathlib import Path

from aether.brain.self_play_rlaif_engine import self_play_engine, SelfPlayTrace
from aether.brain.autonomous_curriculum_synthesizer import curriculum_synthesizer
from aether.brain.perpetual_training_dispatcher import perpetual_dispatcher
from aether.brain.skill_genesis_factory import ALL_ROUNDER_DOMAINS


class TestSelfPlayRLAIFSuite(unittest.TestCase):
    def test_curriculum_synthesis(self):
        core_p, frontier_p = curriculum_synthesizer.synthesize_dual_gpu_curricula()
        self.assertTrue(core_p.exists())
        self.assertTrue(frontier_p.exists())
        self.assertGreater(core_p.stat().st_size, 0)
        self.assertGreater(frontier_p.stat().st_size, 0)

    def test_self_play_cycle_execution(self):
        trace = self_play_engine.execute_self_play_cycle("full_stack_web_and_api")
        self.assertIsInstance(trace, SelfPlayTrace)
        self.assertEqual(trace.domain, "full_stack_web_and_api")
        self.assertTrue(trace.ast_valid)
        self.assertTrue(trace.execution_success)
        self.assertGreaterEqual(trace.reward_score, 0.85)

    def test_rlaif_telemetry(self):
        telemetry = self_play_engine.get_telemetry()
        self.assertIn("total_cycles", telemetry)
        self.assertIn("elite_traces_count", telemetry)
        self.assertIn("average_reward", telemetry)
        self.assertGreater(telemetry["total_cycles"], 0)

    def test_perpetual_dispatcher_evolution_pulse(self):
        pulse = perpetual_dispatcher.execute_evolution_pulse()
        self.assertEqual(pulse.get("status"), "success")
        self.assertIn("domain_processed", pulse)
        self.assertIn("self_play_trace_id", pulse)
        self.assertIn("benchmark_index", pulse)


if __name__ == "__main__":
    unittest.main()
