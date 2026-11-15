"""
Automated Verification Suite for AETHER
Tests memory persistence, hardware sentry, open knowledge tools, and cognitive engine.
"""

import sys
from pathlib import Path

# Ensure UTF-8 output on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from aether.tools.guardrails import get_system_vitals, format_vitals_summary
from aether.memory.store import memory
from aether.memory.persona import persona
from aether.tools.open_knowledge import search_wikipedia, search_arxiv, search_web
from aether.brain.engine import engine


def test_hardware_sentry():
    print("[1/5] Testing Hardware Sentry...")
    vitals = get_system_vitals()
    assert "ram_used_gb" in vitals
    assert "ram_percent" in vitals
    assert "cpu_percent" in vitals
    summary = format_vitals_summary()
    assert "RAM:" in summary
    print(f"  [PASS] Vitals: {summary}")


def test_memory_persistence():
    print("[2/5] Testing Conscious Memory Persistence...")
    # Add fact
    memory.remember_fact("user", "favorite_field", "Autonomous Artificial Intelligence")
    facts = memory.recall_facts("user")
    assert any(f["attribute"] == "favorite_field" for f in facts)

    # Add episode & FTS5 search
    ep_id = memory.add_episode("user", "Quantum gravity exploration project started.")
    assert ep_id > 0
    search_results = memory.search_episodes("Quantum gravity")
    assert len(search_results) > 0
    print("  [PASS] Facts & FTS5 episodic search OK")


def test_open_knowledge_wikipedia():
    print("[3/5] Testing Wikipedia Open Knowledge Connector...")
    res = search_wikipedia("Artificial intelligence", max_chars=300)
    assert "Wikipedia" in res
    assert "intelligence" in res.lower()
    print("  [PASS] Wikipedia lookup OK")


def test_open_knowledge_arxiv():
    print("[4/5] Testing arXiv Open Academic Connector...")
    res = search_arxiv("transformer neural network", max_results=1)
    assert "arXiv Research Papers" in res
    print("  [PASS] arXiv query OK")


def test_cognitive_engine():
    print("[5/5] Testing Cognitive Engine & Tool Calling...")
    response = engine.process_query("What is the current time and system RAM status?")
    assert len(response) > 0
    print(f"  [PASS] Engine response received ({len(response)} chars)")


if __name__ == "__main__":
    print("=== AETHER Verification Suite ===")
    test_hardware_sentry()
    test_memory_persistence()
    test_open_knowledge_wikipedia()
    test_open_knowledge_arxiv()
    test_cognitive_engine()
    print("\n>>> ALL TESTS PASSED SUCCESSFULLY! <<<")
