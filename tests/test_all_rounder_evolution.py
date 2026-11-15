"""
AETHER All-Rounder Skill Genesis & Perpetual Evolution Test Suite
=================================================================
Verifies dynamic skill creation, curriculum dataset formatting, and
perpetual domain evolution cycles.
"""

from pathlib import Path
import tempfile
import unittest

from aether.brain.skill_genesis_factory import SkillGenesisFactory, ALL_ROUNDER_DOMAINS
from aether.brain.autonomous_curriculum_synthesizer import AutonomousCurriculumSynthesizer
from aether.brain.perpetual_training_dispatcher import PerpetualTrainingDispatcher


class TestAllRounderEvolutionSuite(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.tmpdir.name)
        self.factory = SkillGenesisFactory(workspace_root=self.workspace)
        self.synthesizer = AutonomousCurriculumSynthesizer(workspace_root=self.workspace)
        self.dispatcher = PerpetualTrainingDispatcher(workspace_root=self.workspace)

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_skill_synthesis_and_ast_validation(self):
        """Verify dynamic skill synthesis across domains with clean AST parsing."""
        success, skill, msg = self.factory.synthesize_skill_for_domain(
            "network_forensics_and_security",
            "Perform live packet capture and audit open ports."
        )
        self.assertTrue(success)
        self.assertIsNotNone(skill)
        self.assertEqual(skill.domain, "network_forensics_and_security")
        self.assertTrue(skill.ast_analysis["is_valid_syntax"])
        self.assertEqual(len(skill.ast_analysis["security_warnings"]), 0)

    def test_curriculum_synthesis(self):
        """Verify generation of valid ChatML dataset files for fine-tuning."""
        path = self.synthesizer.synthesize_curriculum_for_domain("full_stack_web_and_api", num_samples=5)
        self.assertTrue(path.exists())
        self.assertGreater(path.stat().st_size, 100)

    def test_perpetual_dispatcher_pulse(self):
        """Verify end-to-end evolution pulse and domain advancement."""
        initial_dom = self.dispatcher.get_current_domain()
        pulse = self.dispatcher.execute_evolution_pulse()
        self.assertEqual(pulse["status"], "success")
        self.assertEqual(pulse["domain_processed"], initial_dom)
        self.assertNotEqual(pulse["next_domain"], initial_dom)


if __name__ == "__main__":
    unittest.main()
