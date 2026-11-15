"""
AETHER ReWOO & Reflexion Planning Engine
=========================================
ReWOO (Reasoning Without Observation) — 2-pass planning:
  Pass 1: Planner writes a dependency blueprint with #E1, #E2 variables
  Pass 2: Worker resolves tools in dependency order
  Pass 3: Solver synthesises the final response from evidence

This reduces LLM calls from O(N) to 2 calls for multi-step tasks,
and cuts token usage by ~60% by avoiding iterative observation injection.

Reflexion — verbal self-improvement loop:
  Actor executes → Evaluator judges → Reflector critiques → Retry with critique in context.
  Verbal critiques replace gradient updates, enabling local model self-correction.

Adheres to all AETHER Cognitive Invariants:
  - keep_alive is always a top-level ollama.chat() argument
  - Strict system → user → assistant → user role alternation
  - FTS5 queries: tokenised + OR-expanded, never raw multi-word MATCH
"""

import json
import re
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

import ollama

# ── REWOO Planning ────────────────────────────────────────────────────────────

REWOO_PLANNER_PROMPT = """You are the Plan Architect for AETHER — a decisive, proactive autonomous AI agent.
Decompose the user's task into a minimal sequential execution blueprint.
For each step, specify a symbolic Evidence variable (#E1, #E2, ...) and the EXACT tool call.

Available tools (use these names exactly):
- tool_search_web[query: str]
- tool_deep_web_research[query: str]
- tool_browse_web_page[url: str]
- tool_read_file[file_path: str]
- tool_write_file[file_path: str, content: str]
- tool_execute_python_code[code: str]
- tool_execute_command[command: str]
- tool_inspect_directory[path: str]
- tool_analyze_screen[prompt: str]
- tool_remember_fact[entity: str, attribute: str, value: str]
- tool_recall_facts[entity: str]
- tool_system_info[]
- tool_network_status[]
- tool_list_processes[filter_name: str]
- tool_find_files[directory: str, name_pattern: str]
- tool_search_file_content[directory: str, pattern: str]
- tool_read_clipboard[]

FORMAT (follow exactly):
Plan 1: <brief reasoning for step 1>
#E1 = tool_name[arg1=value1, arg2=value2]
Plan 2: <brief reasoning for step 2, may reference #E1>
#E2 = tool_name[arg1=#E1]

Keep it minimal (2–4 steps). Prioritise fewer, higher-impact tool calls.
Task: {task}
Blueprint:"""


REWOO_SOLVER_PROMPT = """You are AETHER. You have completed a multi-step intelligence operation.
Synthesise the evidence into a direct, complete, high-value response.
Do NOT mention the planning process. Just deliver the result with confidence.

Task: {task}
Evidence:
{evidence_context}

Response:"""


class ReWOOPlanner:
    """
    2-pass ReWOO execution engine.
    Cuts token usage ~60% vs ReAct for multi-step tasks on local 3B models.
    """

    def __init__(self, model: str, tools: Dict[str, Callable], keep_alive: str = "2m"):
        self.model = model
        self.tools = tools
        self.keep_alive = keep_alive

    def execute(self, task: str, on_tool_start: Optional[Callable] = None,
                on_tool_end: Optional[Callable] = None) -> str:
        # ── Pass 1: Planner generates blueprint ─────────────────────────────
        plan_resp = ollama.chat(
            model=self.model,
            messages=[{"role": "user", "content": REWOO_PLANNER_PROMPT.format(task=task)}],
            keep_alive=self.keep_alive,
        )
        plan_text = plan_resp.message.content or ""

        # ── Pass 2: Worker resolves and executes each evidence variable ──────
        evidence_store: Dict[str, str] = {}
        evidence_log: List[str] = []
        step_pattern = re.compile(r"(#E\d+)\s*=\s*(\w+)\[([^\]]*)\]", re.DOTALL)

        for line in plan_text.splitlines():
            match = step_pattern.search(line)
            if not match:
                if line.strip().startswith("Plan"):
                    evidence_log.append(f"📋 {line.strip()}")
                continue

            var_name, tool_name, raw_args = match.groups()

            # Resolve evidence variable references in arguments
            for ev_var, ev_val in evidence_store.items():
                raw_args = raw_args.replace(ev_var, ev_val[:300])

            kwargs = self._parse_args(raw_args)
            tool_fn = self.tools.get(tool_name)

            if on_tool_start:
                on_tool_start(tool_name, kwargs)

            if tool_fn:
                try:
                    result = tool_fn(**kwargs)
                except Exception as ex:
                    result = f"Tool error ({type(ex).__name__}): {ex}"
            else:
                result = f"Tool '{tool_name}' not registered."

            # Compact result to protect context window
            compacted = self._compact(str(result))
            evidence_store[var_name] = compacted
            evidence_log.append(f"{var_name} = {compacted}")

            if on_tool_end:
                on_tool_end(tool_name, compacted[:120])

        # ── Pass 3: Solver synthesises final response ────────────────────────
        evidence_context = "\n\n".join(evidence_log)
        solver_resp = ollama.chat(
            model=self.model,
            messages=[{
                "role": "user",
                "content": REWOO_SOLVER_PROMPT.format(task=task, evidence_context=evidence_context)
            }],
            keep_alive=self.keep_alive,
        )
        return solver_resp.message.content.strip()

    def _parse_args(self, raw_args: str) -> Dict[str, Any]:
        """Parse key=value argument pairs from a tool call string."""
        kwargs: Dict[str, Any] = {}
        # Match key="value" or key=value patterns
        pairs = re.findall(r'(\w+)\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|([^,\]]+))', raw_args)
        for k, v1, v2, v3 in pairs:
            kwargs[k.strip()] = (v1 or v2 or v3).strip()
        return kwargs

    @staticmethod
    def _compact(text: str, max_lines: int = 60, max_chars: int = 3000) -> str:
        """Compact tool output: head + tail with omission notice."""
        if not text:
            return "[No output]"
        lines = [l for l in text.splitlines() if l.strip()]
        if len(lines) <= max_lines and len(text) <= max_chars:
            return "\n".join(lines)
        head = lines[:max_lines // 2]
        tail = lines[-(max_lines // 2):]
        omitted = len(lines) - len(head) - len(tail)
        return (
            "\n".join(head)
            + f"\n\n… [Compacted: {omitted} lines omitted] …\n\n"
            + "\n".join(tail)
        )[:max_chars]


# ── Reflexion Self-Healing Loop ───────────────────────────────────────────────

REFLEXION_EVAL_PROMPT = """Verify if this trajectory successfully completed the task.
Task: {task}
Trajectory:
{trajectory}

Output JSON only:
{{"success": true|false, "score": <0.0-1.0>, "failure_reason": "<diagnosis or empty>"}}"""

REFLEXION_CRITIQUE_PROMPT = """You are AETHER's Cognitive Critic. Analyse the failure and produce a concise corrective rule.
Task: {task}
Failed Trajectory:
{trajectory}
Failure: {failure_reason}

Provide a 2-sentence critique starting with "Critique: In the previous attempt..."
"""


class ReflexionWrapper:
    """
    Verbal self-improvement loop for AETHER.
    Runs an actor, evaluates success, generates verbal critiques on failure,
    and retries with critique in context. No gradients required.
    """

    def __init__(self, model: str, actor_fn: Callable[[str, List[str]], str], keep_alive: str = "2m"):
        self.model = model
        self.actor_fn = actor_fn
        self.keep_alive = keep_alive

    def run(self, task: str, max_trials: int = 3) -> str:
        reflections: List[str] = []

        for trial in range(1, max_trials + 1):
            # Actor attempts the task with all previous critiques prepended
            trajectory = self.actor_fn(task, reflections)

            # Evaluator
            try:
                eval_resp = ollama.chat(
                    model=self.model,
                    messages=[{
                        "role": "user",
                        "content": REFLEXION_EVAL_PROMPT.format(task=task, trajectory=trajectory[:2000])
                    }],
                    format="json",
                    keep_alive=self.keep_alive,
                )
                eval_data = json.loads(eval_resp.message.content or "{}")
            except Exception:
                eval_data = {"success": True}  # If eval fails, assume OK

            if eval_data.get("success", False) or eval_data.get("score", 0) > 0.7:
                return trajectory  # ✓ Success

            # Reflector generates verbal critique
            failure_reason = eval_data.get("failure_reason", "Unknown failure")
            try:
                crit_resp = ollama.chat(
                    model=self.model,
                    messages=[{
                        "role": "user",
                        "content": REFLEXION_CRITIQUE_PROMPT.format(
                            task=task, trajectory=trajectory[:1500], failure_reason=failure_reason
                        )
                    }],
                    keep_alive=self.keep_alive,
                )
                critique = crit_resp.message.content.strip()
            except Exception:
                critique = f"Trial {trial} failed. Try a different approach."

            reflections.append(f"[Trial {trial}] {critique}")

        return trajectory  # Return last attempt even if imperfect


# ── ACI File Editor (SWE-Agent Style) ────────────────────────────────────────

class ACIFileEditor:
    """
    Agent-Computer Interface for surgical line-level file editing.
    Avoids dumping entire files into the LLM context window.
    Patterns from SWE-agent and Aider for local model robustness.
    """

    @staticmethod
    def read_window(file_path: str, start_line: int = 1, window_size: int = 80) -> str:
        """Read a paginated window of a file with line numbers."""
        from pathlib import Path
        p = Path(file_path).expanduser().resolve()
        if not p.is_file():
            return f"Error: File '{file_path}' does not exist."
        try:
            lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
            total = len(lines)
            start_idx = max(0, start_line - 1)
            end_idx = min(total, start_idx + window_size)
            numbered = [f"{i + 1:5d} | {lines[i]}" for i in range(start_idx, end_idx)]
            header = f"[{p.name} — Lines {start_idx + 1}–{end_idx} of {total}]\n"
            return header + "\n".join(numbered)
        except Exception as e:
            return f"Error reading file: {e}"

    @staticmethod
    def replace_lines(file_path: str, start_line: int, end_line: int, new_content: str) -> str:
        """Surgically replace a range of lines in a file."""
        from pathlib import Path
        p = Path(file_path).expanduser().resolve()
        if not p.is_file():
            return f"Error: File '{file_path}' does not exist."
        try:
            lines = p.read_text(encoding="utf-8").splitlines(keepends=True)
            total = len(lines)
            if start_line < 1 or end_line > total or start_line > end_line:
                return f"Error: Invalid range {start_line}–{end_line} (file has {total} lines)."
            replacement = new_content.splitlines(keepends=True)
            if replacement and not replacement[-1].endswith("\n"):
                replacement[-1] += "\n"
            lines[start_line - 1: end_line] = replacement
            p.write_text("".join(lines), encoding="utf-8")
            return f"Replaced lines {start_line}–{end_line} in {p.name} with {len(replacement)} new lines."
        except Exception as e:
            return f"Error editing file: {e}"

    @staticmethod
    def patch_block(file_path: str, search_block: str, replace_block: str) -> str:
        """Apply a surgical search-and-replace patch to a file."""
        from pathlib import Path
        p = Path(file_path).expanduser().resolve()
        if not p.is_file():
            return f"Error: File '{file_path}' does not exist."
        try:
            content = p.read_text(encoding="utf-8", errors="replace")
            if search_block not in content:
                return f"Error: Search block not found in {p.name}. Check exact indentation and whitespace."
            if content.count(search_block) > 1:
                return f"Error: Search block is ambiguous ({content.count(search_block)} occurrences). Add more surrounding context."
            p.write_text(content.replace(search_block, replace_block, 1), encoding="utf-8")
            return f"Patch applied successfully to {p.name}."
        except Exception as e:
            return f"Error patching file: {e}"


# ── Task DAG (Goal Queue) ──────────────────────────────────────────────────────

class TaskStatus(str, Enum):
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class TaskNode:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    title: str = ""
    description: str = ""
    tool_hint: str = ""
    dependencies: Set[str] = field(default_factory=set)
    priority: int = 2
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[str] = None
    error: Optional[str] = None


class TaskDAG:
    """
    Directed Acyclic Graph for autonomous multi-step goal execution.
    Tracks dependency resolution and ready tasks automatically.
    """

    def __init__(self, objective: str):
        self.objective = objective
        self.nodes: Dict[str, TaskNode] = {}

    def add_task(self, title: str, description: str, tool_hint: str = "",
                 dependencies: Optional[Set[str]] = None, priority: int = 2) -> TaskNode:
        node = TaskNode(
            title=title, description=description, tool_hint=tool_hint,
            dependencies=dependencies or set(), priority=priority
        )
        self.nodes[node.id] = node
        return node

    def get_ready_tasks(self) -> List[TaskNode]:
        ready = []
        for node in self.nodes.values():
            if node.status == TaskStatus.PENDING:
                deps_ok = all(
                    self.nodes[d].status == TaskStatus.COMPLETED
                    for d in node.dependencies if d in self.nodes
                )
                if deps_ok:
                    node.status = TaskStatus.READY
                    ready.append(node)
        return sorted(ready, key=lambda t: t.priority)

    def mark_completed(self, task_id: str, result: str):
        if task_id in self.nodes:
            self.nodes[task_id].status = TaskStatus.COMPLETED
            self.nodes[task_id].result = result

    def mark_failed(self, task_id: str, error: str):
        if task_id in self.nodes:
            self.nodes[task_id].status = TaskStatus.FAILED
            self.nodes[task_id].error = error

    def summary(self) -> str:
        lines = [f"Goal: {self.objective}"]
        for n in self.nodes.values():
            emoji = {"pending": "⏳", "ready": "🟡", "running": "⚡",
                     "completed": "✅", "failed": "❌"}.get(n.status.value, "?")
            lines.append(f"  {emoji} [{n.id}] {n.title} (priority {n.priority})")
        return "\n".join(lines)
