"""
AETHER Agency Specialists FastAPI Router
========================================
Exposes endpoints for exploring, dispatching, and auditing the 267+
Agency Specialists from msitarzewski/agency-agents across 18 divisions.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logger = logging.getLogger("aether.agency_router")

router = APIRouter(prefix="/api/agency", tags=["Agency Specialists"])


class DispatchRequest(BaseModel):
    agent: str
    prompt: str
    context: Optional[str] = ""
    provider: Optional[str] = None


@router.get("/vault")
async def get_agency_vault() -> JSONResponse:
    """Audit API keys, inference providers, and training cluster status."""
    from aether.brain.agency_vault import agency_vault
    return JSONResponse(agency_vault.audit_credentials())


@router.get("/divisions")
async def get_divisions() -> JSONResponse:
    """List all 18 operational agency divisions with specialist counts."""
    from aether.brain.agency_specialists_engine import agency_engine
    return JSONResponse({
        "divisions": agency_engine.list_divisions(),
        "total_agents": len(agency_engine._agents),
    })


@router.get("/agents")
async def get_agents(division: Optional[str] = None) -> JSONResponse:
    """List specialized agency agents, optionally filtered by division."""
    from aether.brain.agency_specialists_engine import agency_engine
    agents = agency_engine.list_agents(division=division)
    return JSONResponse({
        "division": division or "all",
        "count": len(agents),
        "agents": agents,
    })


@router.get("/recommend")
async def recommend_agents(goal: str = Query(..., description="Project or task description")) -> JSONResponse:
    """Recommend the top-fit specialists for a technical or business objective."""
    from aether.brain.agency_specialists_engine import agency_engine
    recs = agency_engine.recommend_specialists(goal, top_k=5)
    return JSONResponse({"goal": goal, "recommendations": recs})


@router.post("/dispatch")
async def dispatch_agent(req: DispatchRequest) -> JSONResponse:
    """Execute a task with any of the 267+ specialized agency agents."""
    from aether.brain.agency_specialists_engine import agency_engine
    res = agency_engine.dispatch_specialist(
        slug_or_name=req.agent,
        user_prompt=req.prompt,
        context=req.context or "",
        provider=req.provider,
    )
    status_code = 200 if res.get("status") == "completed" else 400
    return JSONResponse(res, status_code=status_code)


@router.post("/train/sync")
async def sync_training_and_memory() -> JSONResponse:
    """Ingest agency procedural rules into SQLite FTS5 memory and compile instruction dataset."""
    from aether.brain.agency_training_synthesizer import \
        agency_training_synthesizer
    rules_added = agency_training_synthesizer.extract_heuristics_and_rules(max_agents=100)
    dataset_res = agency_training_synthesizer.synthesize_finetuning_dataset()
    return JSONResponse({
        "status": "synchronized",
        "rules_injected_to_memory": rules_added,
        "dataset_samples": dataset_res["samples_count"],
        "dataset_path": dataset_res["dataset_path"],
    })
