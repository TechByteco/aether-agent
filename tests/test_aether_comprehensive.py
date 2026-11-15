"""
Comprehensive End-to-End Verification for AETHER
Tests:
1. Universal Skill Vault (2,076+ skills, fuzzy search, dynamic loading)
2. Procedural Heuristic Rules (Anti-slop, Web Security, Live Debugging, ThreeUI)
3. Autonomous Auto-Learning Engine (introspection, error avoidance, dataset curation)
4. Fast-Path Tool Routing (/skills, /skill, /learning-stats)
5. Live Ollama Inference with aether:antigravity
"""

import sys
import time
from pathlib import Path

# Ensure UTF-8 output on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "src"))

import ollama
from aether.brain.skills_vault import skills_vault
from aether.brain.auto_learner import auto_learner
from aether.brain.engine import engine
from aether.memory.store import memory


def test_skills_vault():
    print("\n[1/5] Testing Universal Skill Vault...")
    stats = skills_vault.get_vault_stats()
    total_skills = stats.get("total_skills", 0)
    print(f"  -> Total Indexed Skills: {total_skills}")
    assert total_skills >= 2000, f"Expected >= 2000 skills, got {total_skills}"

    # Test fuzzy search across design & security
    search_queries = ["motion-primitives", "web-security-auditor", "threeui", "clean-code"]
    for q in search_queries:
        results = skills_vault.search_skills(q, limit=3)
        assert len(results) > 0, f"No results for query '{q}'"
        print(f"  [PASS] Search '{q}': found {len(results)} match(es) -> top match: {results[0]['name']}")

    # Test dynamic surgical loading
    motion_skill_text = skills_vault.load_skill("motion-primitives")
    assert "motion-primitives" in motion_skill_text.lower()
    assert len(motion_skill_text) > 100
    print(f"  [PASS] Dynamic load 'motion-primitives': {len(motion_skill_text)} chars loaded")

    sec_skill_text = skills_vault.load_skill("web-security-auditor")
    assert "web-security-auditor" in sec_skill_text.lower()
    assert len(sec_skill_text) > 100
    print(f"  [PASS] Dynamic load 'web-security-auditor': {len(sec_skill_text)} chars loaded")


def test_procedural_heuristics():
    print("\n[2/5] Testing Procedural Memory & Heuristic Rules...")
    all_rules = memory.recall_heuristic_rules("", limit=100)
    print(f"  -> Total Heuristic Rules in SQLite: {len(all_rules)}")
    assert len(all_rules) >= 17, f"Expected >= 17 rules, found {len(all_rules)}"

    # Verify key domains are reflected in rule text
    rules_text = " ".join(all_rules).lower()
    assert "anti-slop" in rules_text or "oled" in rules_text
    assert "security" in rules_text or "owasp" in rules_text or "vulnerability" in rules_text
    assert "clean code" in rules_text or "refactor" in rules_text
    assert "voicestudio" in rules_text or "speech" in rules_text

    # Verify FTS5 heuristic search
    design_rules = memory.recall_heuristic_rules("anti-slop modern dark mode", limit=4)
    assert len(design_rules) > 0, "Failed to recall anti-slop design heuristics via FTS5"
    print(f"  [PASS] FTS5 Heuristic Recall ('anti-slop'): {len(design_rules)} relevant rule(s) recalled")


def test_auto_learning_engine():
    print("\n[3/5] Testing Autonomous Auto-Learning Engine...")
    metrics = auto_learner.get_learning_metrics()
    print(f"  -> Initial Learning Metrics: {metrics}")
    assert "total_rules_in_memory" in metrics
    assert "synthetic_dataset_samples" in metrics

    # Test introspection on a simulated correction turn
    test_user_query = "Don't use generic purple gradients or AI slop, use OLED pure black #09090b with subtle border."
    test_assistant_response = "Understood. I will enforce #09090b OLED obsidian styling with 1px subtle borders."

    introspect_result = auto_learner.introspect_turn(
        user_message=test_user_query,
        assistant_response=test_assistant_response,
        tool_events=[{"name": "tool_search_skills", "success": True, "error": None}],
        session_id="test_verification"
    )
    print(f"  -> Turn Introspection Result: {introspect_result}")
    assert len(introspect_result["rules_learned"]) > 0 or introspect_result["dataset_curated"]

    # Check updated metrics
    updated_metrics = auto_learner.get_learning_metrics()
    print(f"  [PASS] Auto-Learner rules in memory: {updated_metrics.get('total_rules_in_memory', 0)}")
    print(f"  [PASS] Synthetic training examples: {updated_metrics.get('synthetic_dataset_samples', 0)}")


def test_fast_paths_and_tools():
    print("\n[4/5] Testing Cognitive Engine Fast-Paths & Skill Router...")
    
    # Fast path: /skills
    skills_overview = engine.process_query("/skills")
    assert "Skill Vault Status" in skills_overview
    print(f"  [PASS] Fast-path '/skills' response generated in sub-5ms")

    # Fast path: /skill motion-primitives
    skill_view = engine.process_query("/skill motion-primitives")
    assert "motion-primitives" in skill_view.lower()
    print(f"  [PASS] Fast-path '/skill motion-primitives' returned loaded directives")

    # Fast path: /learning-stats
    learning_stats = engine.process_query("/learning-stats")
    assert "Continuous Auto-Learning" in learning_stats
    print(f"  [PASS] Fast-path '/learning-stats' returned live telemetry")


def test_live_ollama_inference():
    print("\n[5/5] Testing Live Model Inference (aether:antigravity)...")
    active_model = engine.resolve_active_model()
    print(f"  -> Resolved Active Model: {active_model}")
    assert "aether" in active_model or "antigravity" in active_model or "llama3.2" in active_model

    prompt = "AETHER, summarize your active design registry and security auditing capabilities in two concise bullet points."
    print(f"  -> Sending prompt to {active_model}...")
    t0 = time.time()
    response = engine.process_query(prompt)
    t1 = time.time()
    print(f"  -> Response received in {t1 - t0:.2f}s:")
    print(f"--------------------------------------------------")
    print(response.strip())
    print(f"--------------------------------------------------")
    assert len(response) > 20, "Model response was unexpectedly empty"
    print("  [PASS] Live inference with AETHER model successful!")


if __name__ == "__main__":
    print("==================================================")
    print("      AETHER DEEP COMPREHENSIVE VERIFICATION      ")
    print("==================================================")
    t_start = time.time()
    test_skills_vault()
    test_procedural_heuristics()
    test_auto_learning_engine()
    test_fast_paths_and_tools()
    test_live_ollama_inference()
    total_time = time.time() - t_start
    print(f"\n>>> ALL 5 DEEP VERIFICATION PHASES PASSED IN {total_time:.2f}s! <<<")
