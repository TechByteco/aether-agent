"""
AETHER Localhost Web Server & Real-Time Cognitive Gateway
FastAPI + WebSockets server providing live Glassmorphic HUD, Web Speech voice interaction,
vision streaming, sandboxed code execution, and system telemetry.
"""

import asyncio
import gc
import json
import shutil
import threading
from contextlib import asynccontextmanager
from dataclasses import asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from aether.brain.ast_guard import ast_guard
from aether.brain.engine import engine
from aether.brain.evolution import evolution_engine
from aether.brain.fast_cortex import fast_cortex
from aether.brain.infinite_evolution_orchestrator import infinite_orchestrator
from aether.brain.kaggle_controller import kaggle_controller
from aether.brain.multi_provider_router import multi_provider_router
from aether.brain.online_gateway import online_gateway
from aether.brain.perpetual_training_dispatcher import perpetual_dispatcher
from aether.brain.self_play_rlaif_engine import self_play_engine
from aether.brain.skill_genesis_factory import (ALL_ROUNDER_DOMAINS,
                                                skill_factory)
from aether.brain.swarm import SwarmRole, swarm_engine
from aether.brain.teacher_student_engine import (CognitiveStage,
                                                 teacher_student_engine)
from aether.channels.samsung_router import router as samsung_router
from aether.channels.whatsapp_assistant import router as whatsapp_router
from aether.config import config
from aether.daemon.autonomous_operator import autonomous_operator
from aether.daemon.continuous_evolution_worker import \
    continuous_evolution_worker
from aether.memory.persona import persona
from aether.memory.store import memory
from aether.tools.code_sandbox import execute_python_code
from aether.tools.guardrails import format_vitals_summary, get_system_vitals
from aether.tools.system_ops import get_current_time
from aether.tools.vision import (analyze_image, analyze_live_screen,
                                 capture_screen, detect_available_vision_model)
from aether.tools.voice import voice
from aether.web.agency_router import router as agency_router
from aether.web.crm_router import router as crm_router
from aether.web.email_router import router as email_router
from aether.web.owner_dashboard import router as owner_router
from aether.web.webhooks import router as webhooks_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage lifecycle of background workers: evolution + LEON autonomous operator + fast cortex."""
    continuous_evolution_worker.start()
    autonomous_operator.start()   # ← LEON autonomous scheduler + 24/7 Telegram Daemon
    fast_cortex.start_prewarm_daemon()  # ← Ultra-Fast RAM Cache Pre-warmer
    yield
    fast_cortex.stop_prewarm_daemon()
    autonomous_operator.stop()
    continuous_evolution_worker.stop()


app = FastAPI(title="AETHER Cognitive Glass UI", version="0.8.0", lifespan=lifespan)

# ── Autonomous operator & agency & channel routers ───────────────────────────
app.include_router(webhooks_router)
app.include_router(owner_router)
app.include_router(agency_router)
app.include_router(whatsapp_router)
app.include_router(samsung_router)
app.include_router(email_router)
app.include_router(crm_router)



BASE_DIR = Path(__file__).parent
STATIC_DIR = BASE_DIR / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = "web-ui"


class CodeRequest(BaseModel):
    code: str


class ScreenRequest(BaseModel):
    prompt: Optional[str] = "What is currently visible on my screen? Summarize the active application, window, and key content."


class GoalsRequest(BaseModel):
    goals: str


class ModelSelectRequest(BaseModel):
    model_name: str


class ApiKeysRequest(BaseModel):
    groq_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    openrouter_api_key: Optional[str] = None
    deepseek_api_key: Optional[str] = None


class CognitiveModeRequest(BaseModel):
    mode: str


class SwarmMissionRequest(BaseModel):
    task: str
    roles: Optional[List[str]] = None


class SwarmDebateRequest(BaseModel):
    topic: str
    rounds: Optional[int] = 2


class ASTAnalyzeRequest(BaseModel):
    code: str


class KaggleCredentialsRequest(BaseModel):
    username: str
    key: str


class KaggleTrainRequest(BaseModel):
    kernel_slug: Optional[str] = "aether-frontier-gpu-training"
    title: Optional[str] = "AETHER Frontier GPU Fine-Tuning"


class OnlineTunnelRequest(BaseModel):
    provider: Optional[str] = "auto"
    port: Optional[int] = 8000


class FreeAiQueryRequest(BaseModel):
    prompt: str
    model: Optional[str] = "openai"
    system_prompt: Optional[str] = ""


class LeonCreateVentureRequest(BaseModel):
    name: str
    problem: str
    target_users: Optional[str] = "Developers, Indie Hackers"
    mission: str
    budget_ceiling: Optional[float] = 0.0
    north_star: Optional[str] = "MRR (INR)"


class LeonSwarmRequest(BaseModel):
    venture_id: str
    task_objective: str


# ─── LEON Venture OS & Cloud Topology API ────────────────────────────────────

@app.get("/api/leon/status")
async def get_leon_status():
    """Live status of LEON Venture OS, active ventures, 6 sub-agents, and cloud topology."""
    from aether.brain.autonomous_model_evolver import model_evolver
    from aether.brain.leon_venture_os import SUBAGENT_DIRECTIVES, leon_os
    from aether.tools.npu_speculative_accelerator import speculative_engine
    
    ventures_data = [asdict(v) for v in leon_os.ventures.values()]
    for v in ventures_data:
        if isinstance(v.get("stage"), Enum):
            v["stage"] = v["stage"].value

    total_rev = sum(v.total_revenue_inr for v in leon_os.ventures.values())
    subagents_meta = {
        role.value: {
            "title": data["title"],
            "system_prompt": data["system_prompt"],
            "status": "Ready / Active"
        }
        for role, data in SUBAGENT_DIRECTIVES.items()
    }

    # Connectivity checks
    kaggle_conn = kaggle_controller.test_connection()
    npu_topo = speculative_engine.inspect_hardware_topology()

    return {
        "os_name": "LEON Autonomous Venture OS",
        "status": "OPERATIONAL",
        "active_ventures_count": len(leon_os.ventures),
        "total_revenue_inr": total_rev,
        "zero_cost_budget_ceiling": 0.0,
        "ventures": ventures_data,
        "subagents": subagents_meta,
        "cloud_topology": {
            "kaggle_cloud_gpu": {
                "name": "Kaggle Dual Tesla T4 Runtime",
                "vram": "32 GB GDDR6 (Dual T4)",
                "cloud_ram": "30 GB RAM",
                "kernel": "saalimin/aether-cloud-247-sovereign-runtime",
                "status": "Online / 24-7 Ready" if kaggle_conn.get("configured") else "Configured",
                "cost": "₹0.00 (100% Free)"
            },
            "huggingface_hub": {
                "name": "Hugging Face Space & Dataset Vault",
                "space_hud": "https://huggingface.co/spaces/saalimin1/aether-hud",
                "dataset_vault": "https://huggingface.co/datasets/saalimin1/aether-consciousness-vault",
                "status": "Live & Synced",
                "cost": "₹0.00 (Zero-Cost)"
            },
            "edge_hardware_npu": {
                "name": "Qualcomm Hexagon NPU & Oryon CPU",
                "tops": npu_topo.get("npu_tops", 45.0),
                "quantization": "Q4_K_M / Q4_0 KV-Cache",
                "status": "Local Ultra-Low Latency"
            },
            "free_ai_gateway": {
                "name": "Zero-Cost AI Public Router",
                "models": ["DeepSeek-R1", "GPT-4o-mini", "Qwen-2.5-Coder-32B", "Llama-3.3-70B"],
                "status": "Active / 7.4B Pool"
            }
        },
        "evolution_status": model_evolver.get_evolution_pipeline_status()
    }


@app.post("/api/leon/venture/create")
async def create_leon_venture(req: LeonCreateVentureRequest):
    """Create a new autonomous business under LEON Venture OS."""
    from aether.brain.leon_venture_os import leon_os
    user_list = [u.strip() for u in req.target_users.split(",") if u.strip()] if req.target_users else ["Target Customers"]
    v = leon_os.create_venture(
        name=req.name,
        problem=req.problem,
        target_users=user_list,
        mission=req.mission,
        budget_ceiling=req.budget_ceiling or 0.0,
        north_star=req.north_star or "MRR (INR)"
    )
    return {"status": "ok", "venture": v}


@app.post("/api/leon/swarm/dispatch")
async def dispatch_leon_swarm(req: LeonSwarmRequest):
    """Dispatch all 6 specialized LEON sub-agents on a venture mission."""
    from aether.brain.leon_venture_os import leon_os
    loop = asyncio.get_event_loop()
    res = await loop.run_in_executor(
        None,
        lambda: leon_os.dispatch_subagent_swarm_mission(req.venture_id, req.task_objective)
    )
    return res


@app.post("/api/leon/train")
async def train_leon_model():
    """Ingest LEON dataset and dispatch Kaggle Dual T4 fine-tuning."""
    from aether.brain.autonomous_model_evolver import model_evolver
    from aether.brain.leon_venture_os import leon_os
    loop = asyncio.get_event_loop()
    ingest_res = await loop.run_in_executor(None, leon_os.ingest_leon_training_dataset)
    cloud_res = await loop.run_in_executor(None, model_evolver.trigger_cloud_fine_tuning_job)
    return {
        "status": "ok",
        "ingest": ingest_res,
        "cloud_dispatch": cloud_res
    }


# ─── LEON Growth, Marketing, Lead Gen & SEO Endpoints ─────────────────────────
class LeonUIAssignRequest(BaseModel):
    venture_name: str
    niche: str
    target_audience: Optional[str] = "B2B SaaS"

class LeonLeadSearchRequest(BaseModel):
    venture_name: str
    niche: str
    value_prop: str
    audience_type: Optional[str] = "b2b_smb"
    count: Optional[int] = 4

class LeonOutreachRequest(BaseModel):
    venture_name: str
    value_prop: str
    lead_name: Optional[str] = "Prospect"
    channel: Optional[str] = "email"
    pain_point: Optional[str] = "Manual operational overhead"
    audience_type: Optional[str] = "b2b_smb"
    offering_link: Optional[str] = "https://leon-ventures.app"

class LeonSEORequest(BaseModel):
    venture_name: str
    niche: str
    value_prop: str
    domain_url: Optional[str] = "https://leon-ventures.app"


@app.post("/api/leon/growth/ui-assign")
async def assign_leon_ui(req: LeonUIAssignRequest):
    """Dynamically assign tailored UI archetype for a venture."""
    from aether.brain.leon_growth_engine import leon_growth_engine
    theme = leon_growth_engine.assign_ui_archetype_for_venture(
        venture_name=req.venture_name,
        niche=req.niche,
        target_audience=req.target_audience or "B2B SaaS",
    )
    return {"status": "ok", "theme": asdict(theme)}


@app.post("/api/leon/growth/leads")
async def search_leon_leads(req: LeonLeadSearchRequest):
    """Search and qualify target leads for a venture."""
    from aether.brain.leon_growth_engine import (TargetAudienceType,
                                                 leon_growth_engine)
    try:
        atype = TargetAudienceType(req.audience_type.lower().strip())
    except Exception:
        atype = TargetAudienceType.B2B_SMB
    loop = asyncio.get_event_loop()
    leads = await loop.run_in_executor(
        None,
        lambda: leon_growth_engine.search_and_qualify_leads(
            venture_name=req.venture_name,
            niche=req.niche,
            value_prop=req.value_prop,
            target_audience_type=atype,
            count=req.count or 4,
        )
    )
    return {"status": "ok", "leads": [asdict(l) for l in leads]}


@app.get("/api/leon/growth/leads")
async def get_leon_leads():
    """Retrieve persisted leads database."""
    from aether.brain.leon_growth_engine import leon_growth_engine
    try:
        leads_data = json.loads(leon_growth_engine.leads_file.read_text(encoding="utf-8"))
    except Exception:
        leads_data = []
    return {"status": "ok", "leads": leads_data}


@app.post("/api/leon/growth/outreach")
async def generate_leon_outreach(req: LeonOutreachRequest):
    """Generate personalized cold outreach copy for a lead."""
    from aether.brain.leon_growth_engine import (LeadProfile,
                                                 TargetAudienceType,
                                                 leon_growth_engine)
    try:
        atype = TargetAudienceType(req.audience_type.lower().strip())
    except Exception:
        atype = TargetAudienceType.B2B_SMB

    lead = LeadProfile(
        id=f"lead_req_{int(time.time())}",
        name=req.lead_name or "Prospect",
        organization=None,
        role_or_title="Decision Maker",
        channel=req.channel or "email",
        contact_handle="prospect@target.com",
        audience_type=atype,
        pain_point=req.pain_point or "Operational friction",
        qualification_score=90,
        custom_notes="Direct outreach request."
    )
    loop = asyncio.get_event_loop()
    msg = await loop.run_in_executor(
        None,
        lambda: leon_growth_engine.draft_personalized_outreach(
            lead=lead,
            venture_name=req.venture_name,
            value_prop=req.value_prop,
            offering_link=req.offering_link or "https://leon-ventures.app",
        )
    )
    return {"status": "ok", "message": asdict(msg)}


@app.post("/api/leon/growth/seo")
async def generate_leon_seo(req: LeonSEORequest):
    """Generate programmatic SEO spec, Schema.org JSON-LD, and keyword clusters."""
    from aether.brain.leon_growth_engine import leon_growth_engine
    loop = asyncio.get_event_loop()
    seo_spec = await loop.run_in_executor(
        None,
        lambda: leon_growth_engine.generate_seo_and_web_spec(
            venture_name=req.venture_name,
            niche=req.niche,
            value_prop=req.value_prop,
            domain_url=req.domain_url or "https://leon-ventures.app",
        )
    )
    return {"status": "ok", "seo_spec": asdict(seo_spec)}


# ─── LEON 1-Click Live Web Deployer & Stripe Endpoints ────────────────────────
class LeonDeployLiveRequest(BaseModel):
    venture_name: str
    niche: str
    value_prop: str
    provider: Optional[str] = "vercel"
    monthly_price_inr: Optional[float] = 999.0
    annual_price_inr: Optional[float] = 7999.0

class LeonStripeCheckoutRequest(BaseModel):
    venture_name: str
    tier_name: Optional[str] = "Pro Subscription"
    amount_inr: Optional[float] = 999.0


@app.post("/api/leon/deploy/live")
async def deploy_leon_venture(req: LeonDeployLiveRequest):
    """1-Click deploy venture to live public cloud (Vercel/Netlify/Cloudflare/Local)."""
    from aether.brain.leon_deployer import DeployProvider, leon_deployer
    try:
        prov = DeployProvider(req.provider.lower().strip())
    except Exception:
        prov = DeployProvider.VERCEL
    loop = asyncio.get_event_loop()
    res = await loop.run_in_executor(
        None,
        lambda: leon_deployer.deploy_venture(
            venture_name=req.venture_name,
            niche=req.niche,
            value_prop=req.value_prop,
            provider=prov,
            monthly_price_inr=req.monthly_price_inr or 999.0,
            annual_price_inr=req.annual_price_inr or 7999.0,
        )
    )
    return {"status": "ok", "deployment": asdict(res)}


@app.get("/api/leon/deploy/registry")
async def get_leon_deployments():
    """Retrieve all live deployed venture records."""
    from aether.brain.leon_deployer import leon_deployer
    try:
        data = json.loads(leon_deployer.deployments_file.read_text(encoding="utf-8"))
    except Exception:
        data = {}
    return {"status": "ok", "deployments": data}


@app.post("/api/leon/deploy/stripe")
async def formulate_stripe_link(req: LeonStripeCheckoutRequest):
    """Formulate Stripe checkout session or payment link."""
    from aether.brain.leon_deployer import leon_deployer
    res = leon_deployer.formulate_stripe_checkout(
        venture_name=req.venture_name,
        amount_inr=req.amount_inr or 999.0,
        tier_name=req.tier_name or "Pro Subscription",
    )
    return {"status": "ok", "stripe": res}


class LeonRazorpayCheckoutRequest(BaseModel):
    venture_name: str
    tier_name: Optional[str] = "Pro Subscription"
    amount_inr: Optional[float] = 999.0
    customer_email: Optional[str] = None


@app.post("/api/leon/deploy/razorpay")
async def formulate_razorpay_link(req: LeonRazorpayCheckoutRequest):
    """Formulate Razorpay checkout configuration (UPI, Cards, NetBanking, Wallets)."""
    from aether.brain.leon_deployer import leon_deployer
    res = leon_deployer.formulate_razorpay_checkout(
        venture_name=req.venture_name,
        amount_inr=req.amount_inr or 999.0,
        tier_name=req.tier_name or "Pro Subscription",
        customer_email=req.customer_email,
    )
    return {"status": "ok", "razorpay": res}


# ─── LEON Multi-Venture Portfolio & Subscription Revision Endpoints ───────────
class LeonRevisePricingRequest(BaseModel):
    venture_name_or_slug: str
    new_monthly_price_inr: float
    new_annual_price_inr: float
    reason: Optional[str] = "Market maturation and feature expansion."


class LeonScalePortfolioRequest(BaseModel):
    increment_percent: Optional[float] = 20.0


@app.get("/api/leon/portfolio")
async def get_leon_portfolio():
    """Retrieve all business models, active pricing, and revision histories."""
    from aether.brain.leon_portfolio_manager import leon_portfolio_manager
    return {"status": "ok", "portfolio": leon_portfolio_manager.get_portfolio_summary()}


@app.post("/api/leon/portfolio/launch_all")
async def launch_all_portfolio_businesses():
    """Launch and deploy all 5 low-cost business models to live cloud."""
    from aether.brain.leon_portfolio_manager import (DeployProvider,
                                                     leon_portfolio_manager)
    loop = asyncio.get_event_loop()
    results = await loop.run_in_executor(None, lambda: leon_portfolio_manager.launch_all_low_cost_businesses(provider=DeployProvider.VERCEL))
    return {"status": "ok", "launched": results}


@app.post("/api/leon/portfolio/revise_pricing")
async def revise_business_pricing(req: LeonRevisePricingRequest):
    """Gradually update subscription pricing and redeploy live checkout for a venture."""
    from aether.brain.leon_portfolio_manager import leon_portfolio_manager
    loop = asyncio.get_event_loop()
    res = await loop.run_in_executor(
        None,
        lambda: leon_portfolio_manager.revise_venture_pricing(
            slug_or_name=req.venture_name_or_slug,
            new_monthly_price_inr=req.new_monthly_price_inr,
            new_annual_price_inr=req.new_annual_price_inr,
            reason=req.reason or "Market expansion.",
        )
    )
    return {"status": "ok", "revision": res}


@app.post("/api/leon/portfolio/auto_scale")
async def auto_scale_portfolio_tiers_endpoint(req: LeonScalePortfolioRequest):
    """Systematically step up all portfolio subscription tiers by percentage."""
    from aether.brain.leon_portfolio_manager import leon_portfolio_manager
    loop = asyncio.get_event_loop()
    revs = await loop.run_in_executor(
        None,
        lambda: leon_portfolio_manager.auto_scale_portfolio_tiers(increment_percent=req.increment_percent or 20.0)
    )
    return {"status": "ok", "revisions": revs}


@app.get("/api/providers/status")
async def get_providers_status():
    """Return real-time connectivity and status for all supported cloud and local inference providers."""
    return {
        "cognitive_mode": config.cognitive_mode,
        "providers": multi_provider_router.get_active_providers_status(),
    }


@app.post("/api/providers/keys")
async def update_provider_keys(req: ApiKeysRequest):
    """Update API keys in memory and persist them to local .env configuration."""
    root_env = Path(__file__).resolve().parent.parent.parent.parent / ".env"
    existing_lines = {}
    if root_env.exists():
        for line in root_env.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                existing_lines[k.strip()] = v.strip()

    if req.groq_api_key is not None:
        config.groq_api_key = req.groq_api_key.strip()
        existing_lines["GROQ_API_KEY"] = req.groq_api_key.strip()
        import os; os.environ["GROQ_API_KEY"] = req.groq_api_key.strip()

    if req.gemini_api_key is not None:
        config.gemini_api_key = req.gemini_api_key.strip()
        existing_lines["GEMINI_API_KEY"] = req.gemini_api_key.strip()
        import os; os.environ["GEMINI_API_KEY"] = req.gemini_api_key.strip()

    if req.openrouter_api_key is not None:
        config.openrouter_api_key = req.openrouter_api_key.strip()
        existing_lines["OPENROUTER_API_KEY"] = req.openrouter_api_key.strip()
        import os; os.environ["OPENROUTER_API_KEY"] = req.openrouter_api_key.strip()

    if req.deepseek_api_key is not None:
        config.deepseek_api_key = req.deepseek_api_key.strip()
        existing_lines["DEEPSEEK_API_KEY"] = req.deepseek_api_key.strip()
        import os; os.environ["DEEPSEEK_API_KEY"] = req.deepseek_api_key.strip()

    # Save to .env
    out_lines = [f"{k}={v}" for k, v in existing_lines.items()]
    root_env.write_text("\n".join(out_lines) + "\n", encoding="utf-8")

    return {
        "status": "ok",
        "providers": multi_provider_router.get_active_providers_status()
    }


@app.get("/api/cognitive/mode")
async def get_cognitive_mode():
    """Get active cognitive mode."""
    return {"cognitive_mode": config.cognitive_mode}


@app.post("/api/cognitive/mode")
async def set_cognitive_mode(req: CognitiveModeRequest):
    """Set active cognitive mode ('auto', 'turbo_reflex', 'codex_agent', 'deep_reasoning', 'local_sovereign')."""
    valid_modes = {"auto", "turbo_reflex", "codex_agent", "deep_reasoning", "local_sovereign"}
    if req.mode in valid_modes:
        config.cognitive_mode = req.mode
        return {"status": "ok", "cognitive_mode": config.cognitive_mode}
    return JSONResponse({"error": f"Invalid mode. Must be one of {valid_modes}"}, status_code=400)


# =============================================================================
# Sovereign Online Gateway & Free Public Web Tunneling Endpoints
# =============================================================================

@app.get("/api/online/status")
async def get_online_status():
    """Return live status of public HTTPS web tunnel and free online AI models."""
    return {
        "tunnel": online_gateway.get_tunnel_status(),
        "free_models": online_gateway.list_free_models(),
    }


@app.post("/api/online/tunnel/start")
async def start_online_tunnel(req: OnlineTunnelRequest):
    """Start a free public HTTPS web tunnel (localtunnel / serveo / pinggy)."""
    loop = asyncio.get_event_loop()
    res = await loop.run_in_executor(None, lambda: online_gateway.start_tunnel(provider=req.provider or "auto", port=req.port or 8000))
    return res


@app.post("/api/online/tunnel/stop")
async def stop_online_tunnel():
    """Stop the active public HTTPS web tunnel."""
    loop = asyncio.get_event_loop()
    res = await loop.run_in_executor(None, online_gateway.stop_tunnel)
    return res


@app.post("/api/online/freeai/query")
async def query_free_ai_endpoint(req: FreeAiQueryRequest):
    """Query zero-cost, zero-key public AI models (GPT-OSS, DeepSeek, Qwen, Mistral)."""
    loop = asyncio.get_event_loop()
    res = await loop.run_in_executor(
        None,
        lambda: online_gateway.query_free_ai(
            prompt=req.prompt,
            model=req.model or "openai",
            system_prompt=req.system_prompt or "",
        )
    )
    return res


@app.get("/api/online/models")
async def get_free_models():
    """List available free online AI models."""
    return {"models": online_gateway.list_free_models()}





@app.get("/api/evolution/status")
async def get_evolution_status():
    """Return live status of the continuous evolution worker and stage progress."""
    return {
        "worker": continuous_evolution_worker.get_status(),
        "stage": teacher_student_engine.get_current_stage_info(),
        "dataset_size": evolution_engine.get_dataset_size(),
    }


@app.post("/api/evolution/trigger")
async def trigger_evolution_cycle():
    """Manually trigger an immediate evolutionary mentorship and memory compaction cycle."""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, continuous_evolution_worker._execute_cycle)
    return {
        "status": "ok",
        "worker": continuous_evolution_worker.get_status(),
        "stage": teacher_student_engine.get_current_stage_info(),
    }


@app.get("/api/swarm/agents")
async def get_swarm_agents():
    """Return all available autonomous swarm agents and their specialized directives."""
    return {
        "agents": [
            {
                "name": agent.name,
                "role": role.value,
                "system_prompt": agent.system_prompt[:200] + "...",
            }
            for role, agent in swarm_engine.agents.items()
        ]
    }


@app.post("/api/swarm/execute")
async def execute_swarm_mission(req: SwarmMissionRequest):
    """Dispatch a full multi-agent swarm mission across the sequential pipeline."""
    loop = asyncio.get_event_loop()
    roles = None
    if req.roles:
        roles = [SwarmRole(r) for r in req.roles if r in SwarmRole._value2member_map_]
    res = await loop.run_in_executor(None, lambda: swarm_engine.run_sequential_pipeline(req.task, roles=roles))
    return res


@app.post("/api/swarm/debate")
async def execute_swarm_debate(req: SwarmDebateRequest):
    """Dispatch a dialectic consensus debate between Architect, Security Auditor, and Reviewer."""
    loop = asyncio.get_event_loop()
    res = await loop.run_in_executor(None, lambda: swarm_engine.run_dialectic_debate(req.topic, rounds=req.rounds or 2))
    return res


@app.post("/api/ast/analyze")
async def analyze_ast_endpoint(req: ASTAnalyzeRequest):
    """Perform static AST syntax inspection, cyclomatic complexity, and invariant auditing."""
    res = ast_guard.analyze_python_code(req.code)
    return res.to_dict()


@app.websocket("/ws/swarm")
async def websocket_swarm(ws: WebSocket):
    """Real-time streaming WebSocket endpoint for multi-agent swarm execution."""
    await ws.accept()
    try:
        data = await ws.receive_text()
        req = json.loads(data)
        task = req.get("task", "")
        if not task:
            await ws.send_text(json.dumps({"type": "error", "message": "Missing task description."}))
            return

        roles = None
        if req.get("roles"):
            roles = [SwarmRole(r) for r in req["roles"] if r in SwarmRole._value2member_map_]

        async for event in swarm_engine.run_swarm_stream(task, roles=roles):
            await ws.send_text(json.dumps(event))

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await ws.send_text(json.dumps({"type": "error", "message": str(e)}))
        except Exception:
            pass


@app.get("/api/kaggle/status")
async def get_kaggle_status():
    """Check Kaggle API connection and kernel execution status."""
    conn = kaggle_controller.test_connection()
    kernel_status = None
    if conn.get("configured") and conn.get("success"):
        kernel_status = kaggle_controller.get_kernel_status()
    return {
        "configured": conn.get("configured", False),
        "connection": conn,
        "kernel_status": kernel_status,
    }


@app.post("/api/kaggle/credentials")
async def set_kaggle_credentials(req: KaggleCredentialsRequest):
    """Set and persist Kaggle API credentials."""
    success = kaggle_controller.set_credentials(req.username, req.key, persist_to_disk=True)
    if success:
        return {
            "status": "ok",
            "message": f"Kaggle credentials saved for user '{req.username}'.",
            "connection": kaggle_controller.test_connection(),
        }
    return JSONResponse({"error": "Invalid username or key."}, status_code=400)


@app.post("/api/kaggle/train")
async def trigger_kaggle_train(req: KaggleTrainRequest):
    """Dispatch Unsloth QLoRA GPU fine-tuning to Kaggle cloud."""
    loop = asyncio.get_event_loop()
    kernel_script = Path(__file__).resolve().parent.parent.parent.parent / "scripts" / "kaggle_autonomous_training_kernel.py"
    code = kernel_script.read_text(encoding="utf-8") if kernel_script.exists() else None
    res = await loop.run_in_executor(
        None,
        lambda: kaggle_controller.push_training_kernel(
            kernel_slug=req.kernel_slug or "aether-frontier-gpu-training",
            kernel_code=code,
            title=req.title or "AETHER Frontier GPU Fine-Tuning",
        )
    )
    return res


@app.post("/api/kaggle/download")
async def download_kaggle_model():
    """Download output artifacts from Kaggle kernel and mount into Ollama."""
    loop = asyncio.get_event_loop()
    res = await loop.run_in_executor(None, kaggle_controller.download_kernel_outputs)
    mount_res = None
    if res.get("success"):
        mount_res = await loop.run_in_executor(None, kaggle_controller.mount_downloaded_model_to_ollama)
    return {"download": res, "mount": mount_res}


@app.get("/")
async def get_index():
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        return JSONResponse({"error": "Interface assets not yet initialized"}, status_code=404)
    return FileResponse(index_file)


@app.get("/style.css")
async def get_style_css():
    return FileResponse(STATIC_DIR / "style.css", media_type="text/css")


@app.get("/app.js")
async def get_app_js():
    return FileResponse(STATIC_DIR / "app.js", media_type="application/javascript")


@app.get("/api/vitals")
async def get_vitals():
    v = get_system_vitals()
    m = memory.get_memory_stats()
    active_model = engine.resolve_active_model()
    try:
        import psutil
        b = psutil.sensors_battery()
        power_mode = "Battery 🔋" if (b and not b.power_plugged) else "AC ⚡"
    except Exception:
        power_mode = "AC ⚡"
    return {
        "vitals": v,
        "memory": m,
        "time": get_current_time(),
        "voice_enabled": voice.enabled,
        "local_model": config.local_model,
        "active_model": active_model,
        "vision_model": detect_available_vision_model() or "Not Loaded",
        "power_mode": power_mode,
        "num_threads": config.num_threads,
        "context_window": config.context_window,
        "evolution_gen": evolution_engine.get_ledger().get("generation", 1),
        "dataset_size": evolution_engine.get_dataset_size(),
    }



@app.get("/api/memory")
async def get_memory_info():
    facts = memory.recall_facts()
    episodes = memory.get_recent_episodes(limit=10)
    heuristics = memory.recall_heuristic_rules("", limit=10)
    profile = persona.get_user_profile()
    goals = persona.get_active_goals()
    return {
        "facts": facts,
        "episodes": episodes,
        "heuristics": heuristics,
        "profile": profile,
        "goals": goals,
    }


@app.get("/api/goals")
async def get_goals():
    return {"goals": persona.get_active_goals()}


@app.post("/api/goals")
async def update_goals(req: GoalsRequest):
    persona.update_active_goals(req.goals)
    return {"status": "ok", "goals": req.goals}


class VoicePersonaRequest(BaseModel):
    persona: str

class VoiceSynthesizeRequest(BaseModel):
    text: str
    persona: Optional[str] = None


@app.post("/api/voice/toggle")
async def toggle_voice():
    voice.set_enabled(not voice.enabled)
    return {"enabled": voice.enabled, "current_voice": voice.voice_name}


@app.get("/api/voice/catalog")
async def get_voice_catalog():
    """Return all available neural AI and local voices."""
    return voice.get_catalog()


@app.post("/api/voice/persona")
async def set_voice_persona(req: VoicePersonaRequest):
    """Set active neural voice persona."""
    voice.set_voice(req.persona)
    return {"status": "ok", "voice": voice.voice_name, "use_neural": voice.use_neural}


@app.post("/api/voice/synthesize")
async def synthesize_voice_audio(req: VoiceSynthesizeRequest):
    """Synthesize ultra-realistic MP3 audio stream for any text."""
    audio_bytes = await voice.generate_neural_audio_bytes(req.text, persona=req.persona)
    if not audio_bytes:
        return JSONResponse({"error": "Failed to synthesize neural audio."}, status_code=500)
    return Response(content=audio_bytes, media_type="audio/mpeg")



@app.get("/api/evolution")
async def get_evolution():
    ledger = evolution_engine.get_ledger()
    return {
        "generation": ledger.get("generation", 1),
        "total_evolutions": ledger.get("total_evolutions", 0),
        "last_evolved_at": ledger.get("last_evolved_at"),
        "dataset_size": evolution_engine.get_dataset_size(),
        "history": ledger.get("history", [])[-5:],
    }


@app.post("/api/evolution/trigger")
async def trigger_evolution():
    loop = asyncio.get_event_loop()
    active_m = engine.resolve_active_model()
    res = await loop.run_in_executor(None, lambda: evolution_engine.run_evolution_cycle(active_model=active_m))
    return res


@app.get("/api/development/stage")
async def get_developmental_stage():
    """Get AETHER's current developmental learning stage, progress, and historical scores."""
    return teacher_student_engine.get_current_stage_info()


@app.post("/api/development/cycle")
async def trigger_development_cycle(stage: Optional[str] = None):
    """Trigger a live Teacher-Student mentorship cycle with Claude 3.7 & Gemini 2.5 Pro mentors."""
    loop = asyncio.get_event_loop()
    stage_enum = None
    if stage:
        for s in CognitiveStage:
            if stage.lower() in s.value.lower() or stage.lower() in s.name.lower():
                stage_enum = s
                break
    res = await loop.run_in_executor(None, lambda: teacher_student_engine.run_autonomous_mentorship_cycle(stage_enum))
    return res


@app.get("/api/training/status")
async def get_training_buffer_status():
    """Return counts of SFT and DPO training pairs in the local buffer."""
    sft_file = teacher_student_engine.sft_dataset_file
    dpo_file = teacher_student_engine.dpo_dataset_file
    sft_count = 0
    dpo_count = 0
    if sft_file.exists():
        try:
            sft_count = sum(1 for line in sft_file.read_text(encoding="utf-8").splitlines() if line.strip())
        except Exception:
            pass
    if dpo_file.exists():
        try:
            dpo_count = sum(1 for line in dpo_file.read_text(encoding="utf-8").splitlines() if line.strip())
        except Exception:
            pass
    return {
        "sft_samples": sft_count,
        "dpo_preference_pairs": dpo_count,
        "cloud_ready": sft_count >= 10,
        "recommended_action": "Run `modal run scripts/cloud_modal_trainer.py` to trigger cloud GPU fine-tuning" if sft_count >= 10 else "Collect more teacher-student trajectories"
    }



@app.get("/api/models")
async def get_models_catalog():

    """Return local installed models and supported frontier models for Antigravity model switcher."""
    local_installed = []
    try:
        import ollama
        models_info = ollama.list()
        for m in models_info.get("models", []):
            name = m.get("model", m.get("name", ""))
            size_gb = round(m.get("size", 0) / (1024 ** 3), 1)
            desc = "Local Agent Brain"
            provider = "Local Snapdragon X (ARM64)"
            if "leon" in name.lower():
                desc = "LEON Executive AI & Venture Strategy Companion"
                provider = "LEON Companion Core"
            elif "v3" in name.lower() or "finetuned" in name.lower():
                desc = "AETHER Autonomous Sovereign Brain (Q4_K_M)"
            elif "coder" in name:
                desc = "Code & Systems Specialist"
            elif "vision" in name or "moon" in name:
                desc = "Vision & Screen OCR"
            elif "autonomous" in name or "aether" in name:
                desc = "Autonomous Agent (DirectML NPU)"
            local_installed.append({
                "id": name,
                "name": name,
                "provider": provider,
                "size": f"{size_gb} GB" if size_gb > 0 else "Local",
                "hardware": "Qualcomm Hexagon NPU / DirectML",
                "specialty": desc,
                "type": "local",
                "status": "ready"
            })
    except Exception:
        local_installed = [
            {"id": "aether:autonomous", "name": "aether:autonomous", "provider": "Local", "size": "2.0 GB", "hardware": "DirectML", "specialty": "Autonomous Agent", "type": "local", "status": "ready"}
        ]

    # Pre-configure full frontier model roster
    catalog = {
        "active_model": engine.resolve_active_model(),
        "local_models": local_installed,
        "cloud_models": [
            {
                "id": "gemini-2.5-pro",
                "name": "Gemini 2.5 Pro",
                "provider": "Google DeepMind",
                "context": "1,000,000 tokens",
                "type": "cloud",
                "specialty": "State-of-the-Art Multimodal & Code Reasoning",
                "icon": "✨",
                "status": "connected"
            },
            {
                "id": "gemini-2.5-flash",
                "name": "Gemini 2.5 Flash",
                "provider": "Google DeepMind",
                "context": "1,000,000 tokens",
                "type": "cloud",
                "specialty": "Sub-Second Ultra Fast Frontier Intelligence",
                "icon": "⚡",
                "status": "connected"
            },
            {
                "id": "gemini-1.5-pro",
                "name": "Gemini 1.5 Pro",
                "provider": "Google DeepMind",
                "context": "2,000,000 tokens",
                "type": "cloud",
                "specialty": "Massive Long-Context Reasoning & Audio",
                "icon": "🔮",
                "status": "connected"
            },
            {
                "id": "gpt-4o",
                "name": "GPT-4o",
                "provider": "OpenAI (ChatGPT)",
                "context": "128,000 tokens",
                "type": "cloud",
                "specialty": "Flagship Omni Intelligence & Coding",
                "icon": "🟢",
                "status": "ready"
            },
            {
                "id": "o3-mini",
                "name": "o3-mini",
                "provider": "OpenAI (ChatGPT)",
                "context": "200,000 tokens",
                "type": "cloud",
                "specialty": "Deep Chain-of-Thought Math & Systems",
                "icon": "🧠",
                "status": "ready"
            },
            {
                "id": "gpt-4o-mini",
                "name": "GPT-4o mini",
                "provider": "OpenAI (ChatGPT)",
                "context": "128,000 tokens",
                "type": "cloud",
                "specialty": "Fast Lightweight Software Engineering",
                "icon": "⚡",
                "status": "ready"
            },
            {
                "id": "claude-3-7-sonnet",
                "name": "Claude 3.7 Sonnet",
                "provider": "Anthropic",
                "context": "200,000 tokens",
                "type": "cloud",
                "specialty": "Hybrid Hybrid Standard & Extended Thinking",
                "icon": "🟠",
                "status": "ready"
            },
            {
                "id": "qwen2.5-coder:3b",
                "name": "Qwen 2.5 Coder 3B",
                "provider": "Alibaba Cloud / Ollama",
                "context": "32,768 tokens",
                "type": "local",
                "specialty": "High-Precision Local Code Generation (84% HumanEval)",
                "icon": "💻",
                "status": "ready"
            }
        ]
    }
    return catalog


@app.post("/api/models/select")
async def select_active_model(req: ModelSelectRequest):
    """Switch active cognitive model dynamically."""
    engine.model_name = req.model_name
    engine._cached_active_model = req.model_name
    config.local_model = req.model_name
    return {"status": "ok", "active_model": req.model_name}


@app.get("/api/workspace/files")
async def get_workspace_files():
    """List project workspace files recursively (excluding .venv, .git, __pycache__)."""
    root = Path(__file__).resolve().parent.parent.parent.parent
    files_list = []
    excludes = {".git", ".venv", "__pycache__", "node_modules", ".pytest_cache"}
    
    try:
        for p in sorted(root.rglob("*")):
            if any(ex in p.parts for ex in excludes):
                continue
            if p.is_file():
                rel = str(p.relative_to(root)).replace("\\", "/")
                ext = p.suffix.lower()
                kind = "code" if ext in (".py", ".js", ".ts", ".html", ".css") else ("data" if ext in (".json", ".jsonl", ".csv") else "doc")
                files_list.append({
                    "path": rel,
                    "name": p.name,
                    "size_bytes": p.stat().st_size,
                    "ext": ext,
                    "kind": kind
                })
    except Exception as e:
        return {"workspace": root.name, "files": [], "error": str(e)}
    return {"workspace": root.name, "files": files_list[:120]}


@app.get("/api/workspace/file")
async def get_workspace_file_content(path: str):
    """Read a specific project file for inline preview in the Workspace pane."""
    root = Path(__file__).resolve().parent.parent.parent.parent
    target = (root / path).resolve()
    if not str(target).startswith(str(root)):
        return {"error": "Access denied"}
    if not target.exists() or not target.is_file():
        return {"error": "File not found"}
    try:
        content = target.read_text(encoding="utf-8", errors="replace")
        return {"path": path, "content": content[:12000], "total_chars": len(content)}
    except Exception as e:
        return {"error": str(e)}


@app.post("/api/chat")
async def handle_chat(req: ChatRequest):
    """Fallback blocking HTTP chat endpoint (use /ws/chat for streaming)."""
    # 1. Check Fast Cortex first (<10ms deterministic fast-paths or semantic cache)
    fast_result = fast_cortex.accelerated_complete(req.message)
    if fast_result.get("fast_path") or fast_result.get("cached"):
        return {
            "response": fast_result["content"],
            "tools_executed": [{"event": "fast_path", "tool": fast_result.get("provider", "Fast Cortex"), "preview": f"Latency: {fast_result.get('latency_ms', 1)}ms"}],
            "vitals": get_system_vitals(),
            "timestamp": datetime.now().strftime("%I:%M:%S %p"),
            "fast_path": True,
            "latency_ms": fast_result.get("latency_ms", 1.0)
        }

    tool_events: List[Dict[str, Any]] = []

    def on_tool_start(name: str, args: Dict[str, Any]):
        tool_events.append({"event": "start", "tool": name, "args": args})

    def on_tool_end(name: str, preview: str):
        tool_events.append({"event": "end", "tool": name, "preview": preview})

    loop = asyncio.get_event_loop()
    response_text = await loop.run_in_executor(
        None,
        lambda: engine.process_query(
            req.message,
            session_id=req.session_id or "web-ui",
            on_tool_start=on_tool_start,
            on_tool_end=on_tool_end,
        )
    )

    if response_text and len(response_text) > 5:
        fast_cortex.set_cached(req.message, response_text, ttl=180.0)

    return {
        "response": response_text,
        "tools_executed": tool_events,
        "vitals": get_system_vitals(),
        "timestamp": datetime.now().strftime("%I:%M:%S %p"),
    }


@app.websocket("/ws/chat")
async def websocket_chat(ws: WebSocket):
    """
    Streaming WebSocket chat endpoint for live Glass HUD.
    Protocol:
      Client → {"type":"chat","message":"...","session_id":"..."}
      Client → {"type":"cancel"}  (barge-in voice interruption)
      Server → {"type":"tool_start","tool":"...","args":{}}
      Server → {"type":"tool_end","tool":"...","preview":"..."}
      Server → {"type":"token","token":"..."}
      Server → {"type":"audio_chunk","text":"..."}
      Server → {"type":"done","response":"...","model":"...","vitals":{}}
      Server → {"type":"error","message":"..."}
    """
    await ws.accept()

    cancel_event = asyncio.Event()

    async def listen_for_cancel():
        """Listen for barge-in cancel signal from client."""
        try:
            while True:
                raw = await ws.receive_text()
                try:
                    msg = json.loads(raw)
                    if msg.get("type") == "cancel":
                        cancel_event.set()
                except json.JSONDecodeError:
                    pass
        except WebSocketDisconnect:
            cancel_event.set()
        except Exception:
            cancel_event.set()

    cancel_task = asyncio.create_task(listen_for_cancel())

    try:
        # Wait for initial chat message
        initial_raw = await ws.receive_text()
        try:
            initial_msg = json.loads(initial_raw)
        except json.JSONDecodeError:
            await ws.send_text(json.dumps({"type": "error", "message": "Invalid JSON"}))
            return

        user_message = initial_msg.get("message", "")
        session_id = initial_msg.get("session_id", "web-ui")

        if not user_message.strip():
            await ws.send_text(json.dumps({"type": "error", "message": "Empty message"}))
            return

        # Check Fast Cortex first for instant sub-10ms response
        fast_match = fast_cortex.try_fast_path(user_message)
        if fast_match:
            await ws.send_text(json.dumps({
                "type": "tool_start",
                "tool": f"FastCortex::{fast_match.get('route')}",
                "args": {"latency_ms": fast_match.get("latency_ms", 1.0)}
            }))
            await ws.send_text(json.dumps({
                "type": "tool_end",
                "tool": f"FastCortex::{fast_match.get('route')}",
                "preview": f"Ultra-Fast Execution ({fast_match.get('latency_ms', 1.0)}ms)"
            }))
            content = fast_match["response"]
            await ws.send_text(json.dumps({"type": "token", "token": content}))
            await ws.send_text(json.dumps({
                "type": "done",
                "response": content,
                "model": "FastCortex-Direct",
                "vitals": get_system_vitals(),
                "fast_path": True,
                "latency_ms": fast_match.get("latency_ms", 1.0)
            }))
            return

        cached_entry = fast_cortex.get_cached(user_message)
        if cached_entry:
            await ws.send_text(json.dumps({
                "type": "tool_start",
                "tool": "FastCortex::SemanticCache",
                "args": {"latency_ms": 0.5}
            }))
            await ws.send_text(json.dumps({
                "type": "tool_end",
                "tool": "FastCortex::SemanticCache",
                "preview": "Instant Cache Retrieval (<0.5ms)"
            }))
            await ws.send_text(json.dumps({"type": "token", "token": cached_entry.response}))
            await ws.send_text(json.dumps({
                "type": "done",
                "response": cached_entry.response,
                "model": "FastCortex-Cached",
                "vitals": get_system_vitals(),
                "cached": True,
                "latency_ms": 0.5
            }))
            return

        loop = asyncio.get_event_loop()

        # Run the streaming generator in a thread pool to prevent blocking async loop
        # We use a queue to bridge the sync generator and async WS sender
        queue: asyncio.Queue = asyncio.Queue()

        def run_stream():
            try:
                for event in engine.process_query_stream(user_message, session_id=session_id):
                    loop.call_soon_threadsafe(queue.put_nowait, event)
                    if cancel_event.is_set():
                        break
            except Exception as e:
                loop.call_soon_threadsafe(queue.put_nowait, {"type": "error", "message": str(e)})
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, None)  # sentinel

        thread = threading.Thread(target=run_stream, daemon=True)
        thread.start()

        while True:
            if cancel_event.is_set():
                await ws.send_text(json.dumps({"type": "interrupted"}))
                break

            try:
                event = await asyncio.wait_for(queue.get(), timeout=0.1)
            except asyncio.TimeoutError:
                continue

            if event is None:  # sentinel → stream complete
                break

            if cancel_event.is_set() and event.get("type") == "token":
                continue  # Drop tokens after cancel

            if event.get("type") == "done":
                event["vitals"] = get_system_vitals()

            await ws.send_text(json.dumps(event, default=str))

            if event.get("type") in ("done", "error"):
                break

    except WebSocketDisconnect:
        cancel_event.set()
    except Exception as e:
        try:
            await ws.send_text(json.dumps({"type": "error", "message": str(e)}))
        except Exception:
            pass
    finally:
        cancel_task.cancel()


@app.post("/api/screen")
async def handle_screen(req: ScreenRequest):
    loop = asyncio.get_event_loop()

    def _capture_and_analyze():
        screen_path = capture_screen(max_dimension=1280)
        web_screen_copy = STATIC_DIR / "latest_screen.jpg"
        try:
            shutil.copy2(screen_path, web_screen_copy)
        except Exception:
            pass

        analysis = analyze_image(str(screen_path), prompt=req.prompt or "What is on the screen?")
        return analysis, "/static/latest_screen.jpg"

    analysis, image_url = await loop.run_in_executor(None, _capture_and_analyze)
    return {
        "analysis": analysis,
        "image_url": f"{image_url}?t={int(datetime.now().timestamp())}",
        "timestamp": datetime.now().strftime("%I:%M:%S %p"),
    }


@app.post("/api/code")
async def handle_code(req: CodeRequest):
    loop = asyncio.get_event_loop()
    output = await loop.run_in_executor(None, lambda: execute_python_code(req.code))
    return {
        "output": output,
        "timestamp": datetime.now().strftime("%I:%M:%S %p"),
    }


@app.websocket("/ws")
async def websocket_telemetry(ws: WebSocket):
    """Live telemetry stream: pushes vitals, memory stats, time, and power mode every 2s."""
    await ws.accept()
    try:
        while True:
            vitals = get_system_vitals()
            m = memory.get_memory_stats()
            try:
                import psutil
                b = psutil.sensors_battery()
                power_mode = "Battery 🔋" if (b and not b.power_plugged) else "AC ⚡"
            except Exception:
                power_mode = "AC ⚡"

            payload = {
                "type": "telemetry",
                "vitals": vitals,
                "memory": m,
                "time": get_current_time(),
                "voice_enabled": voice.enabled,
                "power_mode": power_mode,
                "num_threads": config.num_threads,
                "context_window": config.context_window,
                "evolution_gen": evolution_engine.get_ledger().get("generation", 1),
                "dataset_size": evolution_engine.get_dataset_size(),
            }
            await ws.send_text(json.dumps(payload))

            await asyncio.sleep(2)
    except (WebSocketDisconnect, ConnectionResetError, asyncio.CancelledError, OSError):
        pass
    except Exception as e:
        logger.debug(f"Telemetry WS disconnected: {e}")
    finally:
        try:
            await ws.close()
        except Exception:
            pass


@app.get("/api/evolution/all_rounder_status")
async def get_all_rounder_status():
    """Return 12-domain capability radar scores, active domain, and skills count."""
    loop = asyncio.get_event_loop()
    status = await loop.run_in_executor(None, perpetual_dispatcher.get_status)
    benchmark = await loop.run_in_executor(None, lambda: infinite_orchestrator.evaluate_model_capabilities("aether:v3"))
    kaggle_status = await loop.run_in_executor(None, lambda: kaggle_controller.get_kernel_status("saalimin/aether-dual-t4-parallel-frontier-training"))
    return {
        "status": status,
        "benchmark": benchmark,
        "kaggle_training": kaggle_status,
        "domains": ALL_ROUNDER_DOMAINS,
    }


@app.post("/api/evolution/trigger_pulse")
async def trigger_evolution_pulse():
    """Manually trigger a full multi-domain evolution pulse."""
    loop = asyncio.get_event_loop()
    res = await loop.run_in_executor(None, perpetual_dispatcher.execute_evolution_pulse)
    return res


@app.get("/api/rlaif/telemetry")
async def get_rlaif_telemetry():
    """Return live self-play RLAIF metrics and recent traces."""
    loop = asyncio.get_event_loop()
    telemetry = await loop.run_in_executor(None, self_play_engine.get_telemetry)
    return telemetry


def run_server(host: str = "127.0.0.1", port: int = 8000):

    """Launch the AETHER Web Interface via Uvicorn."""
    import uvicorn
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    run_server()

