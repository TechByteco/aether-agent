"""
AETHER AGI Planner
==================
A deterministic, self-directing task planner for AETHER + LEON.

Design principles:
  • No free-form LLM generation unless all rule-based paths are exhausted.
  • Every task is decomposed into a typed Plan (steps + expected outputs).
  • Each step is verified before the next step begins.
  • Failed steps trigger the Reflexion Engine for automatic root-cause analysis.
  • Completed plans are committed to the episodic memory for future learning.
  • The planner iterates (up to MAX_ITERATIONS) before giving up and logging
    an unresolved task entry in the ops log.

Execution flow:
  User goal → Planner.create_plan() → [Step₁ → verify → Step₂ → verify … → Step_n]
    → Planner.commit_plan() → memory + asset_registry → done.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from aether.system.deterministic_mode import (DETERMINISTIC,
                                              ENFORCE_VERIFICATION,
                                              verify_output)

logger = logging.getLogger("aether.agi.planner")

_WORKSPACE = Path(__file__).resolve().parents[3]
_PLANS_DIR = _WORKSPACE / "data" / "leon_intelligence" / "plans"
_PLANS_DIR.mkdir(parents=True, exist_ok=True)

MAX_ITERATIONS = 5          # Max retry attempts per plan step
STEP_TIMEOUT_S  = 120       # Seconds before a step is marked timed-out


class StepStatus(str, Enum):
    PENDING   = "pending"
    RUNNING   = "running"
    DONE      = "done"
    FAILED    = "failed"
    SKIPPED   = "skipped"


class PlanStatus(str, Enum):
    CREATED   = "created"
    RUNNING   = "running"
    COMPLETED = "completed"
    FAILED    = "failed"
    PARTIAL   = "partial"


@dataclass
class PlanStep:
    """A single atomic action within a Plan."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    tool: str = ""                  # Name of the AETHER tool to call
    args: Dict[str, Any] = field(default_factory=dict)
    expected_output_schema: Optional[str] = None   # Key into SCHEMAS dict
    status: StepStatus = StepStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    attempts: int = 0
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

    def to_dict(self) -> Dict:
        d = asdict(self)
        d["status"] = self.status.value
        return d


@dataclass
class Plan:
    """A full multi-step execution plan."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    goal: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat() + "Z")
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat() + "Z")
    status: PlanStatus = PlanStatus.CREATED
    steps: List[PlanStep] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    completed_at: Optional[str] = None

    def to_dict(self) -> Dict:
        d = asdict(self)
        d["status"] = self.status.value
        d["steps"] = [s.to_dict() for s in self.steps]
        return d

    def save(self) -> None:
        """Persist plan to disk for recovery/auditability."""
        self.updated_at = datetime.now(timezone.utc).isoformat() + "Z"
        path = _PLANS_DIR / f"{self.id}.json"
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")


class AgiPlanner:
    """
    Deterministic AGI Planner.

    Accepts a high-level goal, decomposes it into typed steps using a
    rule-based decomposer (with optional LLM enrichment in non-deterministic
    mode), executes each step via the TOOL_DISPATCHER, verifies results,
    and persists everything to disk + memory.
    """

    def __init__(self, tool_dispatcher: Optional[Dict[str, Callable]] = None) -> None:
        self._tools: Dict[str, Callable] = tool_dispatcher or {}
        self._active_plans: Dict[str, Plan] = {}

    # ── Tool registration ────────────────────────────────────────────────────

    def register_tool(self, name: str, fn: Callable) -> None:
        """Register a callable tool so the planner can dispatch to it."""
        self._tools[name] = fn

    def register_tools(self, tools: Dict[str, Callable]) -> None:
        """Bulk-register a dict of {name: callable}."""
        self._tools.update(tools)

    # ── Plan creation ────────────────────────────────────────────────────────

    def create_plan(
        self,
        goal: str,
        steps: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Plan:
        """
        Create a Plan from a goal description and a list of step dicts.

        Each step dict must contain at minimum:
            { "name": str, "tool": str, "args": dict }
        Optionally:
            { "expected_output_schema": str }  — key into SCHEMAS

        Returns the created Plan (not yet executed).
        """
        plan = Plan(
            goal=goal,
            steps=[
                PlanStep(
                    name=s.get("name", f"step_{i}"),
                    tool=s.get("tool", ""),
                    args=s.get("args", {}),
                    expected_output_schema=s.get("expected_output_schema"),
                )
                for i, s in enumerate(steps)
            ],
            metadata=metadata or {},
        )
        self._active_plans[plan.id] = plan
        plan.save()
        logger.info("Plan created: %s — goal: '%s' — %d steps", plan.id, goal, len(plan.steps))
        return plan

    # ── Execution ────────────────────────────────────────────────────────────

    def execute_plan(self, plan: Plan) -> Plan:
        """
        Execute a Plan step by step.

        Each step:
          1. Looks up the tool in self._tools.
          2. Calls the tool with step.args.
          3. Verifies the result via the deterministic verification layer.
          4. On failure, retries up to MAX_ITERATIONS, then marks FAILED.
          5. Persists progress after every step.

        Returns the Plan with all steps updated.
        """
        plan.status = PlanStatus.RUNNING
        plan.save()

        for step in plan.steps:
            if step.status == StepStatus.DONE:
                continue  # allow resuming partial plans

            step.status = StepStatus.RUNNING
            step.started_at = datetime.now(timezone.utc).isoformat() + "Z"

            success = False
            for attempt in range(1, MAX_ITERATIONS + 1):
                step.attempts = attempt
                try:
                    fn = self._tools.get(step.tool)
                    if fn is None:
                        raise LookupError(
                            f"Tool '{step.tool}' not registered with AgiPlanner. "
                            f"Available: {sorted(self._tools)}"
                        )

                    result = fn(**step.args)

                    # Verify output if schema is declared
                    if step.expected_output_schema and ENFORCE_VERIFICATION:
                        if not verify_output(
                            result if isinstance(result, dict) else {"result": result},
                            schema_name=step.expected_output_schema,
                        ):
                            raise ValueError(
                                f"Step '{step.name}' output failed verification "
                                f"(schema='{step.expected_output_schema}')."
                            )

                    step.result = result
                    step.status = StepStatus.DONE
                    step.completed_at = datetime.now(timezone.utc).isoformat() + "Z"
                    step.error = None
                    success = True
                    logger.info(
                        "Plan %s step '%s' DONE (attempt %d)", plan.id, step.name, attempt
                    )
                    break

                except Exception as exc:
                    step.error = str(exc)
                    logger.warning(
                        "Plan %s step '%s' attempt %d FAILED: %s",
                        plan.id, step.name, attempt, exc,
                    )
                    if attempt < MAX_ITERATIONS:
                        time.sleep(min(2 ** attempt, 30))  # exponential back-off

            if not success:
                step.status = StepStatus.FAILED
                step.completed_at = datetime.now(timezone.utc).isoformat() + "Z"
                logger.error(
                    "Plan %s step '%s' exhausted %d attempts — marking FAILED.",
                    plan.id, step.name, MAX_ITERATIONS,
                )
                # Trigger reflexion engine to derive an invariant from this failure
                self._trigger_reflexion(plan, step)

            plan.save()

        # Final plan status
        failed = [s for s in plan.steps if s.status == StepStatus.FAILED]
        plan.status = (
            PlanStatus.COMPLETED if not failed
            else (PlanStatus.PARTIAL if len(failed) < len(plan.steps) else PlanStatus.FAILED)
        )
        plan.completed_at = datetime.now(timezone.utc).isoformat() + "Z"
        plan.save()

        logger.info(
            "Plan %s finished with status=%s (%d/%d steps passed)",
            plan.id, plan.status.value,
            sum(1 for s in plan.steps if s.status == StepStatus.DONE),
            len(plan.steps),
        )
        self._commit_to_memory(plan)
        return plan

    # ── Reflexion integration ────────────────────────────────────────────────

    @staticmethod
    def _trigger_reflexion(plan: Plan, step: PlanStep) -> None:
        """Forward failures to the ReflexionEngine for invariant derivation."""
        try:
            from aether.brain.reflexion_engine import reflexion_engine
            reflexion_engine.reflect_and_heal(
                original_task=plan.goal,
                failed_tool=step.tool,
                args=step.args,
                error_message=step.error or "Unknown error",
            )
        except Exception as e:
            logger.warning("Reflexion engine error: %s", e)

    # ── Memory commit ────────────────────────────────────────────────────────

    @staticmethod
    def _commit_to_memory(plan: Plan) -> None:
        """Store completed plan summary in episodic memory."""
        try:
            from aether.memory.store import memory
            summary = (
                f"[PLAN:{plan.status.value}] Goal='{plan.goal}' "
                f"Steps={len(plan.steps)} "
                f"OK={sum(1 for s in plan.steps if s.status == StepStatus.DONE)}"
            )
            memory.add_episode(
                content=summary,
                source="agi_planner",
                metadata={"plan_id": plan.id, "status": plan.status.value},
            )
        except Exception as e:
            logger.debug("Memory commit skipped: %s", e)

    # ── Convenience helpers ──────────────────────────────────────────────────

    def run_goal(
        self,
        goal: str,
        steps: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Plan:
        """One-call shortcut: create + execute a plan."""
        plan = self.create_plan(goal, steps, metadata)
        return self.execute_plan(plan)

    def get_plan(self, plan_id: str) -> Optional[Plan]:
        """Retrieve an active plan by ID."""
        return self._active_plans.get(plan_id)

    def list_plans(self) -> List[Dict[str, Any]]:
        """Return summaries of all plans in memory."""
        return [
            {
                "id": p.id,
                "goal": p.goal,
                "status": p.status.value,
                "steps": len(p.steps),
                "created_at": p.created_at,
            }
            for p in self._active_plans.values()
        ]


# ── Singleton ─────────────────────────────────────────────────────────────────
agi_planner = AgiPlanner()
