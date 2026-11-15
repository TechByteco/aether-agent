"""
AETHER Engineer & Entrepreneur Executive Companion Test Suite
==============================================================
Verifies venture unit economics modeling, cap table dilution math,
technical PRD synthesis, investor pitch memos, and executive focus orchestration.
"""

from pathlib import Path
import tempfile
import unittest

from aether.tools.entrepreneur import (
    tool_model_venture_unit_economics,
    tool_simulate_cap_table_and_dilution,
    tool_synthesize_technical_prd,
    tool_synthesize_investor_memo_and_pitch,
    tool_orchestrate_executive_sprint,
)
from aether.brain.skill_genesis_factory import SkillGenesisFactory, ALL_ROUNDER_DOMAINS
from aether.brain.self_play_rlaif_engine import SelfPlayRLAIFEngine


class TestEntrepreneurCompanionSuite(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.tmpdir.name)
        self.factory = SkillGenesisFactory(workspace_root=self.workspace)
        self.rlaif_engine = SelfPlayRLAIFEngine(workspace_root=self.workspace)

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_venture_unit_economics_modeling(self):
        """Test SaaS/AI unit economics, payback periods, and runway calculations."""
        res = tool_model_venture_unit_economics(
            cac=500.0,
            arpu=100.0,
            gross_margin_pct=80.0,
            churn_rate_monthly=2.0,
            monthly_burn=20000.0,
            cash_balance=240000.0,
        )
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["health_rating"], "ELITE")
        self.assertEqual(res["metrics"]["runway_months"], 12.0)
        self.assertGreater(res["metrics"]["ltv_to_cac_ratio"], 3.0)
        self.assertLessEqual(res["metrics"]["cac_payback_months"], 12.0)

    def test_cap_table_dilution_simulation(self):
        """Test post-money SAFE conversion and founder retention breakdown."""
        founders = {"Founder_A": 60.0, "Founder_B": 40.0}
        res = tool_simulate_cap_table_and_dilution(
            founders=founders,
            existing_shares=10_000_000,
            new_investment_usd=1_500_000.0,
            post_money_valuation_usd=10_000_000.0,
            unallocated_option_pool_pct=10.0,
        )
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["round_summary"]["investor_equity_pct"], 15.0)
        self.assertEqual(res["round_summary"]["total_founder_retention_pct"], 75.0)
        # Founder A: 60% of 75% = 45%
        self.assertEqual(res["founder_equity_breakdown"]["Founder_A"]["post_round_ownership_pct"], 45.0)

    def test_technical_prd_synthesis(self):
        """Test production PRD document creation."""
        res = tool_synthesize_technical_prd(
            product_title="AETHER Sovereign Autonomous Copilot",
            target_users="Engineers and Startup Founders",
            core_value_prop="Zero-latency on-device AI pairing with autonomous cloud GPU training.",
            key_features=["AST Code Sandbox", "DirectML NPU Accelerator", "FTS5 Memory Store"],
        )
        self.assertEqual(res["status"], "success")
        self.assertIn("# Product Requirements Document", res["prd_content"])
        self.assertEqual(res["total_features"], 3)

    def test_investor_memo_and_pitch_synthesis(self):
        """Test institutional pitch memo formulation."""
        res = tool_synthesize_investor_memo_and_pitch(
            company_name="AETHER Labs",
            problem="Developers struggle with context-fragmented, high-latency cloud-only AI assistants.",
            solution="On-device Sovereign AI with persistent episodic conscious memory and continuous RLAIF self-play.",
            target_market="30M+ Global Software Engineers and Deep-Tech Founders",
            business_model="Tiered open-core with premium sovereign hardware modules and enterprise cloud swarm orchestration.",
            traction="40/40 test suite verified, dual-T4 GPU training completed, 1.30s local inference latency.",
            ask_amount_usd=2_500_000.0,
        )
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["company_name"], "AETHER Labs")
        self.assertIn("$2,500,000.00", res["investment_memo"])

    def test_executive_sprint_orchestration(self):
        """Test founder Eisenhower prioritization and blocker elimination."""
        goals = ["Complete DirectML NPU Kernel", "Finalize Series A Pitch Deck", "Review Q3 Cap Table"]
        blockers = ["Waiting on legal counsel for SAFE terms"]
        res = tool_orchestrate_executive_sprint(goals=goals, blockers=blockers, available_hours_per_week=50.0)
        self.assertEqual(res["status"], "success")
        self.assertEqual(len(res["prioritized_goals"]), 3)
        self.assertEqual(res["prioritized_goals"][0]["priority"], "P0 (Critical Path)")

    def test_entrepreneur_domain_skill_genesis(self):
        """Verify dynamic skill generation for entrepreneur domains."""
        self.assertIn("venture_modeling_and_unit_economics", ALL_ROUNDER_DOMAINS)
        ok, skill, msg = self.factory.synthesize_skill_for_domain(
            "venture_modeling_and_unit_economics",
            "Autonomous SaaS & AI unit economics modeler and runway predictor."
        )
        self.assertTrue(ok)
        self.assertIsNotNone(skill)
        self.assertTrue(skill.ast_analysis["is_valid_syntax"])

    def test_entrepreneur_self_play_rlaif_challenge(self):
        """Verify that self-play RLAIF engine can synthesize verified traces for entrepreneur domains."""
        trace = self.rlaif_engine.execute_self_play_cycle(domain="venture_modeling_and_unit_economics")
        self.assertIsNotNone(trace)
        self.assertTrue(trace.ast_valid)
        self.assertTrue(trace.execution_success)
        self.assertGreaterEqual(trace.reward_score, 0.85)


if __name__ == "__main__":
    unittest.main()
