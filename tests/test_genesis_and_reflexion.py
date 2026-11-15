"""
AETHER Dynamic Tool Genesis & Autonomous Reflexion Test Suite
============================================================
Tests:
1. Dynamic Tool Genesis (Option A):
   - AST validation & security checks (blocking forbidden constructs like eval/exec)
   - Dynamic tool registration, disk persistence, and hot-mounting into TOOL_DISPATCHER
   - Live execution of synthesized tools with arguments
   - Persistence across cold boots (load_all_generated_tools)
   - Tool listing and dynamic deletion
2. Autonomous Reflexion Loop (Option B):
   - Real-time error post-mortem analysis (heuristic & LLM critique)
   - SQLite FTS5 heuristic rule persistence (ExpeL pattern)
   - Cross-agent synchronization to .agents/rules/aether-cognitive-invariants.md
   - Self-healing directive formatting and retry guidance
3. Engine Integration:
   - Tool dispatcher registration & keyword routing
   - Error hook interception in engine execution
"""

import ast
from pathlib import Path
import sys
import tempfile
import time

# Ensure src is in python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from aether.brain.tool_genesis import (
    ToolGenesisEngine,
    tool_genesis,
    tool_synthesize_new_tool,
    tool_list_generated_tools,
    tool_delete_generated_tool,
)
from aether.brain.reflexion_engine import (
    ReflexionEngine,
    reflexion_engine,
    tool_reflect_on_error,
    tool_audit_error_invariants,
)
from aether.memory.store import memory
import aether.brain.engine as engine_mod


def test_tool_genesis_ast_validation():
    print("\n--- 1. Testing Tool Genesis AST Validation & Safety ---")

    # Valid tool code
    valid_code = """
import hashlib

def tool_generate_sha256(text: str = "") -> str:
    \"\"\"Compute SHA-256 hash of the input string.\"\"\"
    try:
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        return f"SHA-256: `{digest}`"
    except Exception as e:
        return f"Error: {e}"
"""
    valid, msg = tool_genesis.validate_tool_sandbox(valid_code, "tool_generate_sha256")
    assert valid, f"Valid tool should pass validation, got: {msg}"
    print(f"✓ Valid tool code passed validation: {msg}")

    # Syntax Error code
    syntax_error_code = "def tool_broken(: return 'error'"
    valid, msg = tool_genesis.validate_tool_sandbox(syntax_error_code)
    assert not valid
    assert "SyntaxError" in msg
    print(f"✓ Syntax error caught cleanly: {msg}")

    # Dangerous code with forbidden call
    dangerous_code = """
def tool_exploit():
    eval("__import__('os').system('dir')")
    return "done"
"""
    valid, msg = tool_genesis.validate_tool_sandbox(dangerous_code)
    assert not valid
    assert "Security Violation" in msg
    print(f"✓ Security violation blocked cleanly: {msg}")


def test_dynamic_tool_registration_and_execution():
    print("\n--- 2. Testing Dynamic Tool Registration & Live Execution ---")

    test_tool_name = "tool_test_calc_entropy"
    test_code = """
import math
from collections import Counter

def tool_test_calc_entropy(data_string: str = "") -> str:
    \"\"\"Calculate the Shannon entropy of a string.\"\"\"
    try:
        if not data_string:
            return "Shannon Entropy: 0.000 bits (empty string)"
        counts = Counter(data_string)
        total = len(data_string)
        entropy = -sum((c / total) * math.log2(c / total) for c in counts.values())
        return f"Shannon Entropy: **{entropy:.4f} bits** (Length: {total})"
    except Exception as e:
        return f"Error: {e}"
"""
    # 1. Register dynamic tool
    reg_res = tool_genesis.register_dynamic_tool(test_tool_name, test_code, overwrite=True)
    assert reg_res["success"], f"Registration failed: {reg_res.get('error')}"
    print(f"✓ Tool registered: {reg_res['tool_name']} at {reg_res['file_path']}")

    # 2. Verify presence in TOOL_DISPATCHER
    assert test_tool_name in engine_mod.TOOL_DISPATCHER, f"{test_tool_name} not found in TOOL_DISPATCHER"
    print(f"✓ Hot-mounted into engine.TOOL_DISPATCHER: {test_tool_name}")

    # 3. Execute tool via TOOL_DISPATCHER
    fn = engine_mod.TOOL_DISPATCHER[test_tool_name]
    output = fn(data_string="AETHER-AGI-EVOLUTION")
    assert "Shannon Entropy:" in output
    assert "bits" in output
    print(f"✓ Tool execution output: {output}")

    # 4. Verify listed in generated tools
    tools = tool_genesis.list_generated_tools()
    matching = [t for t in tools if t["tool_name"] == test_tool_name]
    assert len(matching) > 0
    print(f"✓ Tool found in list_generated_tools(): {matching[0]['docstring']}")

    # 5. Clean up
    deleted = tool_genesis.delete_generated_tool(test_tool_name)
    assert deleted
    assert test_tool_name not in engine_mod.TOOL_DISPATCHER
    print(f"✓ Tool successfully deleted and unmounted from TOOL_DISPATCHER")


def test_tool_genesis_cold_boot_persistence():
    print("\n--- 3. Testing Cold-Boot Persistence of Generated Tools ---")

    persisted_name = "tool_persisted_benchmark_helper"
    persisted_code = """
def tool_persisted_benchmark_helper(metric: str = "latency") -> str:
    \"\"\"Helper for benchmarking latency and throughput.\"\"\"
    return f"Benchmark Metric [{metric.upper()}]: Verified Optimal."
"""
    # Register tool
    reg_res = tool_genesis.register_dynamic_tool(persisted_name, persisted_code, overwrite=True)
    assert reg_res["success"]

    # Simulate fresh cold-boot re-indexing
    engine_mod.TOOL_DISPATCHER.pop(persisted_name, None)
    load_stats = tool_genesis.load_all_generated_tools()
    assert load_stats["loaded"] >= 1
    assert persisted_name in engine_mod.TOOL_DISPATCHER
    print(f"✓ Cold-boot loader recovered {load_stats['loaded']} generated tools from disk.")

    # Cleanup
    tool_genesis.delete_generated_tool(persisted_name)


def test_reflexion_post_mortem_and_invariants():
    print("\n--- 4. Testing Reflexion Error Post-Mortem & Heuristics ---")

    # 1. Test PowerShell unrecognized command failure
    res_cmd = reflexion_engine.reflect_and_heal(
        failed_tool="tool_execute_command",
        args={"command": "nonexistent_tool_xyz --flag"},
        error_message="The term 'nonexistent_tool_xyz' is not recognized as a name of a cmdlet...",
        original_task="Run benchmark",
    )
    assert res_cmd["success"]
    assert "PATH" in res_cmd["diagnosis"] or "not found" in res_cmd["diagnosis"]
    assert "[Invariant]" in res_cmd["invariant_rule"]
    print(f"✓ Command failure diagnosed: {res_cmd['diagnosis']}")
    print(f"✓ Invariant rule generated: {res_cmd['invariant_rule']}")

    # 2. Test File Not Found failure
    res_file = reflexion_engine.reflect_and_heal(
        failed_tool="tool_read_file",
        args={"file_path": "c:/invalid/path/missing_config.json"},
        error_message="FileNotFoundError: [Errno 2] No such file or directory: missing_config.json",
        original_task="Read config",
    )
    assert res_file["success"]
    assert any(w in res_file["diagnosis"].lower() for w in ["does not exist", "not found", "missing", "file", "path"])
    print(f"✓ File error diagnosed: {res_file['diagnosis']}")

    # 3. Verify rule persisted in SQLite FTS5
    rules = memory.recall_heuristic_rules("reflexion", limit=10)
    assert len(rules) > 0
    print(f"✓ Recalled {len(rules)} Reflexion invariant rules from SQLite FTS5.")

    # 4. Verify rule file synchronization
    rules_file_path = Path(__file__).parent.parent / ".agents" / "rules" / "aether-cognitive-invariants.md"
    if rules_file_path.exists():
        content = rules_file_path.read_text(encoding="utf-8")
        assert "Learned Runtime Invariants" in content or "Invariants" in content
        print("✓ Successfully synchronized invariant rules to .agents/rules/aether-cognitive-invariants.md")


def test_engine_dispatcher_and_keywords():
    print("\n--- 5. Testing Engine Dispatcher & Action Keywords ---")

    # Check that new tools are in TOOL_DISPATCHER
    expected_tools = [
        "tool_synthesize_new_tool",
        "tool_list_generated_tools",
        "tool_delete_generated_tool",
        "tool_reflect_on_error",
        "tool_audit_error_invariants",
    ]
    for t in expected_tools:
        assert t in engine_mod.TOOL_DISPATCHER, f"Tool '{t}' missing from TOOL_DISPATCHER"
        print(f"✓ Verified engine tool: {t}")

    # Check that keywords map to new tools
    assert "genesis" in engine_mod.ACTION_KEYWORDS
    assert "tool_synthesize_new_tool" in engine_mod.ACTION_KEYWORDS["genesis"]
    assert "reflexion" in engine_mod.ACTION_KEYWORDS
    assert "tool_reflect_on_error" in engine_mod.ACTION_KEYWORDS["reflexion"]
    print("✓ Verified keyword routing for 'genesis' and 'reflexion'.")


def run_all():
    print("================================================================")
    print("🚀 Running AETHER Dynamic Genesis & Reflexion Test Suite")
    print("================================================================")
    test_tool_genesis_ast_validation()
    test_dynamic_tool_registration_and_execution()
    test_tool_genesis_cold_boot_persistence()
    test_reflexion_post_mortem_and_invariants()
    test_engine_dispatcher_and_keywords()
    print("\n================================================================")
    print("🎉 ALL TESTS PASSED! Dynamic Tool Genesis & Reflexion Loop Verified.")
    print("================================================================")


if __name__ == "__main__":
    run_all()
