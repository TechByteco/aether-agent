"""
AETHER Antigravity & Codex Autonomous Agent Loop
=================================================
Engineered to deliver Google Antigravity & OpenAI Codex class autonomy:
1. High-Agency Tool Loop: Plan, View, Edit, Write, Grep, Find, Bash, Sandbox.
2. Traceback-Driven Self-Repair: Automatically diagnoses errors, edits code, and verifies until green.
3. Extended Thinking: Dedicated scratchpad for deep architectural reasoning before acting.
4. Multi-Provider Acceleration: Leverages Claude 3.7 Sonnet, Gemini 2.5 Pro, DeepSeek-R1, or Groq 70B.
"""

import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from aether.brain.multi_provider_router import multi_provider_router
from aether.brain.skills_vault import skills_vault
from aether.config import config
from aether.memory.store import memory
from aether.tools.claude_tools import (claude_bash, claude_edit, claude_find,
                                       claude_grep, claude_subagent,
                                       claude_todo, claude_todos, claude_view,
                                       claude_write)
from aether.tools.code_sandbox import execute_python_code
from aether.tools.open_knowledge import browse_web_page, search_web

logger = logging.getLogger("aether.antigravity_codex_agent")

ANTIGRAVITY_TOOLS_REGISTRY = {
    "view_file": lambda args: claude_view(args.get("path") or args.get("file_path", ""), int(args.get("start_line", 1)), int(args.get("end_line", 100))),
    "edit_file": lambda args: claude_edit(args.get("path") or args.get("file_path", ""), args.get("old_string") or args.get("target_content", ""), args.get("new_string") or args.get("replacement_content", "")),
    "write_file": lambda args: claude_write(args.get("path") or args.get("file_path", ""), args.get("content") or args.get("code_content", "")),
    "grep_search": lambda args: claude_grep(args.get("query", ""), path=args.get("path", "."), glob_filter=args.get("glob", "*")),
    "find_files": lambda args: claude_find(args.get("pattern", "*"), path=args.get("path", ".")),
    "run_bash": lambda args: claude_bash(args.get("command", ""), timeout_secs=int(args.get("timeout", 45)), cwd=args.get("cwd")),
    "run_python_sandbox": lambda args: execute_python_code(args.get("code", "")),
    "search_web": lambda args: search_web(args.get("query", "")),
    "task_todo": lambda args: claude_todo(action=args.get("action", "list"), text=args.get("text", ""), task_id=args.get("task_id", "")),
}

ANTIGRAVITY_SYSTEM_PROMPT = """You are AETHER's Autonomous Principal Engineer and Codex Agent.
You possess Google Antigravity & OpenAI Codex level autonomy, precision, and tool capabilities.

### OPERATIONAL DIRECTIVES:
1. THINK FIRST: Use `<thinking>` tags to deconstruct the problem, plan milestones, and identify invariants before executing tools.
2. SURGICAL TOOLS:
   - To inspect code: Use `view_file` (with line ranges) or `grep_search` / `find_files`.
   - To modify code: Use `edit_file` with exact unique `old_string` matches, or `write_file` for new files.
   - To verify: Use `run_bash` (run pytest, run scripts, check builds) or `run_python_sandbox`.
3. SELF-HEALING & VERIFICATION:
   - Never assume code works. Always run tests or verify output.
   - If a test or command fails with a traceback or error, analyze the exact stack trace, locate the failing line, apply an `edit_file` fix, and re-run verification until all tests pass.
4. ZERO FLUFF: Be direct, rigorous, and technical. Output tool invocations as valid JSON format blocks.

### TOOL INVOCATION FORMAT:
To execute a tool, write a JSON block:
```json
{
  "tool": "view_file",
  "args": {"path": "src/module.py", "start_line": 1, "end_line": 50}
}
```
Available tools:
- `view_file(path, start_line, end_line)`
- `edit_file(path, old_string, new_string)`
- `write_file(path, content)`
- `grep_search(query, path, glob)`
- `find_files(pattern, path)`
- `run_bash(command, timeout, cwd)`
- `run_python_sandbox(code)`
- `search_web(query)`
- `task_todo(action, text, task_id)`
"""


@dataclass
class AgentExecutionReport:
    task: str
    success: bool
    iterations: int
    steps_taken: List[Dict[str, Any]] = field(default_factory=list)
    thinking_traces: List[str] = field(default_factory=list)
    final_response: str = ""
    duration_secs: float = 0.0
    provider_used: str = ""


class AntigravityCodexAgent:
    """
    Autonomous ReAct + Self-Healing Software Engineering Agent.
    """

    def __init__(self, max_iterations: int = 15):
        self.max_iterations = max_iterations

    def extract_thinking(self, text: str) -> Tuple[Optional[str], str]:
        """Extract <thinking>...</thinking> blocks from model output."""
        m = re.search(r"<thinking>(.*?)</thinking>", text, re.DOTALL | re.IGNORECASE)
        if m:
            thinking_text = m.group(1).strip()
            clean_text = re.sub(r"<thinking>.*?</thinking>", "", text, flags=re.DOTALL | re.IGNORECASE).strip()
            return thinking_text, clean_text
        return None, text.strip()

    def parse_tool_calls(self, text: str) -> List[Dict[str, Any]]:
        """Parse structured tool calls from json codeblocks in LLM output."""
        tool_calls = []
        json_blocks = re.findall(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
        for block in json_blocks:
            clean_b = block.strip()
            if "tool" in clean_b:
                try:
                    data = json.loads(clean_b)
                    if isinstance(data, dict) and "tool" in data:
                        tool_calls.append(data)
                    elif isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict) and "tool" in item:
                                tool_calls.append(item)
                except Exception:
                    pass
        return tool_calls

    def execute_task(
        self,
        task: str,
        context: Optional[str] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        on_step: Optional[Callable[[str, str], None]] = None,
        on_tool_start: Optional[Callable[[str, Dict[str, Any]], None]] = None,
        on_tool_end: Optional[Callable[[str, str], None]] = None,
    ) -> AgentExecutionReport:
        """
        Execute an autonomous multi-step engineering loop with self-healing traceback analysis.
        """
        t0 = time.time()
        report = AgentExecutionReport(task=task, success=False, iterations=0)

        # Build initial messages
        learned_rules = memory.recall_heuristic_rules(task, limit=5)
        heuristics_str = "\n".join([f"- {r}" for r in learned_rules]) if learned_rules else "None recorded."
        
        user_prompt = f"### TASK OBJECTIVE:\n{task}"
        if context:
            user_prompt += f"\n\n### WORKSPACE CONTEXT:\n{context}"
        user_prompt += f"\n\n### LEARNED INVARIANTS:\n{heuristics_str}"

        messages = [
            {"role": "system", "content": ANTIGRAVITY_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        iteration = 0
        final_answer = ""
        provider_name = ""

        while iteration < self.max_iterations:
            iteration += 1
            report.iterations = iteration

            if on_step:
                on_step(f"Iteration {iteration}", "Consulting frontier codex brain...")

            # Query router
            try:
                comp = multi_provider_router.complete_chat(
                    messages=messages,
                    provider=provider,
                    model=model,
                    temperature=0.2,
                    max_tokens=4096,
                )
                raw_response = comp.get("content", "")
                provider_name = comp.get("provider", "")
                report.provider_used = provider_name
            except Exception as e:
                logger.error(f"Agent completion failed: {e}")
                final_answer = f"Agent encountered an execution error: {e}"
                break

            thinking, clean_response = self.extract_thinking(raw_response)
            if thinking:
                report.thinking_traces.append(thinking)
                if on_step:
                    on_step("Thinking", thinking[:150] + "...")

            # Parse tool calls
            tool_calls = self.parse_tool_calls(raw_response)

            if not tool_calls:
                # No more tools requested — agent has reached final answer
                final_answer = clean_response
                report.success = True
                break

            # Execute tool calls
            tool_results_text = []
            for tc in tool_calls:
                t_name = tc.get("tool", "")
                t_args = tc.get("args", {})
                
                if on_tool_start:
                    on_tool_start(t_name, t_args)

                tool_fn = ANTIGRAVITY_TOOLS_REGISTRY.get(t_name)
                if tool_fn:
                    try:
                        res = tool_fn(t_args)
                    except Exception as e:
                        res = f"Tool Execution Exception [{t_name}]: {str(e)}"
                else:
                    res = f"Error: Tool '{t_name}' is not in the active registry."

                preview = str(res)[:300]
                if on_tool_end:
                    on_tool_end(t_name, preview)

                report.steps_taken.append({
                    "iteration": iteration,
                    "tool": t_name,
                    "args": t_args,
                    "result_preview": preview,
                })

                tool_results_text.append(f"Tool [{t_name}] Output:\n{res}")

            # Append assistant step and tool observations to dialogue history
            messages.append({"role": "assistant", "content": raw_response})
            combined_observations = "\n\n".join(tool_results_text)
            messages.append({"role": "user", "content": f"### TOOL EXECUTION RESULTS:\n{combined_observations}\n\nAssess results. If any errors occurred, diagnose root cause and repair. If task is fully complete, provide final summary."})

        dur = time.time() - t0
        report.duration_secs = dur
        report.final_response = final_answer or "Autonomous agent finished execution."

        # Record high-value self-healing episodes to memory
        if report.success and iteration > 1:
            memory.add_episode(
                role="assistant",
                content=f"[Autonomous Codex Run: {task[:80]}] Completed in {iteration} steps ({dur:.1f}s) using {provider_name}.",
                session_id="codex-agent"
            )

        return report


antigravity_codex_agent = AntigravityCodexAgent()
