"""
AETHER Goal Queue
=================
Persistent, priority-ordered queue of high-level goals for AETHER+LEON.

Goals survive server restarts (stored in data/leon_intelligence/goal_queue.json).
The AutonomousOperator picks the highest-priority unstarted goal every 4 hours
and executes it via AgiPlanner.

Priority: 1 = critical, 5 = low. Lower number runs first.
"""

from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

_WORKSPACE  = Path(__file__).resolve().parents[3]
_QUEUE_FILE = _WORKSPACE / "data" / "leon_intelligence" / "goal_queue.json"
_QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)

_LOCK = threading.Lock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat() + "Z"


def _load() -> List[Dict]:
    try:
        if _QUEUE_FILE.exists():
            return json.loads(_QUEUE_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return []


def _save(goals: List[Dict]) -> None:
    _QUEUE_FILE.write_text(json.dumps(goals, indent=2, ensure_ascii=False), encoding="utf-8")


class GoalQueue:
    """Thread-safe persistent goal queue."""

    def add(
        self,
        goal: str,
        steps: Optional[List[Dict]] = None,
        priority: int = 3,
        source: str = "user",
        tags: Optional[List[str]] = None,
    ) -> str:
        """Add a goal. Returns the new goal ID."""
        gid = str(uuid.uuid4())[:8]
        entry = {
            "id": gid,
            "goal": goal,
            "steps": steps or [],
            "priority": max(1, min(5, priority)),
            "source": source,
            "tags": tags or [],
            "status": "pending",
            "created_at": _now(),
            "started_at": None,
            "completed_at": None,
            "plan_id": None,
            "result": None,
        }
        with _LOCK:
            goals = _load()
            goals.append(entry)
            _save(goals)
        return gid

    def next_pending(self) -> Optional[Dict]:
        """Return highest-priority pending goal (lowest priority number first)."""
        with _LOCK:
            goals = _load()
        pending = [g for g in goals if g["status"] == "pending"]
        if not pending:
            return None
        return sorted(pending, key=lambda g: (g["priority"], g["created_at"]))[0]

    def mark_running(self, goal_id: str) -> None:
        with _LOCK:
            goals = _load()
            for g in goals:
                if g["id"] == goal_id:
                    g["status"] = "running"
                    g["started_at"] = _now()
            _save(goals)

    def mark_done(self, goal_id: str, plan_id: str, result: str) -> None:
        with _LOCK:
            goals = _load()
            for g in goals:
                if g["id"] == goal_id:
                    g["status"] = "completed"
                    g["plan_id"] = plan_id
                    g["result"] = result[:500]
                    g["completed_at"] = _now()
            _save(goals)

    def mark_failed(self, goal_id: str, reason: str) -> None:
        with _LOCK:
            goals = _load()
            for g in goals:
                if g["id"] == goal_id:
                    g["status"] = "failed"
                    g["result"] = reason[:500]
                    g["completed_at"] = _now()
            _save(goals)

    def list_all(self, status: Optional[str] = None) -> List[Dict]:
        with _LOCK:
            goals = _load()
        if status:
            return [g for g in goals if g["status"] == status]
        return goals

    def summary(self) -> Dict[str, Any]:
        goals = self.list_all()
        by_status: Dict[str, int] = {}
        for g in goals:
            by_status[g["status"]] = by_status.get(g["status"], 0) + 1
        return {"total": len(goals), "by_status": by_status}


goal_queue = GoalQueue()
