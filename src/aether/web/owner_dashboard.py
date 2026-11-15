"""
AETHER Owner Dashboard API
===========================
REST endpoints for the owner's autonomous-operator control panel.
All data comes from live files — no fake/hardcoded values.

Mount in server.py:
    from aether.web.owner_dashboard import router as owner_router
    app.include_router(owner_router)
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter
from fastapi.responses import JSONResponse

logger = logging.getLogger("aether.owner_dashboard")

router = APIRouter(prefix="/api/owner", tags=["owner"])

_WORKSPACE  = Path(__file__).resolve().parent.parent.parent.parent
_INTEL_DIR  = _WORKSPACE / "data" / "leon_intelligence"


def _read(path: Path, default: Any = None) -> Any:
    """Thread-safe file read with graceful fallback."""
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning(f"read failed {path}: {e}")
    return default


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/inbox")
async def get_inbox() -> JSONResponse:
    """Return the full owner inbox with summary counts."""
    items: List[Dict] = _read(_INTEL_DIR / "inbox.json", [])
    pending    = [i for i in items if i.get("status") == "pending"]
    approved   = [i for i in items if i.get("status") == "approved"]
    dismissed  = [i for i in items if i.get("status") == "dismissed"]
    need_approval = [i for i in pending if i.get("requires_approval")]
    return JSONResponse({
        "total": len(items),
        "pending": len(pending),
        "needs_approval": len(need_approval),
        "approved": len(approved),
        "dismissed": len(dismissed),
        "items": list(reversed(items[-100:])),  # most recent first, max 100
    })


@router.get("/status")
async def get_status() -> JSONResponse:
    """Return autonomous operator scheduler health and portfolio summary."""
    try:
        from aether.daemon.autonomous_operator import autonomous_operator
        status = autonomous_operator.get_status()
    except Exception as e:
        logger.warning(f"Could not get operator status: {e}")
        status = {"scheduler_running": False, "error": str(e)}
    return JSONResponse(status)


@router.post("/approve/{item_id}")
async def approve_item(item_id: str) -> JSONResponse:
    """Mark an inbox item as approved and trigger relevant downstream action."""
    try:
        from aether.daemon.autonomous_operator import autonomous_operator
        ok = autonomous_operator.mark_approved(item_id)
        return JSONResponse({"success": ok, "item_id": item_id, "status": "approved"})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@router.post("/dismiss/{item_id}")
async def dismiss_item(item_id: str) -> JSONResponse:
    """Mark an inbox item as dismissed."""
    try:
        from aether.daemon.autonomous_operator import autonomous_operator
        ok = autonomous_operator.mark_dismissed(item_id)
        return JSONResponse({"success": ok, "item_id": item_id, "status": "dismissed"})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@router.get("/payments")
async def get_payments() -> JSONResponse:
    """Return all recorded payments (from webhooks + Razorpay sync)."""
    payments: List[Dict] = _read(_INTEL_DIR / "payments.json", [])
    total_inr = sum(p.get("amount_inr", 0) for p in payments)
    return JSONResponse({
        "count": len(payments),
        "total_inr": round(total_inr, 2),
        "payments": list(reversed(payments[-200:])),
    })


@router.get("/leads")
async def get_leads() -> JSONResponse:
    """Return discovered buying-intent lead signals grouped by venture."""
    signals_file = _INTEL_DIR / "lead_signals.json"
    signals: List[Dict] = _read(signals_file, [])
    # Group by venture_slug
    grouped: Dict[str, List] = {}
    for s in signals:
        slug = s.get("venture_slug", "unknown")
        grouped.setdefault(slug, []).append(s)
    # Sort each group by score
    for slug in grouped:
        grouped[slug].sort(key=lambda x: x.get("intent_score", 0), reverse=True)
    return JSONResponse({
        "total": len(signals),
        "by_venture": grouped,
        "signals": sorted(signals, key=lambda x: x.get("intent_score", 0), reverse=True)[:50],
    })


@router.get("/ops_log")
async def get_ops_log() -> JSONResponse:
    """Return the last 50 ops log entries in reverse chronological order."""
    log_file = _INTEL_DIR / "ops_log.jsonl"
    entries: List[Dict] = []
    try:
        if log_file.exists():
            lines = log_file.read_text(encoding="utf-8").strip().splitlines()
            for line in lines[-50:]:
                try:
                    entries.append(json.loads(line))
                except Exception:
                    pass
        entries.reverse()
    except Exception as e:
        logger.warning(f"Could not read ops log: {e}")
    return JSONResponse({"count": len(entries), "entries": entries})


@router.get("/health")
async def dashboard_health() -> JSONResponse:
    """Simple health check for the owner dashboard API."""
    return JSONResponse({"status": "ok", "timestamp": _now()})


# ── New: Asset Registry & AGI Planner ────────────────────────────────────────

@router.get("/assets")
async def get_asset_registry() -> JSONResponse:
    """
    Return a summary of the asset registry (all deployments, tools, models)
    along with the latest asset health evaluation scores.
    """
    try:
        from aether.utils.asset_registry import asset_registry
        from aether.utils.evaluator import compute_portfolio_health
        records = asset_registry.read_all()
        health = compute_portfolio_health(records)
        recent = list(reversed(records[-50:]))  # latest 50
        return JSONResponse({
            "health": health,
            "recent_assets": recent,
            "total": len(records),
        })
    except Exception as e:
        logger.warning(f"asset registry read failed: {e}")
        return JSONResponse({"error": str(e), "total": 0}, status_code=500)


@router.get("/plans")
async def get_agi_plans() -> JSONResponse:
    """Return a list of all AGI plans executed this session."""
    try:
        from aether.agi.planner import agi_planner
        return JSONResponse({"plans": agi_planner.list_plans()})
    except Exception as e:
        return JSONResponse({"plans": [], "error": str(e)})


@router.post("/self-eval")
async def trigger_self_evaluation() -> JSONResponse:
    """
    Manually trigger the self-evaluation job.
    Scores the asset registry immediately without waiting for the nightly cron.
    """
    try:
        from aether.daemon.autonomous_operator import autonomous_operator
        autonomous_operator.job_self_evaluation()
        return JSONResponse({"status": "triggered", "timestamp": _now()})
    except Exception as e:
        return JSONResponse({"status": "error", "detail": str(e)}, status_code=500)


@router.get("/deterministic-mode")
async def get_deterministic_mode() -> JSONResponse:
    """Return current AETHER deterministic mode settings."""
    try:
        from aether.system.deterministic_mode import (DETERMINISTIC,
                                                      ENFORCE_VERIFICATION,
                                                      MAX_TOKENS)
        return JSONResponse({
            "deterministic": DETERMINISTIC,
            "enforce_verification": ENFORCE_VERIFICATION,
            "max_tokens": MAX_TOKENS,
            "description": (
                "AETHER is in hallucination-free deterministic mode — "
                "all LLM calls use temperature=0, top_p=0, seed=42"
                if DETERMINISTIC else
                "Deterministic mode is OFF — LLM outputs may be stochastic"
            ),
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/goals")
async def get_goals() -> JSONResponse:
    """Return the persistent AGI goal queue."""
    try:
        from aether.agi.goal_queue import goal_queue
        return JSONResponse({
            "summary": goal_queue.summary(),
            "goals": list(reversed(goal_queue.list_all()[-50:])),
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/goals/add")
async def add_goal(body: Dict[str, Any]) -> JSONResponse:
    """Add a new goal to the queue. Body: {goal, priority, steps}"""
    try:
        from aether.agi.goal_queue import goal_queue
        gid = goal_queue.add(
            goal=body.get("goal", ""),
            steps=body.get("steps", []),
            priority=int(body.get("priority", 3)),
            source="dashboard",
        )
        return JSONResponse({"id": gid, "status": "queued"})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/goals/process-now")
async def process_next_goal() -> JSONResponse:
    """Immediately process the highest-priority pending goal."""
    try:
        from aether.daemon.autonomous_operator import autonomous_operator
        autonomous_operator.job_process_goals()
        return JSONResponse({"status": "processed", "timestamp": _now()})
    except Exception as e:
        return JSONResponse({"status": "error", "detail": str(e)}, status_code=500)


@router.post("/harvest_intent")
async def harvest_intent_now() -> JSONResponse:
    """Trigger an immediate Pillar 4 Intent Harvesting sweep across all 5 ventures."""
    try:
        from aether.growth.intent_harvester import intent_harvester
        signals = intent_harvester.harvest_all_ventures(min_score=40, max_signals_per_venture=5)
        high_intent = [s for s in signals if s.intent_score >= 65]
        return JSONResponse({
            "status": "success",
            "total_signals_harvested": len(signals),
            "high_intent_queued_for_approval": len(high_intent),
            "signals": [s.to_dict() for s in signals[:20]],
            "timestamp": _now(),
        })
    except Exception as e:
        logger.error(f"Intent harvesting trigger failed: {e}")
        return JSONResponse({"status": "error", "detail": str(e)}, status_code=500)


# ── Pillar 5: LATS Deliberation Trees ────────────────────────────────────────

@router.get("/lats/trees")
async def list_lats_trees() -> JSONResponse:
    """Return all persisted LATS deliberation trees."""
    lats_dir = _INTEL_DIR / "lats_trees"
    trees = []
    if lats_dir.exists():
        for p in sorted(lats_dir.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True)[:30]:
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                trees.append({
                    "id": data.get("id"),
                    "goal": data.get("goal"),
                    "status": data.get("status"),
                    "node_count": len(data.get("nodes", {})),
                    "best_path_length": len(data.get("best_path", [])),
                    "created_at": data.get("created_at"),
                    "completed_at": data.get("completed_at"),
                })
            except Exception:
                pass
    return JSONResponse({"count": len(trees), "trees": trees})


@router.get("/lats/trees/{tree_id}")
async def get_lats_tree(tree_id: str) -> JSONResponse:
    """Return full node structure and best path for a specific LATS tree."""
    tree_file = _INTEL_DIR / "lats_trees" / f"{tree_id}.json"
    if not tree_file.exists():
        return JSONResponse({"error": "Tree not found"}, status_code=404)
    try:
        data = json.loads(tree_file.read_text(encoding="utf-8"))
        return JSONResponse(data)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/lats/solve")
async def solve_with_lats(body: Dict[str, Any]) -> JSONResponse:
    """Run LATS Monte Carlo search for a goal. Body: {goal: str}"""
    goal = body.get("goal", "").strip()
    if not goal:
        return JSONResponse({"error": "goal is required"}, status_code=400)
    try:
        from aether.agi.lats_planner import lats_planner
        from aether.brain.engine import TOOL_DISPATCHER
        lats_planner.register_tools(TOOL_DISPATCHER)
        tree = lats_planner.solve(goal=goal)
        return JSONResponse({
            "id": tree.id,
            "goal": tree.goal,
            "status": tree.status,
            "node_count": len(tree.nodes),
            "best_path": tree.best_path,
            "created_at": tree.created_at,
            "completed_at": tree.completed_at,
        })
    except Exception as e:
        logger.error(f"LATS solve failed: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


# ── Executive Chronobiology & Managing Officer (COO) ─────────────────────────

@router.get("/briefing/morning")
async def get_morning_briefing() -> JSONResponse:
    """Return the latest synthesized Morning Executive Briefing."""
    try:
        from aether.daemon.executive_chronobiology import \
            executive_chronobiology
        briefing = executive_chronobiology.generate_morning_briefing()
        return JSONResponse(briefing.to_dict())
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/briefing/evening")
async def get_evening_review() -> JSONResponse:
    """Return the synthesized Evening Executive Review."""
    try:
        from aether.daemon.executive_chronobiology import \
            executive_chronobiology
        review = executive_chronobiology.generate_evening_review()
        return JSONResponse(review.to_dict())
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/memos")
async def list_decision_memos() -> JSONResponse:
    """Return all executive decision memos."""
    try:
        from aether.growth.executive_decision_memo import executive_memo_engine
        memos = executive_memo_engine.list_all_memos()
        return JSONResponse({"count": len(memos), "memos": memos})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/memos/create")
async def create_decision_memo(body: Dict[str, Any]) -> JSONResponse:
    """Create a new Executive Decision Memo. Body: {title, business_venture, problem_statement}"""
    try:
        from aether.growth.executive_decision_memo import executive_memo_engine
        memo = executive_memo_engine.create_decision_memo(
            title=body.get("title", "Strategic Growth Initiative"),
            business_venture=body.get("business_venture", "CogniGuard Cyber"),
            problem_statement=body.get("problem_statement", "Scale commercial venture performance"),
            action_payload=body.get("action_payload"),
        )
        return JSONResponse(memo.to_dict())
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ── Phase 1 Immediate Evolutions Endpoints ────────────────────────────────────

@router.get("/podcast/latest")
async def get_latest_podcast() -> JSONResponse:
    """Generate and return the 90-second Morning Executive Audio Podcast."""
    try:
        from aether.daemon.executive_audio_podcast import \
            executive_audio_podcast
        podcast_data = executive_audio_podcast.generate_latest_podcast()
        return JSONResponse(podcast_data)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/guardian/snapshot")
async def get_guardian_snapshot() -> JSONResponse:
    """Return live ambient desktop context (active window, clipboard classification, battery)."""
    try:
        from aether.daemon.windows_system_guardian import windows_guardian
        snapshot = windows_guardian.capture_ambient_snapshot()
        return JSONResponse(snapshot.to_dict())
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/outbound/dispatch")
async def dispatch_outbound_lead(body: Dict[str, Any]) -> JSONResponse:
    """Dispatch an approved lead's value-first diagnostic outreach via email or public script."""
    lead_id = body.get("lead_id", "")
    channel = body.get("channel", "public_reply_script")
    try:
        from aether.growth.outbound_dispatcher import outbound_dispatcher
        if channel == "smtp_email":
            res = outbound_dispatcher.dispatch_email(
                recipient_email=body.get("recipient_email", ""),
                subject=body.get("subject", "Automated Diagnostic Report"),
                diagnostic_html=body.get("diagnostic_html", "<p>Diagnostic Report</p>"),
                lead_id=lead_id,
                venture_name=body.get("venture_name", "LEON Venture")
            )
        else:
            res = outbound_dispatcher.format_public_reply(
                lead_id=lead_id,
                author=body.get("author", "User"),
                source_url=body.get("source_url", ""),
                venture_name=body.get("venture_name", "LEON Venture"),
                diagnostic_summary=body.get("diagnostic_summary", ""),
                free_value=body.get("free_value", ""),
                cta=body.get("cta", "")
            )
        return JSONResponse(res.to_dict())
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ── Cloud Personal Assistant Endpoints (Calendar, Tasks, Email) ──────────────

@router.get("/calendar")
async def get_calendar_events() -> JSONResponse:

    """Return all calendar events and today's schedule."""
    try:
        from aether.tools.cloud_calendar_agent import cloud_calendar_agent
        events = cloud_calendar_agent._read_events()
        todays = cloud_calendar_agent.get_daily_agenda()
        return JSONResponse({
            "total_events": len(events),
            "today_events_count": len(todays),
            "today_schedule": todays,
            "all_events": list(reversed(events[-50:])),
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/calendar/sync")
async def sync_calendar_feed() -> JSONResponse:
    """Trigger an immediate ICS calendar feed synchronization."""
    try:
        from aether.tools.cloud_calendar_agent import cloud_calendar_agent
        count = cloud_calendar_agent.sync_ics_feed()
        return JSONResponse({"status": "synced", "new_events_count": count, "timestamp": _now()})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/tasks")
async def get_cloud_tasks() -> JSONResponse:
    """Return all scheduled cloud alarms, reminders, and completed tasks."""
    try:
        from aether.tools.cloud_tasks_alarms import cloud_tasks
        all_tasks = cloud_tasks._read_tasks()
        active = cloud_tasks.list_active_tasks()
        return JSONResponse({
            "total_tasks": len(all_tasks),
            "active_tasks_count": len(active),
            "active_tasks": active,
            "all_tasks": list(reversed(all_tasks[-50:])),
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/tasks/add")
async def add_cloud_task(body: Dict[str, Any]) -> JSONResponse:
    """Add a new alarm/reminder from natural text or structured parameters."""
    text = body.get("text", "")
    try:
        from aether.tools.cloud_tasks_alarms import cloud_tasks
        if text:
            reply = cloud_tasks.create_reminder_from_text(text)
            return JSONResponse({"status": "ok", "message": reply})
        else:
            return JSONResponse({"error": "text is required"}, status_code=400)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/email/triage-now")
async def triage_email_now() -> JSONResponse:
    """Trigger an immediate IMAP email inbox check and Eisenhower triage."""
    try:
        from aether.tools.cloud_email_agent import cloud_email_agent
        triaged = cloud_email_agent.check_inbox_and_triage(limit=10)
        return JSONResponse({
            "status": "ok",
            "triaged_count": len(triaged),
            "results": [t.to_dict() for t in triaged],
            "timestamp": _now(),
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)






