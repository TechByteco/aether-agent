"""
AETHER Infinite Evolution Orchestrator & Situation Deliberation Test Suite
==========================================================================
Tests the 8-stage infinite training lifecycle, situation assessment heuristics,
and dynamic deliberation routing.
"""

from pathlib import Path
import tempfile
import unittest

from aether.brain.infinite_evolution_orchestrator import (
    InfiniteEvolutionOrchestrator,
    CurriculumStage,
    infinite_orchestrator,
)
from aether.brain.thinking_cortex import thinking_cortex


class TestInfiniteEvolutionOrchestrator(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.tmpdir.name)
        self.orchestrator = InfiniteEvolutionOrchestrator(workspace_root=self.workspace)

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_stage_sequence_and_advancement(self):
        """Verify that the infinite loop cycles through all 8 frontier stages correctly."""
        initial_stage = self.orchestrator.get_current_stage()
        self.assertEqual(initial_stage, CurriculumStage.STAGE_1_COGNITIVE_INVARIANTS)

        for expected_stage in list(CurriculumStage)[1:]:
            next_stage = self.orchestrator.advance_to_next_stage()
            self.assertEqual(next_stage, expected_stage)

        # 8th advance should wrap around to stage 1 (infinite loop)
        wrap_stage = self.orchestrator.advance_to_next_stage()
        self.assertEqual(wrap_stage, CurriculumStage.STAGE_1_COGNITIVE_INVARIANTS)
        self.assertEqual(self.orchestrator.total_completed_stages, 8)

    def test_situation_assessment_heuristics(self):
        """Verify autonomous situation detection and proactive action derivation."""
        # 1. Cyber defense
        cyber_assess = self.orchestrator.assess_situation("Audit network for SSRF vulnerabilities and leaked AWS keys.")
        self.assertEqual(cyber_assess.situation_type, "CYBER_DEFENSE_AUDIT")
        self.assertEqual(cyber_assess.urgency_level, "HIGH")
        self.assertEqual(cyber_assess.recommended_model_tier, "SWARM_DEBATE")
        self.assertGreater(len(cyber_assess.deliberated_actions), 0)

        # 2. Swarm mission
        swarm_assess = self.orchestrator.assess_situation("Architect a multi-agent consensus bus with adversarial review.")
        self.assertEqual(swarm_assess.situation_type, "MULTI_AGENT_SWARM_MISSION")
        self.assertEqual(swarm_assess.recommended_model_tier, "SWARM_DEBATE")

        # 3. Code crash repair
        crash_assess = self.orchestrator.assess_situation("SyntaxError on line 42: unexpected EOF in parser loop.")
        self.assertEqual(crash_assess.situation_type, "AUTONOMOUS_INCIDENT_REPAIR")
        self.assertEqual(crash_assess.urgency_level, "HIGH")

        # 4. Standard cognitive
        std_assess = self.orchestrator.assess_situation("What is the speed of light in vacuum?")
        self.assertEqual(std_assess.situation_type, "STANDARD_COGNITIVE_TASK")
        self.assertEqual(std_assess.recommended_model_tier, "EDGE_LOCAL")

    def test_model_capability_evaluation(self):
        """Verify model evaluation recording and history tracking."""
        eval_res = self.orchestrator.evaluate_model_capabilities("aether:v3")
        self.assertEqual(eval_res["status"], "FRONTIER_CERTIFIED")
        self.assertGreaterEqual(eval_res["overall_frontier_index"], 90.0)

        status = self.orchestrator.get_status()
        self.assertTrue(status["infinite_loop_active"])
        self.assertIsNotNone(status["latest_benchmark"])

    def test_thinking_cortex_situation_routing(self):
        """Verify thinking_cortex integrates situation assessment and deliberation."""
        res = thinking_cortex.deliberate_situation_and_act("Search episodic memory for the database credentials.")
        self.assertIn("assessment", res)
        self.assertEqual(res["assessment"].situation_type, "EPISODIC_MEMORY_RETRIEVAL")


if __name__ == "__main__":
    unittest.main()
