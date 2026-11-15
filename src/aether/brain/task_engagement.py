"""
AETHER Proactive Multi-Turn Task Engagement Engine
==================================================
Transforms AETHER into a proactive, high-agency engineering partner:
1. Hierarchical Task DAG (Directed Acyclic Graph):
   - Decomposes high-level objectives into interconnected tasks with dependencies.
   - States: PENDING -> IN_PROGRESS -> VERIFIED -> COMPLETED (or BLOCKED).
   - Checkpoints state to disk (`data/memory/active_engagements.json`) for persistence across sessions.
2. Dynamic Persona Adaptation:
   - Shifts cognitive posture according to task needs:
     * ARCHITECT: High-level system design, modular decoupling, boundary contracts.
     * BUILDER: Action-first surgical implementation, unified diffs, zero placeholders.
     * SECURITY_AUDITOR: Threat modeling, exploit surfaces, input sanitization, BOLA/IDOR.
     * PERFORMANCE_PROFILER: Memory pressure, latency reduction, cache alignment, hardware sentry.
     * UI_ARTISAN: Anti-slop visual polish, OLED obsidian themes, Framer Motion spring physics.
3. Proactive Auto-Remediation & Milestone Telemetry:
   - Provides live visual DAG progress trees and next-action recommendations.
"""

import json
import logging
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from aether.config import config
from aether.memory.store import memory

logger = logging.getLogger("aether.task_engagement")


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    VERIFIED = "verified"
    COMPLETED = "completed"


class EngagementPersona(str, Enum):
    ARCHITECT = "ARCHITECT"
    BUILDER = "BUILDER"
    SECURITY_AUDITOR = "SECURITY_AUDITOR"
    PERFORMANCE_PROFILER = "PERFORMANCE_PROFILER"
    UI_ARTISAN = "UI_ARTISAN"


PERSONA_DIRECTIVES: Dict[EngagementPersona, str] = {
    EngagementPersona.ARCHITECT: (
        "Focus on system architecture, modular decomposition, interface boundaries, "
        "minimal shared state, and long-term maintainability. Prioritize structural clarity."
    ),
    EngagementPersona.BUILDER: (
        "Operate as a high-agency surgical implementer. Write complete production code with "
        "zero placeholders or TODOs. Use exact string replacements and verify changes with tests."
    ),
    EngagementPersona.SECURITY_AUDITOR: (
        "Audit with a zero-trust mindset. Scan for injection flaws, authentication bypasses, "
        "BOLA/IDOR vulnerabilities, sensitive data leakage, and improper boundary sanitization."
    ),
    EngagementPersona.PERFORMANCE_PROFILER: (
        "Optimize for sub-millisecond latency, minimal heap allocations, cache locality, "
        "and strict hardware resource preservation (<2.0 GB active RAM on Snapdragon X)."
    ),
    EngagementPersona.UI_ARTISAN: (
        "Enforce agency-grade visual design: OLED dark mode (#09090b), 1px subtle borders "
        "(rgba(255,255,255,0.08)), Framer Motion spring physics, and flawless typography rhythm."
    ),
}


@dataclass
class DAGNode:
    id: str
    title: str
    description: str
    dependencies: List[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    assigned_persona: EngagementPersona = EngagementPersona.BUILDER
    result_summary: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())


class TaskEngagementEngine:
    def __init__(self):
        self.data_dir = config.data_dir
        self.storage_file = self.data_dir / "active_engagements.json"
        self.active_objective: str = ""
        self.nodes: Dict[str, DAGNode] = {}
        self.active_persona: EngagementPersona = EngagementPersona.BUILDER
        self._load_state()

    def _save_state(self) -> None:
        """Persist active engagement DAG to disk."""
        try:
            payload = {
                "active_objective": self.active_objective,
                "active_persona": self.active_persona.value,
                "nodes": {nid: asdict(node) for nid, node in self.nodes.items()},
                "updated_at": datetime.now().isoformat(),
            }
            self.storage_file.parent.mkdir(parents=True, exist_ok=True)
            self.storage_file.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            logger.warning(f"Failed to persist engagement state: {e}")

    def _load_state(self) -> None:
        """Restore active engagement DAG from disk if present."""
        if not self.storage_file.exists():
            return
        try:
            data = json.loads(self.storage_file.read_text(encoding="utf-8"))
            self.active_objective = data.get("active_objective", "")
            p_val = data.get("active_persona", "BUILDER")
            self.active_persona = EngagementPersona(p_val) if p_val in EngagementPersona._value2member_map_ else EngagementPersona.BUILDER
            raw_nodes = data.get("nodes", {})
            self.nodes = {}
            for nid, ndata in raw_nodes.items():
                self.nodes[nid] = DAGNode(
                    id=ndata["id"],
                    title=ndata["title"],
                    description=ndata.get("description", ""),
                    dependencies=ndata.get("dependencies", []),
                    status=TaskStatus(ndata.get("status", "pending")),
                    assigned_persona=EngagementPersona(ndata.get("assigned_persona", "BUILDER")),
                    result_summary=ndata.get("result_summary", ""),
                    created_at=ndata.get("created_at", ""),
                    updated_at=ndata.get("updated_at", ""),
                )
        except Exception as e:
            logger.warning(f"Failed to load engagement state: {e}")

    # ── Persona Management ────────────────────────────────────────────────────

    def set_persona(self, persona: EngagementPersona) -> str:
        """Explicitly switch the active engagement cognitive posture."""
        self.active_persona = persona
        self._save_state()
        return f"Cognitive posture switched to **{persona.value}**: {PERSONA_DIRECTIVES[persona]}"

    def get_persona_directive(self) -> str:
        """Return the current persona directive string for prompt injection."""
        return f"Active Posture [{self.active_persona.value}]: {PERSONA_DIRECTIVES[self.active_persona]}"

    # ── Hierarchical Task DAG Creation & Management ───────────────────────────

    def create_engagement_dag(self, objective: str, steps: Optional[List[Dict[str, Any]]] = None) -> str:
        """
        Initialize or decompose a high-level goal into a hierarchical DAG of actionable tasks.
        """
        self.active_objective = objective.strip()
        self.nodes = {}

        if steps:
            for s in steps:
                nid = str(s.get("id", f"T{len(self.nodes)+1}"))
                persona_val = s.get("persona", "BUILDER")
                assigned_p = EngagementPersona(persona_val) if persona_val in EngagementPersona._value2member_map_ else EngagementPersona.BUILDER
                self.nodes[nid] = DAGNode(
                    id=nid,
                    title=s.get("title", f"Task {nid}"),
                    description=s.get("description", ""),
                    dependencies=s.get("dependencies", []),
                    status=TaskStatus.PENDING,
                    assigned_persona=assigned_p,
                )
        else:
            # Default 4-step canonical engineering engagement DAG
            self.nodes = {
                "T1": DAGNode(
                    id="T1",
                    title="System Architecture & Boundary Modeling",
                    description="Deconstruct requirements, model interfaces, and map data flows.",
                    dependencies=[],
                    status=TaskStatus.IN_PROGRESS,
                    assigned_persona=EngagementPersona.ARCHITECT,
                ),
                "T2": DAGNode(
                    id="T2",
                    title="Surgical Core Implementation",
                    description="Write modular components with zero placeholders and verified diffs.",
                    dependencies=["T1"],
                    status=TaskStatus.PENDING,
                    assigned_persona=EngagementPersona.BUILDER,
                ),
                "T3": DAGNode(
                    id="T3",
                    title="Security Audit & Boundary Hardening",
                    description="Audit for vulnerabilities, input boundaries, and invariant enforcement.",
                    dependencies=["T2"],
                    status=TaskStatus.PENDING,
                    assigned_persona=EngagementPersona.SECURITY_AUDITOR,
                ),
                "T4": DAGNode(
                    id="T4",
                    title="End-to-End Automated Verification",
                    description="Run test suite and verify clean execution codes and regression safety.",
                    dependencies=["T3"],
                    status=TaskStatus.VERIFIED,
                    assigned_persona=EngagementPersona.PERFORMANCE_PROFILER,
                ),
            }

        self._save_state()
        return self.format_dag_markdown()

    def advance_task(self, task_id: str, result_summary: str = "", new_status: TaskStatus = TaskStatus.COMPLETED) -> str:
        """
        Mark a task completed or verified, unblock dependent tasks, and update engagement state.
        """
        if task_id not in self.nodes:
            return f"Task '{task_id}' not found in active engagement DAG."

        node = self.nodes[task_id]
        node.status = new_status
        node.result_summary = result_summary
        node.updated_at = datetime.now().isoformat()

        # Check and activate dependent tasks whose prerequisites are now complete
        unblocked = []
        for nid, other in self.nodes.items():
            if other.status == TaskStatus.PENDING:
                all_deps_done = all(
                    self.nodes[dep].status in (TaskStatus.COMPLETED, TaskStatus.VERIFIED)
                    for dep in other.dependencies
                    if dep in self.nodes
                )
                if all_deps_done:
                    other.status = TaskStatus.IN_PROGRESS
                    # Auto-adapt persona to the newly active task
                    self.active_persona = other.assigned_persona
                    unblocked.append(other.id)

        self._save_state()
        unblocked_msg = f" Unblocked next task(s): {', '.join(unblocked)}" if unblocked else ""
        return f"✓ Task [{task_id}] marked {new_status.value}.{unblocked_msg}"

    def get_current_actionable_task(self) -> Optional[DAGNode]:
        """Return the next active or in-progress task in the DAG."""
        for node in self.nodes.values():
            if node.status == TaskStatus.IN_PROGRESS:
                return node
        for node in self.nodes.values():
            if node.status == TaskStatus.PENDING:
                all_deps_done = all(
                    self.nodes[dep].status in (TaskStatus.COMPLETED, TaskStatus.VERIFIED)
                    for dep in node.dependencies
                    if dep in self.nodes
                )
                if all_deps_done:
                    node.status = TaskStatus.IN_PROGRESS
                    self._save_state()
                    return node
        return None

    # ── Telemetry & Markdown Formatting ───────────────────────────────────────

    def format_dag_markdown(self) -> str:
        """Format the active engagement DAG into clean Markdown telemetry."""
        if not self.active_objective:
            return "No active engagement DAG. Start one with `/engage <objective>`."

        status_symbols = {
            TaskStatus.PENDING: "⏳",
            TaskStatus.IN_PROGRESS: "🚀",
            TaskStatus.BLOCKED: "🛑",
            TaskStatus.VERIFIED: "🔍",
            TaskStatus.COMPLETED: "✅",
        }

        completed_cnt = sum(1 for n in self.nodes.values() if n.status == TaskStatus.COMPLETED)
        total_cnt = len(self.nodes)

        lines = [
            f"### 🧭 Active Task Engagement DAG ({completed_cnt}/{total_cnt} Completed)",
            f"**Objective:** {self.active_objective}",
            f"**Current Posture:** `{self.active_persona.value}`",
            "",
            "| ID | Status | Persona | Task & Dependencies |",
            "| :--- | :---: | :---: | :--- |",
        ]

        for nid, n in self.nodes.items():
            sym = status_symbols.get(n.status, "⏳")
            deps_str = f" *(requires: {', '.join(n.dependencies)})*" if n.dependencies else ""
            lines.append(f"| **{nid}** | {sym} `{n.status.value.upper()}` | `{n.assigned_persona.value}` | **{n.title}**{deps_str} |")

        actionable = self.get_current_actionable_task()
        if actionable:
            lines.append(f"\n👉 **Immediate Focus:** [{actionable.id}] {actionable.title}")
            lines.append(f"   *{actionable.description}*")
        elif completed_cnt == total_cnt and total_cnt > 0:
            lines.append("\n🎉 **All DAG milestones successfully verified and completed!**")

        return "\n".join(lines)


task_engagement = TaskEngagementEngine()
