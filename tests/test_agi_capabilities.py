import sys, os
from pathlib import Path

# Set project root
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "src"))
os.chdir(str(ROOT_DIR))

from aether.brain.planning import ACIFileEditor, ReWOOPlanner, TaskDAG
from aether.memory.store import memory
from aether.brain.engine import AVAILABLE_TOOLS, TOOL_DISPATCHER

print(f"Total Available Tools: {len(AVAILABLE_TOOLS)}")
assert "tool_read_file_window" in TOOL_DISPATCHER
assert "tool_replace_file_lines" in TOOL_DISPATCHER
assert "tool_patch_file_block" in TOOL_DISPATCHER
assert "tool_plan_and_execute_task" in TOOL_DISPATCHER
assert "tool_learn_heuristic_rule" in TOOL_DISPATCHER
print("[OK] All ACI and ReWOO tools present in dispatcher.")

# Test ACIFileEditor
win = ACIFileEditor.read_window("pyproject.toml", start_line=1, window_size=10)
print("[OK] ACI read_window:\n" + win[:120] + "...")

# Test Heuristic Rules
rule_id = memory.add_heuristic_rule("Always verify syntax with AST before running generated Python code.", domain="coding")
print(f"[OK] Added heuristic rule #{rule_id}")
recalled = memory.recall_heuristic_rules("python code syntax verification")
print(f"[OK] Recalled heuristic rules: {recalled}")

# Test TaskDAG
dag = TaskDAG("Autonomous Evolution")
t1 = dag.add_task("Gather System Specs", "Inspect Windows ARM64 hardware", tool_hint="tool_system_info")
t2 = dag.add_task("Research Models", "Search for edge models", tool_hint="tool_search_web", dependencies={t1.id})
ready = dag.get_ready_tasks()
assert len(ready) == 1 and ready[0].id == t1.id
dag.mark_completed(t1.id, "Qualcomm Snapdragon X 16GB")
ready2 = dag.get_ready_tasks()
assert len(ready2) == 1 and ready2[0].id == t2.id
print("[OK] TaskDAG dependency resolution verified.")
print(dag.summary())
