"""
AETHER Cognitive Deliberation Cortex
====================================
Implements dual-process deliberation (System 1 vs. System 2):
1. Complexity Classifier: Detects tasks requiring deep architectural reasoning,
   algorithmic rigor, multi-step debugging, or security hardening.
2. Multi-Perspective Deliberation:
   - Phase 1: Problem Deconstruction & Invariant Mapping.
   - Phase 2: Inner Debate:
     * The Architect: Proposes elegant, modular, decoupled architecture.
     * The Critic / Skeptic: Attacks edge cases, race conditions, memory leaks, OS constraints.
     * The Synthesizer: Fuses perspectives into a battle-hardened execution blueprint.
   - Phase 3: Action Pre-Simulation:
     * Mental sandbox evaluating destructive side-effects, file overwrites, and command safety.
"""

import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import ollama

from aether.config import config
from aether.memory.store import memory

logger = logging.getLogger("aether.thinking_cortex")

COMPLEXITY_PATTERNS = [
    r"\b(architect|architecture|design|redesign|refactor|restructure)\b",
    r"\b(concurrency|multithread|race condition|deadlock|asyncio|lock)\b",
    r"\b(security|vulnerability|exploit|injection|buffer overflow|audit)\b",
    r"\b(optimize|performance|profiling|latency|throughput|memory leak)\b",
    r"\b(distributed|consensus|microservice|event-driven|scale)\b",
    r"\b(algorithm|data structure|tree|graph|dp|dynamic programming)\b",
    r"\b(debug|root cause|reproduce|post-mortem|diagnose)\b",
    r"\b(why did|how to prevent|invariant|formal verification)\b",
]

DELIBERATE_TRIGGER_KEYWORDS = [
    "/deliberate", "deliberate", "think deeply", "deep thinking",
    "analyze thoroughly", "inner debate", "critique"
]

DESTRUCTIVE_COMMAND_PATTERNS = [
    r"\brm\s+-[rf]{1,2}\b",
    r"\bdel\s+/[fqsa]{1,4}\s+c:\\\b",
    r"\bformat\s+[a-z]:\b",
    r"\brmdir\s+/[sq]\s+c:\\\b",
    r"\bdrop\s+database\b",
    r"\bdrop\s+table\b",
    r"\btruncate\s+table\b",
    r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;",  # fork bomb
]


@dataclass
class SimulationVerdict:
    safe: bool
    risk_level: str  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    reason: str
    warnings: List[str] = field(default_factory=list)
    precautions: List[str] = field(default_factory=list)


@dataclass
class DeliberationResult:
    task: str
    is_deliberate: bool
    deconstruction: str = ""
    architect_view: str = ""
    critic_view: str = ""
    synthesizer_plan: str = ""
    full_trace: str = ""
    duration_secs: float = 0.0


ARCHITECT_SYSTEM_PROMPT = """You are AETHER's Chief Software Architect.
Analyze the problem and propose a state-of-the-art, elegant, highly scalable solution.
Focus on modularity, clean decoupling, minimal state, and production engineering excellence.
Be concrete, technical, and precise. Avoid fluff."""

CRITIC_SYSTEM_PROMPT = """You are AETHER's Cognitive Skeptic and Security Auditor.
Your job is to rigorously challenge the proposed solution:
1. Identify hidden edge cases, platform gotchas (Windows, PowerShell, Snapdragon ARM64, Python 3.13).
2. Point out race conditions, resource leaks, unhandled exceptions, and failure modes.
3. Attack potential performance bottlenecks and security vulnerabilities.
Be ruthless, constructive, and hyper-specific."""

SYNTHESIZER_SYSTEM_PROMPT = """You are AETHER's Master Synthesizer.
You have observed the debate between the Architect and the Critic.
Reconcile their perspectives into a single, bulletproof, step-by-step execution blueprint.
Explicitly list:
1. Core Strategy & Invariants (what MUST always hold true).
2. Anticipated Traps & Hardened Defenses (how critic findings were mitigated).
3. Surgical Execution Steps."""


class ThinkingCortex:
    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or "aether:claude"
        self._cached_model: Optional[str] = None

    def resolve_model(self) -> str:
        """Resolve available local reasoning model."""
        if self._cached_model:
            return self._cached_model
        try:
            installed = [m.get("model", m.get("name", "")) for m in ollama.list().get("models", [])]
            for candidate in ["aether:claude", "aether:autonomous", "aether:antigravity", "llama3.2:3b", "qwen2.5-coder:3b"]:
                for m in installed:
                    if candidate in m:
                        self._cached_model = candidate
                        return candidate
            return config.local_model
        except Exception:
            return config.local_model

    def should_deliberate(self, prompt: str) -> Tuple[bool, str]:
        """
        System 1 vs. System 2 Cognitive Classifier.
        Returns (is_complex, reason).
        """
        p_lower = prompt.lower().strip()

        # Check explicit trigger
        for kw in DELIBERATE_TRIGGER_KEYWORDS:
            if kw in p_lower:
                return True, f"Explicit deliberation trigger detected: '{kw}'"

        # Check multi-line or long complex prompt with code
        if len(prompt) > 350 and ("```" in prompt or len(prompt.splitlines()) > 6):
            return True, "Complex multi-paragraph prompt with code context"

        # Check complexity regex patterns
        for pat in COMPLEXITY_PATTERNS:
            m = re.search(pat, p_lower)
            if m:
                return True, f"Domain complexity keyword detected: '{m.group(0)}'"

        return False, "Standard query (System 1 fast-path suitable)"

    def deliberate(
        self,
        task: str,
        context: Optional[str] = None,
        on_stage: Optional[Callable[[str, str], None]] = None,
    ) -> DeliberationResult:
        """
        Executes a 3-stage Tree-of-Thought Inner Debate:
        Stage 1: Problem Deconstruction
        Stage 2: Architect vs. Critic Debate
        Stage 3: Master Synthesis Blueprint
        """
        t0 = time.time()
        active_model = self.resolve_model()
        result = DeliberationResult(task=task, is_deliberate=True)

        context_block = f"\nRelevant Context:\n{context}\n" if context else ""
        learned_heuristics = memory.recall_heuristic_rules(task, limit=4)
        heuristics_block = f"\nRelevant Operational Invariants:\n" + "\n".join([f"- {h}" for h in learned_heuristics]) if learned_heuristics else ""

        # --- Stage 1: Problem Deconstruction ---
        if on_stage:
            on_stage("deconstruction", "Deconstructing problem requirements and constraints...")

        deconstruct_prompt = f"""Task: {task}{context_block}{heuristics_block}

Deconstruct this task into:
1. Primary Objective & Hard Constraints.
2. Latent Assumptions & Hidden Complexities.
3. Critical Success Invariants."""

        try:
            from aether.brain.multi_provider_router import \
                multi_provider_router
            d_res = multi_provider_router.complete_chat(
                messages=[{"role": "user", "content": deconstruct_prompt}],
                provider=None,
                temperature=0.2,
                max_tokens=2048,
            )
            result.deconstruction = d_res.get("content", "").strip()
        except Exception as e:
            logger.warning(f"Deconstruction fallback: {e}")
            result.deconstruction = f"Objective: Solve '{task}'. Constraints: Maintain stability, clean syntax, verified execution."

        # --- Stage 2a: The Architect Proposes ---
        if on_stage:
            on_stage("architect", "The Architect is formulating an optimal architectural solution...")

        arch_prompt = f"""Task: {task}
Problem Deconstruction:
{result.deconstruction}

Propose an elegant, modular, high-performance architecture and implementation plan."""

        try:
            from aether.brain.multi_provider_router import \
                multi_provider_router
            a_res = multi_provider_router.complete_chat(
                messages=[
                    {"role": "system", "content": ARCHITECT_SYSTEM_PROMPT},
                    {"role": "user", "content": arch_prompt}
                ],
                provider=None,
                temperature=0.3,
                max_tokens=2048,
            )
            result.architect_view = a_res.get("content", "").strip()
        except Exception as e:
            logger.warning(f"Architect fallback: {e}")
            result.architect_view = f"Recommended Architecture: Decoupled modular design isolating state and tool operations."

        # --- Stage 2b: The Critic Attacks & Challenges ---
        if on_stage:
            on_stage("critic", "The Critic is auditing the proposal for edge cases and vulnerabilities...")

        critic_prompt = f"""Task: {task}
Architect's Proposal:
{result.architect_view}

Rigorously challenge this design. What will break? What edge cases, race conditions, or platform issues are missed?"""

        try:
            from aether.brain.multi_provider_router import \
                multi_provider_router
            c_res = multi_provider_router.complete_chat(
                messages=[
                    {"role": "system", "content": CRITIC_SYSTEM_PROMPT},
                    {"role": "user", "content": critic_prompt}
                ],
                provider=None,
                temperature=0.3,
                max_tokens=2048,
            )
            result.critic_view = c_res.get("content", "").strip()
        except Exception as e:
            logger.warning(f"Critic fallback: {e}")
            result.critic_view = "Critique: Verify input boundaries, error handling around system calls, and safe rollback states."

        # --- Stage 3: Master Synthesis ---
        if on_stage:
            on_stage("synthesizer", "The Master Synthesizer is reconciling the debate into a hardened blueprint...")

        synth_prompt = f"""Task: {task}
Architect Proposal:
{result.architect_view[:1800]}

Critic Findings:
{result.critic_view[:1800]}

Synthesize a final, bulletproof execution blueprint reconciling both perspectives."""

        try:
            from aether.brain.multi_provider_router import \
                multi_provider_router
            s_res = multi_provider_router.complete_chat(
                messages=[
                    {"role": "system", "content": SYNTHESIZER_SYSTEM_PROMPT},
                    {"role": "user", "content": synth_prompt}
                ],
                provider=None,
                temperature=0.2,
                max_tokens=2048,
            )
            result.synthesizer_plan = s_res.get("content", "").strip()
        except Exception as e:
            logger.warning(f"Synthesizer fallback: {e}")
            result.synthesizer_plan = (
                f"### Synthesized Execution Blueprint\n"
                f"1. Implement modular structure per Architect proposal.\n"
                f"2. Apply Critic mitigations: Guard against edge cases and validate state transitions.\n"
                f"3. Run end-to-end automated verification."
            )

        result.duration_secs = time.time() - t0

        # Construct comprehensive trace
        result.full_trace = (
            f"<thinking>\n"
            f"=== [SYSTEM 2 COGNITIVE DELIBERATION] ===\n\n"
            f"[STAGE 1: PROBLEM DECONSTRUCTION]\n{result.deconstruction}\n\n"
            f"[STAGE 2A: ARCHITECT PROPOSAL]\n{result.architect_view}\n\n"
            f"[STAGE 2B: COGNITIVE CRITIQUE & VULNERABILITIES]\n{result.critic_view}\n\n"
            f"[STAGE 3: HARDENED SYNTHESIS BLUEPRINT]\n{result.synthesizer_plan}\n"
            f"=========================================\n"
            f"</thinking>"
        )

        return result

    def pre_simulate_action(self, tool_name: str, args: Dict[str, Any]) -> SimulationVerdict:
        """
        Action Pre-Simulation (Mental Sandbox):
        Evaluates potential hazards, destructive side-effects, or preconditions before execution.
        """
        # 1. Shell / Command execution simulation
        if tool_name in ("claude_bash", "execute_system_command", "tool_execute_command"):
            cmd = str(args.get("command", "")).strip()
            cmd_lower = cmd.lower()

            for pat in DESTRUCTIVE_COMMAND_PATTERNS:
                if re.search(pat, cmd_lower):
                    return SimulationVerdict(
                        safe=False,
                        risk_level="CRITICAL",
                        reason=f"Destructive system command pattern detected: '{cmd}'",
                        precautions=["Command blocked by safety pre-simulation."],
                    )

            warnings = []
            if "git reset --hard" in cmd_lower:
                warnings.append("Hard git reset will discard uncommitted working changes.")
            if "npm install -g" in cmd_lower or "pip install" in cmd_lower and "--break-system-packages" in cmd_lower:
                warnings.append("Global dependency mutation detected; prefer localized virtual environments.")

            return SimulationVerdict(
                safe=True,
                risk_level="MEDIUM" if warnings else "LOW",
                reason="Command verified safe for execution.",
                warnings=warnings,
                precautions=["Capture stdout/stderr and verify exit code."],
            )

        # 2. File Write simulation
        if tool_name in ("claude_write", "write_text_file", "tool_write_file"):
            path_str = str(args.get("file_path", args.get("path", "")))
            content = str(args.get("content", ""))
            target = Path(path_str)

            warnings = []
            if target.exists():
                size_kb = target.stat().st_size / 1024
                warnings.append(f"Target file '{target.name}' already exists ({size_kb:.1f} KB). Existing contents will be overwritten.")
            
            if len(content) == 0:
                warnings.append("Attempting to write an empty file.")

            return SimulationVerdict(
                safe=True,
                risk_level="MEDIUM" if warnings else "LOW",
                reason="File write pre-simulation passed.",
                warnings=warnings,
                precautions=["Ensure parent directories exist.", "Backup or inspect prior content if critical."],
            )

        # 3. Surgical Edit simulation
        if tool_name in ("claude_edit", "ACIFileEditor"):
            path_str = str(args.get("file_path", args.get("path", "")))
            old_str = str(args.get("old_str", ""))
            new_str = str(args.get("new_str", ""))
            target = Path(path_str)

            if not target.exists():
                return SimulationVerdict(
                    safe=False,
                    risk_level="HIGH",
                    reason=f"Target file '{path_str}' does not exist. Surgical edit cannot proceed.",
                    precautions=["Verify file path with claude_find or create the file first."],
                )

            try:
                content = target.read_text(encoding="utf-8", errors="replace")
                count = content.count(old_str)
                if count == 0:
                    return SimulationVerdict(
                        safe=False,
                        risk_level="HIGH",
                        reason=f"Target string not found in '{target.name}'. Verify exact line contents with claude_view first.",
                        precautions=["Inspect file lines with 1-based indexing before editing."],
                    )
                elif count > 1:
                    return SimulationVerdict(
                        safe=False,
                        risk_level="HIGH",
                        reason=f"Target string occurs {count} times in '{target.name}'. Match is ambiguous; include surrounding lines.",
                        precautions=["Expand old_str to include unique surrounding lines."],
                    )
            except Exception as e:
                return SimulationVerdict(
                    safe=False,
                    risk_level="HIGH",
                    reason=f"Failed to read file for edit simulation: {e}",
                )

            return SimulationVerdict(
                safe=True,
                risk_level="LOW",
                reason="Surgical string replacement verified unique and exact.",
            )

        # Default safe for read-only tools
        return SimulationVerdict(
            safe=True,
            risk_level="LOW",
            reason=f"Tool '{tool_name}' is read-only or low-impact.",
        )

    def deliberate_situation_and_act(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Full autonomous situation assessment and proactive execution routing.
        """
        from aether.brain.infinite_evolution_orchestrator import \
            infinite_orchestrator
        assessment = infinite_orchestrator.assess_situation(prompt, context)

        logger.info(f"🧠 [ThinkingCortex] Assessed Situation: {assessment.situation_type} (Urgency: {assessment.urgency_level}, Tier: {assessment.recommended_model_tier})")

        if assessment.recommended_model_tier == "SWARM_DEBATE":
            from aether.brain.swarm.swarm_engine import swarm_engine
            swarm_res = swarm_engine.run_mission(prompt)
            return {
                "assessment": assessment,
                "execution_mode": "SWARM_DEBATE",
                "result": swarm_res,
            }
        is_complex, _ = self.should_deliberate(prompt)
        if is_complex:
            delib_res = self.deliberate(prompt)
            return {
                "assessment": assessment,
                "execution_mode": "SYSTEM_2_DELIBERATION",
                "result": delib_res,
            }
        else:
            return {
                "assessment": assessment,
                "execution_mode": "STANDARD_SOVEREIGN",
                "deliberated_actions": assessment.deliberated_actions,
            }


thinking_cortex = ThinkingCortex()

