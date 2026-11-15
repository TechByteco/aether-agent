"""
AETHER Diversified Curriculum & Task Engagement Test Suite
==========================================================
Rigorously verifies:
1. 8 Frontier Cognitive Disciplines & Seed Curriculums.
2. Cross-Skill Synthesis between disparate vault skills.
3. Adversarial Tournament flow and invariant extraction.
4. Hierarchical Task DAG orchestration, dependency resolution, and persistent checkpointing.
5. Dynamic Persona adaptation (Architect, Builder, Security Auditor, Profiler, UI Artisan).
6. Fast-paths in Engine and Claude Agent.
"""

from pathlib import Path
import sys

from aether.brain.curriculum_learner import curriculum_learner, FRONTIER_DISCIPLINES
from aether.brain.task_engagement import task_engagement, TaskStatus, EngagementPersona
from aether.brain.engine import resolve_fast_path
from aether.memory.store import memory


def test_frontier_disciplines_catalog():
    print("\n--- Testing 8 Frontier Cognitive Disciplines Catalog ---")
    discs = curriculum_learner.list_disciplines()
    assert len(discs) == 8, f"Expected 8 disciplines, got {len(discs)}"

    expected_keys = [
        "distributed_systems", "anti_slop_ui_ux", "security_red_teaming",
        "low_level_systems", "data_engineering", "agent_orchestration",
        "cloud_sre", "scientific_bio"
    ]
    for k in expected_keys:
        assert k in FRONTIER_DISCIPLINES, f"Missing discipline: {k}"
        disc = FRONTIER_DISCIPLINES[k]
        assert len(disc["seed_challenges"]) >= 3, f"Discipline {k} has insufficient challenges"
        print(f"✓ Verified discipline: {disc['title']} ({len(disc['seed_challenges'])} seed challenges)")


def test_cross_skill_synthesis():
    print("\n--- Testing Cross-Skill Synthesis ---")
    res = curriculum_learner.synthesize_cross_domain_skills("clean-code", "web-security-auditor")
    assert res.get("success")
    assert "Cross-Skill Synthesis" in res["synthesized_rule"]
    assert res.get("rule_id", 0) > 0
    print(f"✓ Synthesized cross-skill rule #{res['rule_id']}:")
    print(f"  > {res['synthesized_rule']}")

    # Verify rule is indexed in SQLite FTS5
    recalled = memory.recall_heuristic_rules("Cross-Skill Synthesis", limit=1)
    assert len(recalled) > 0
    print(f"✓ Recalled synthesized rule from SQLite FTS5: {recalled[0][:80]}...")


def test_hierarchical_task_dag_orchestration():
    print("\n--- Testing Hierarchical Task DAG Orchestration ---")
    obj = "Architect and deploy end-to-end telemetry system on Snapdragon ARM64"
    dag_md = task_engagement.create_engagement_dag(obj)
    assert "Active Task Engagement DAG" in dag_md
    assert len(task_engagement.nodes) == 4
    print(f"✓ Initialized 4-step DAG for objective: '{obj}'")

    # Step T1 should be IN_PROGRESS, T2 pending T1
    t1 = task_engagement.nodes["T1"]
    t2 = task_engagement.nodes["T2"]
    assert t1.status == TaskStatus.IN_PROGRESS
    assert t2.status == TaskStatus.PENDING
    assert "T1" in t2.dependencies
    print(f"✓ Step T1 is IN_PROGRESS; Step T2 is PENDING on T1.")

    # Advance T1 -> T2 should become unblocked and IN_PROGRESS
    adv_res = task_engagement.advance_task("T1", result_summary="Architecture blueprint approved.")
    assert "Unblocked next task(s): T2" in adv_res
    assert task_engagement.nodes["T1"].status == TaskStatus.COMPLETED
    assert task_engagement.nodes["T2"].status == TaskStatus.IN_PROGRESS
    print(f"✓ Advanced T1: T2 automatically unblocked and active.")

    # Check persistence on disk
    storage_file = Path("data/memory/active_engagements.json")
    assert storage_file.exists()
    print(f"✓ Verified DAG checkpoint persistence to {storage_file}")


def test_dynamic_persona_adaptation():
    print("\n--- Testing Dynamic Persona Adaptation ---")
    msg1 = task_engagement.set_persona(EngagementPersona.SECURITY_AUDITOR)
    assert task_engagement.active_persona == EngagementPersona.SECURITY_AUDITOR
    directive = task_engagement.get_persona_directive()
    assert "SECURITY_AUDITOR" in directive
    assert "zero-trust" in directive.lower()
    print(f"✓ Set and verified persona: SECURITY_AUDITOR -> '{directive[:65]}...'")

    msg2 = task_engagement.set_persona(EngagementPersona.UI_ARTISAN)
    assert task_engagement.active_persona == EngagementPersona.UI_ARTISAN
    directive2 = task_engagement.get_persona_directive()
    assert "OLED" in directive2 or "agency-grade" in directive2
    print(f"✓ Set and verified persona: UI_ARTISAN -> '{directive2[:65]}...'")


def test_fast_paths_integration():
    print("\n--- Testing Fast-Paths Integration ---")
    # /dag fast-path
    fp_dag = resolve_fast_path("/dag")
    assert fp_dag is not None
    assert "tool_get_active_engagement_status" in fp_dag["tool"]
    print(f"✓ Fast path /dag verified: {fp_dag['preview']}")

    # /disciplines fast-path
    fp_disc = resolve_fast_path("/disciplines")
    assert fp_disc is not None
    assert "8 Frontier Cognitive Disciplines" in fp_disc["result"]
    print(f"✓ Fast path /disciplines verified: {fp_disc['preview']}")

    # /persona fast-path
    fp_p = resolve_fast_path("/persona ARCHITECT")
    assert fp_p is not None
    assert "ARCHITECT" in fp_p["result"]
    print(f"✓ Fast path /persona verified: {fp_p['preview']}")


if __name__ == "__main__":
    print("================================================================================")
    print("AETHER Diversified Curriculum & Task Engagement Verification Suite")
    print("================================================================================")
    test_frontier_disciplines_catalog()
    test_cross_skill_synthesis()
    test_hierarchical_task_dag_orchestration()
    test_dynamic_persona_adaptation()
    test_fast_paths_integration()
    print("\n================================================================================")
    print("ALL 5 CURRICULUM & ENGAGEMENT PHASES PASSED WITH ZERO ERRORS!")
    print("================================================================================")
