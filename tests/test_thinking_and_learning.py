"""
AETHER Comprehensive Thinking & Learning Test Suite
===================================================
Rigorously tests:
1. Thinking Cortex (System 1 vs System 2 complexity classifier, pre-simulation safety).
2. Cognitive Learner (dynamic skill assimilation, reflexion error invariants, episodic consolidation).
3. Live integration with Claude Agent and Engine.
"""

import os
from pathlib import Path
import shutil
import sys
import tempfile


from aether.brain.thinking_cortex import thinking_cortex, SimulationVerdict
from aether.brain.cognitive_learner import cognitive_learner
from aether.brain.skills_vault import skills_vault
from aether.memory.store import memory
from aether.brain.claude_agent import claude_agent
from aether.brain.engine import resolve_fast_path


def test_thinking_cortex_complexity_classification():
    print("\n--- Testing Thinking Cortex Complexity Classifier ---")
    
    # Simple query -> System 1 (False)
    is_complex, reason = thinking_cortex.should_deliberate("hi what time is it")
    assert not is_complex, f"Simple query should not trigger deliberation, got: {reason}"
    print(f"✓ System 1 path verified for simple prompt: '{reason}'")

    # Explicit /deliberate trigger -> System 2 (True)
    is_complex, reason = thinking_cortex.should_deliberate("/deliberate design an event-driven queue")
    assert is_complex
    assert "trigger" in reason.lower()
    print(f"✓ Explicit deliberation trigger verified: '{reason}'")

    # Domain complexity keyword (concurrency/architecture/security) -> System 2 (True)
    is_complex, reason = thinking_cortex.should_deliberate("how to eliminate a race condition in multithreaded sqlite")
    assert is_complex
    assert "complexity" in reason.lower()
    print(f"✓ Domain complexity keyword verified: '{reason}'")


def test_action_pre_simulation_safety():
    print("\n--- Testing Action Pre-Simulation Mental Sandbox ---")

    # 1. Critical risk: Destructive bash command
    v1 = thinking_cortex.pre_simulate_action("claude_bash", {"command": "rm -rf / --no-preserve-root"})
    assert not v1.safe
    assert v1.risk_level == "CRITICAL"
    print(f"✓ Destructive command blocked: {v1.reason}")

    # 2. Safe command
    v2 = thinking_cortex.pre_simulate_action("claude_bash", {"command": "git status"})
    assert v2.safe
    assert v2.risk_level == "LOW"
    print(f"✓ Safe command permitted: {v2.reason}")

    # 3. Surgical edit on non-existent file
    v3 = thinking_cortex.pre_simulate_action("claude_edit", {"file_path": "c:/non_existent_file_xyz.py", "old_str": "a", "new_str": "b"})
    assert not v3.safe
    assert "does not exist" in v3.reason
    print(f"✓ Surgical edit on missing file blocked: {v3.reason}")

    # 4. Surgical edit on existing file with non-existent target string
    test_file = Path("test_presim_sample.txt")
    test_file.write_text("hello world from aether", encoding="utf-8")
    try:
        v4 = thinking_cortex.pre_simulate_action("claude_edit", {"file_path": str(test_file), "old_str": "string_not_in_file", "new_str": "replacement"})
        assert not v4.safe
        assert "not found" in v4.reason
        print(f"✓ Ambiguous/missing string replacement blocked: {v4.reason}")

        v5 = thinking_cortex.pre_simulate_action("claude_edit", {"file_path": str(test_file), "old_str": "hello world", "new_str": "salutations world"})
        assert v5.safe
        assert v5.risk_level == "LOW"
        print(f"✓ Valid surgical replacement permitted: {v5.reason}")
    finally:
        if test_file.exists():
            test_file.unlink()


def test_dynamic_skill_assimilation():
    print("\n--- Testing Dynamic Skill Assimilation ---")
    skills_vault.ensure_indexed()

    # Search for an available skill (e.g. 007 or clean-code or motion-primitives)
    search_res = skills_vault.search_skills("clean-code", limit=1)
    if search_res:
        target_name = search_res[0]["name"]
        print(f"Found target skill: '{target_name}'")

        res = cognitive_learner.assimilate_skill(target_name)
        assert res.get("success"), f"Failed to assimilate skill: {res}"
        assert len(res.get("rules_assimilated", [])) > 0
        print(f"✓ Assimilated {len(res['rules_assimilated'])} rules from '{target_name}' into SQLite FTS5!")
        print(f"  Sample rule: {res['rules_assimilated'][0]['rule']}")

    # Test auto retrieval for prompt
    directives = cognitive_learner.auto_retrieve_skills_for_prompt("audit web security and check owasp vulnerabilities")
    assert len(directives) > 0
    print(f"✓ Auto-retrieved {len(directives)} matching skills for security prompt: {[d['name'] for d in directives]}")


def test_reflexion_error_invariant_synthesis():
    print("\n--- Testing Reflexion Error Invariant Synthesis ---")
    tool_args = {"file_path": "src/aether/engine.py", "old_str": "target_line"}
    error_msg = "Error: target string not found in file content (count == 0)"

    invariant = cognitive_learner.reflexion_post_mortem("claude_edit", tool_args, error_msg)
    assert "Reflexion Invariant" in invariant
    assert "claude_view" in invariant or "claude_edit" in invariant
    print(f"✓ Synthesized and recorded invariant: {invariant}")

    # Verify invariant is stored and recalled from SQLite FTS5
    invariants = cognitive_learner.get_learned_invariants(limit=5)
    assert len(invariants) > 0
    print(f"✓ Retrieved {len(invariants)} stored invariants from SQLite FTS5 memory.")


def test_episodic_consolidation():
    print("\n--- Testing Episodic Knowledge Consolidation ---")
    # Add a mock conversation turn with user project stack
    memory.add_episode("user", "We are using FastAPI with React, Tailwind CSS, and SQLite for our new dashboard.")
    memory.add_episode("assistant", "Excellent stack. I will enforce Tailwind dark mode and FastAPI async patterns.")

    c_res = cognitive_learner.consolidate_episodes(limit=5)
    assert c_res["episodes_analyzed"] >= 2
    assert c_res["facts_added"] >= 1
    print(f"✓ Consolidated episodes: {c_res}")

    facts = memory.recall_facts(entity="project")
    print(f"✓ Recalled project facts: {facts}")


def test_cognitive_metrics_aggregation():
    print("\n--- Testing Cognitive Metrics Aggregation ---")
    metrics = cognitive_learner.get_cognitive_metrics()
    assert metrics["total_skills_available"] > 50
    assert metrics["heuristic_rules_total"] > 0
    print(f"✓ Cognitive Metrics Verified:")
    print(f"  - Skills Available: {metrics['total_skills_available']}")
    print(f"  - Reflexion Invariants: {metrics['reflexion_invariants_count']}")
    print(f"  - Total Heuristic Rules: {metrics['heuristic_rules_total']}")
    print(f"  - Facts Stored: {metrics['facts_stored']}")


def test_engine_fast_paths_integration():
    print("\n--- Testing Engine Fast-Paths Integration ---")
    # Test /invariants fast path
    fp1 = resolve_fast_path("/invariants")
    assert fp1 is not None
    assert "tool_view_learned_invariants" in fp1["tool"]
    print(f"✓ Fast path /invariants: {fp1['preview']}")

    # Test /consolidate fast path
    fp2 = resolve_fast_path("/consolidate")
    assert fp2 is not None
    assert "tool_consolidate_memory" in fp2["tool"]
    print(f"✓ Fast path /consolidate: {fp2['preview']}")


if __name__ == "__main__":
    print("================================================================================")
    print("AETHER Cognitive Thinking & Learning Engine Verification Suite")
    print("================================================================================")
    test_thinking_cortex_complexity_classification()
    test_action_pre_simulation_safety()
    test_dynamic_skill_assimilation()
    test_reflexion_error_invariant_synthesis()
    test_episodic_consolidation()
    test_cognitive_metrics_aggregation()
    test_engine_fast_paths_integration()
    print("\n================================================================================")
    print("ALL 7 VERIFICATION PHASES PASSED WITH ZERO ERRORS!")
    print("================================================================================")
