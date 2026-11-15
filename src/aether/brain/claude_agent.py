r"""
AETHER Claude Agent Cognitive Orchestrator
==========================================
Engineered to replicate Anthropic's Claude Code agent architecture:
1. Extended Thinking: Decoupled <thinking> scratchpad reasoning and self-reflection.
2. High Agency: Surgical tools (Bash, View, Edit, Write, Grep, Find, Todo, Subagent).
3. Verification Loop: Tests code, catches errors, inspects diffs, and iterates.
4. Zero Sycophancy: Crisp, technical, objective, action-first responses.
"""

import logging
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import ollama

from aether.brain.auto_learner import auto_learner
from aether.brain.cognitive_learner import cognitive_learner
from aether.brain.curriculum_learner import curriculum_learner
from aether.brain.prompts import build_claude_system_prompt
from aether.brain.skills_vault import skills_vault
from aether.brain.task_engagement import EngagementPersona, task_engagement
from aether.brain.thinking_cortex import thinking_cortex
from aether.config import config
from aether.memory.store import memory
from aether.tools.claude_tools import (claude_bash, claude_edit, claude_find,
                                       claude_grep, claude_subagent,
                                       claude_todo, claude_todos, claude_view,
                                       claude_write)
from aether.tools.open_knowledge import browse_web_page, search_web

logger = logging.getLogger("aether.claude_agent")

CLAUDE_TOOLS_LIST = [
    claude_bash,
    claude_view,
    claude_edit,
    claude_write,
    claude_grep,
    claude_find,
    claude_todo,
    claude_subagent,
]

CLAUDE_TOOL_DISPATCHER = {
    "claude_bash": claude_bash,
    "claude_view": claude_view,
    "claude_edit": claude_edit,
    "claude_write": claude_write,
    "claude_grep": claude_grep,
    "claude_find": claude_find,
    "claude_todo": claude_todo,
    "claude_subagent": claude_subagent,
}


@dataclass
class AgentTurnMetrics:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    duration_secs: float = 0.0
    tools_executed: List[str] = field(default_factory=list)


class ClaudeAgent:
    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or "aether:claude"
        self._cached_active_model: Optional[str] = None
        self.max_iterations = 15

    def resolve_active_model(self) -> str:
        """Resolve the active model in Ollama, prioritizing aether:claude."""
        if self._cached_active_model:
            return self._cached_active_model
        try:
            installed_models = [m.get("model", m.get("name", "")) for m in ollama.list().get("models", [])]
            for target in ["aether:claude", "aether:antigravity", "aether:autonomous", "qwen2.5-coder:3b", "llama3.2:3b"]:
                for m in installed_models:
                    if target in m:
                        self._cached_active_model = target
                        return target
            return config.local_model
        except Exception:
            return config.local_model

    def extract_thinking(self, content: str) -> Tuple[Optional[str], str]:
        """
        Extract <thinking>...</thinking> blocks from the model's output.
        Returns (thinking_text, clean_response_text).
        """
        m = re.search(r"<thinking>(.*?)</thinking>", content, re.DOTALL | re.IGNORECASE)
        if m:
            thinking_text = m.group(1).strip()
            clean_text = re.sub(r"<thinking>.*?</thinking>", "", content, flags=re.DOTALL | re.IGNORECASE).strip()
            return thinking_text, clean_text
        return None, content.strip()

    def parse_text_tool_calls(self, text: str) -> List[Dict[str, Any]]:
        """Parse JSON or markdown-wrapped tool calls if model outputs them as text."""
        import json
        parsed = []
        json_blocks = re.findall(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
        for block in json_blocks:
            block_clean = block.strip()
            if block_clean.startswith("[") and block_clean.endswith("]"):
                try:
                    items = json.loads(block_clean)
                    for item in items:
                        if isinstance(item, dict) and "name" in item:
                            parsed.append(item)
                except Exception:
                    pass
            else:
                wrapped = f"[{block_clean}]"
                try:
                    items = json.loads(wrapped)
                    for item in items:
                        if isinstance(item, dict) and "name" in item:
                            parsed.append(item)
                except Exception:
                    for obj_match in re.finditer(r"\{[^{}]*\"name\"[^{}]*\}", block_clean):
                        try:
                            item = json.loads(obj_match.group(0))
                            if isinstance(item, dict) and "name" in item:
                                parsed.append(item)
                        except Exception:
                            pass
        return parsed

    def execute_turn(
        self,
        user_prompt: str,
        session_id: str = "claude_default",
        on_thinking: Optional[Callable[[str], None]] = None,
        on_tool_start: Optional[Callable[[str, Dict[str, Any]], None]] = None,
        on_tool_end: Optional[Callable[[str, str], None]] = None,
    ) -> Tuple[str, AgentTurnMetrics]:
        """
        Execute an autonomous multi-step Claude agent loop.
        """
        t_start = time.time()
        metrics = AgentTurnMetrics()
        active_model = self.resolve_active_model()

        # Check for fast-paths
        q = user_prompt.strip().lower()
        if q in ("/todo", "todo", "todos", "/todos"):
            return claude_todos.format_markdown(), metrics
        if q.startswith(("/todo add", "todo add")):
            text = re.sub(r"^/?todo\s+add\s*", "", user_prompt.strip(), flags=re.IGNORECASE)
            return claude_todo("add", text=text), metrics
        if q in ("/diff", "diff"):
            diff_res = claude_bash("git diff")
            return f"```diff\n{diff_res}\n```", metrics
        if q.startswith("/deliberate"):
            task_text = re.sub(r"^/deliberate\s*", "", user_prompt.strip(), flags=re.IGNORECASE)
            d_res = thinking_cortex.deliberate(task_text)
            if on_thinking:
                on_thinking(d_res.full_trace)
            return (
                f"{d_res.full_trace}\n\n"
                f"### 🎯 Synthesized Execution Blueprint\n{d_res.synthesizer_plan}"
            ), metrics
        if q.startswith("/assimilate"):
            s_name = re.sub(r"^/assimilate\s*", "", user_prompt.strip(), flags=re.IGNORECASE)
            res = cognitive_learner.assimilate_skill(s_name)
            return res.get("summary", res.get("error", "Failed")), metrics
        if q in ("/consolidate", "consolidate"):
            res = cognitive_learner.consolidate_episodes()
            return f"✓ {res.get('status', 'Consolidated')} ({res.get('facts_added', 0)} facts, {res.get('insights_consolidated', 0)} insights).", metrics
        if q in ("/invariants", "invariants"):
            invs = cognitive_learner.get_learned_invariants(limit=10)
            if not invs:
                return "No Reflexion error invariants recorded yet.", metrics
            return "### 🛡️ Active Learned Invariants (Reflexion Memory):\n" + "\n".join([f"- {inv}" for inv in invs]), metrics
        if q.startswith("/selfplay"):
            dom = re.sub(r"^/selfplay\s*", "", user_prompt.strip(), flags=re.IGNORECASE) or "coding"
            res = cognitive_learner.run_self_play(dom)
            if res.get("success"):
                return f"✓ Self-Play challenge completed in '{dom}'!\n**Problem:** {res['problem']}\n**Dataset count:** {res['total_dataset_samples']} pairs.", metrics
            return f"Self-play failed: {res.get('error')}", metrics
        if q.startswith("/engage"):
            obj = re.sub(r"^/engage\s*", "", user_prompt.strip(), flags=re.IGNORECASE)
            if not obj:
                return task_engagement.format_dag_markdown(), metrics
            dag_view = task_engagement.create_engagement_dag(obj)
            return dag_view, metrics
        if q in ("/dag", "dag", "/engagement", "engagement"):
            return task_engagement.format_dag_markdown(), metrics
        if q.startswith("/advance"):
            parts = re.sub(r"^/advance\s*", "", user_prompt.strip(), flags=re.IGNORECASE).split(maxsplit=1)
            tid = parts[0] if parts else ""
            res_txt = parts[1] if len(parts) > 1 else "Advanced autonomously."
            if not tid:
                current_task = task_engagement.get_current_actionable_task()
                tid = current_task.id if current_task else "T1"
            res = task_engagement.advance_task(tid, result_summary=res_txt)
            return f"{res}\n\n{task_engagement.format_dag_markdown()}", metrics
        if q.startswith("/persona"):
            p_arg = re.sub(r"^/persona\s*", "", user_prompt.strip(), flags=re.IGNORECASE).upper()
            if p_arg in EngagementPersona._value2member_map_:
                msg = task_engagement.set_persona(EngagementPersona(p_arg))
                return msg, metrics
            curr = task_engagement.active_persona.value
            valid = ", ".join(list(EngagementPersona._value2member_map_.keys()))
            return f"Current cognitive posture: **{curr}**\nUsage: `/persona <{valid}>`", metrics
        if q in ("/disciplines", "disciplines"):
            discs = curriculum_learner.list_disciplines()
            lines = ["### 🌌 8 Frontier Cognitive Disciplines (Curriculum Learner):"]
            for d in discs:
                lines.append(f"- **{d['title']}** (`{d['key']}`): {d['description']}")
            lines.append("\n*To run an adversarial tournament in any discipline: `/tournament <discipline>`*")
            return "\n".join(lines), metrics
        if q.startswith("/tournament"):
            disc = re.sub(r"^/tournament\s*", "", user_prompt.strip(), flags=re.IGNORECASE) or "distributed_systems"
            t_res = curriculum_learner.run_adversarial_tournament(disc)
            report = (
                f"### ⚔️ Adversarial Tournament Completed: {disc.upper()}\n"
                f"**Duration:** {t_res.duration_secs:.2f}s | **Problem:** {t_res.problem}\n\n"
                f"#### 🏆 Judge & Synthesis Verdict:\n{t_res.judge_verdict}\n\n"
                f"**Invariants Extracted:** {len(t_res.invariants_extracted)} rules committed to SQLite FTS5."
            )
            return report, metrics


        recalled = memory.recall_facts()
        recalled_str = "\n".join([f"- {f['entity']} {f['attribute']}: {f['value']}" for f in recalled[:6]]) if recalled else ""
        heuristics = memory.recall_heuristic_rules(user_prompt, limit=5)

        # Dynamic skill assimilation: detect specialized skill context
        active_skills = cognitive_learner.auto_retrieve_skills_for_prompt(user_prompt, max_skills=2)
        skills_directives = ""
        if active_skills:
            skills_directives = "\n".join([f"#### [{s['name'].upper()} GUIDELINES]\n{s['workflow']}" for s in active_skills])

        # Dynamic persona and DAG engagement context
        persona_directive = task_engagement.get_persona_directive()
        dag_context = ""
        if task_engagement.active_objective:
            curr_task = task_engagement.get_current_actionable_task()
            curr_title = f"[{curr_task.id}] {curr_task.title}" if curr_task else "All tasks completed"
            dag_context = f"\n- Engagement Objective: {task_engagement.active_objective}\n- Immediate Focus: {curr_title}\n- {persona_directive}"

        system_prompt = build_claude_system_prompt(
            recalled_context=(recalled_str + dag_context).strip(),
            learned_rules=heuristics,
            skills_directives=skills_directives,
        )
        recent_episodes = memory.get_recent_episodes(limit=6)

        messages: List[Dict[str, Any]] = [{"role": "system", "content": system_prompt}]
        for ep in recent_episodes:
            if ep["role"] in ("user", "assistant"):
                messages.append({"role": ep["role"], "content": ep["content"]})
        messages.append({"role": "user", "content": user_prompt})

        # System 2 Cognitive Deliberation check
        should_delib, delib_reason = thinking_cortex.should_deliberate(user_prompt)
        if should_delib and not q.startswith("/"):
            delib_res = thinking_cortex.deliberate(user_prompt)
            if on_thinking:
                on_thinking(delib_res.full_trace)
            messages.append({
                "role": "assistant",
                "content": f"<thinking>\nDeliberation: {delib_res.synthesizer_plan}\n</thinking>\nI have analyzed the problem requirements and verified the execution blueprint.",
            })

        final_response = ""
        tool_events: List[Dict[str, Any]] = []

        for iteration in range(self.max_iterations):
            try:
                res = ollama.chat(
                    model=active_model,
                    messages=messages,
                    tools=CLAUDE_TOOLS_LIST,
                    options={
                        "temperature": 0.2,
                        "num_ctx": 8192,
                        "repeat_penalty": 1.15,
                    },
                    keep_alive=config.keep_alive,
                )
            except Exception as e:
                err_msg = f"Ollama execution error: {e}"
                logger.error(err_msg)
                return f"Error executing model turn: {e}", metrics

            msg = res.message
            content = msg.content or ""
            tool_calls = msg.tool_calls or []

            # Extract thinking block if present
            thinking, clean_content = self.extract_thinking(content)
            if thinking and on_thinking:
                on_thinking(thinking)

            # Support dual-mode tool parsing: native Ollama tool_calls + text JSON tool blocks
            executable_calls: List[Tuple[str, Dict[str, Any]]] = []
            if tool_calls:
                for call in tool_calls:
                    fn = call.function
                    executable_calls.append((fn.name, fn.arguments or {}))
            else:
                text_calls = self.parse_text_tool_calls(clean_content)
                for tc in text_calls:
                    tname = tc.get("name", "")
                    targs = tc.get("parameters") or tc.get("arguments") or {}
                    clean_args = {k: v for k, v in targs.items() if v is not None}
                    executable_calls.append((tname, clean_args))

            if not executable_calls:
                final_response = clean_content
                break

            # Execute tool calls with Pre-Simulation & Reflexion
            messages.append(msg)
            for tool_name, tool_args in executable_calls:
                metrics.tools_executed.append(tool_name)

                if on_tool_start:
                    on_tool_start(tool_name, tool_args)

                # Pre-Simulation Safety Check
                verdict = thinking_cortex.pre_simulate_action(tool_name, tool_args)
                if not verdict.safe:
                    tool_res = f"[PRE-SIMULATION SAFETY BLOCK] Action halted: {verdict.reason}. Precautions: {', '.join(verdict.precautions)}"
                    logger.warning(f"Tool {tool_name} blocked by pre-simulation: {verdict.reason}")
                else:
                    handler = CLAUDE_TOOL_DISPATCHER.get(tool_name)
                    if handler:
                        try:
                            tool_res = handler(**tool_args)
                        except Exception as ex:
                            tool_res = f"Error calling {tool_name}: {ex}"
                    else:
                        tool_res = f"Unknown tool: {tool_name}"

                # Reflexion Invariant synthesis on failure
                is_err = "error" in str(tool_res).lower() or "exception" in str(tool_res).lower() or not verdict.safe
                if is_err:
                    invariant = cognitive_learner.reflexion_post_mortem(tool_name, tool_args, str(tool_res))
                    tool_res = f"{tool_res}\n[Learned Reflexion Invariant: {invariant}]"

                tool_events.append({
                    "tool": tool_name,
                    "args": tool_args,
                    "result": str(tool_res),
                    "is_error": is_err,
                })

                if on_tool_end:
                    on_tool_end(tool_name, str(tool_res)[:120])

                messages.append({
                    "role": "tool",
                    "content": str(tool_res),
                    "name": tool_name,
                })

        metrics.duration_secs = time.time() - t_start
        memory.add_episode("user", user_prompt, session_id=session_id)
        if final_response:
            memory.add_episode("assistant", final_response, session_id=session_id)

        # Fire continuous learning turn introspection in background
        auto_learner.introspect_turn_async(
            user_message=user_prompt,
            assistant_response=final_response,
            tool_events=tool_events,
            session_id=session_id,
        )

        return final_response, metrics


claude_agent = ClaudeAgent()
