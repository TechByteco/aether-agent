import unittest
from pathlib import Path

from aether.brain.teacher_student_engine import (
    CognitiveStage,
    EvaluationVerdict,
    TeacherStudentOrchestrator,
    teacher_student_engine,
)


class TestTeacherStudentEngine(unittest.TestCase):
    def test_stage_initialization(self):
        state = teacher_student_engine.get_current_stage_info()
        self.assertIn("current_stage", state)
        self.assertIn("stage_progress", state)
        self.assertIn("average_score", state)

    def test_challenge_generation(self):
        challenge = teacher_student_engine.synthesize_teacher_challenge(
            stage=CognitiveStage.STAGE_1_CHILD,
            topic_override="Inspect system vitals with tool_system_vitals",
        )
        self.assertTrue("title" in challenge or "scenario" in challenge)

    def test_evaluation_and_dataset_buffering(self):
        challenge = {
            "title": "Test JSON Tool Calling",
            "scenario": "Audit open network ports on the machine.",
            "rubric": "Invoke tool_audit_active_connections with valid filter_state.",
        }
        mock_attempt = '```json\n{"tool": "tool_audit_active_connections", "args": {"filter_state": "LISTEN"}}\n```'

        verdict = teacher_student_engine.evaluate_student_attempt(
            challenge=challenge,
            student_attempt=mock_attempt,
            stage=CognitiveStage.STAGE_1_CHILD,
        )
        self.assertGreaterEqual(verdict.score, 1)
        self.assertEqual(verdict.stage, CognitiveStage.STAGE_1_CHILD)

        # Check that datasets were appended
        sft_file = teacher_student_engine.sft_dataset_file
        self.assertTrue(sft_file.exists())
        self.assertGreater(sft_file.stat().st_size, 0)


if __name__ == "__main__":
    unittest.main()

