"""Production-grade FastAPI HTTP REST + SSE server for the Obscura Enchanted Agent Engine.

Endpoints
---------
POST   /navigate              Navigate to URL → DistilledSnapshot
POST   /act                   Execute atomic browser action → result JSON
GET    /snapshot              Current distilled page snapshot
GET    /diff                  Semantic DOM diff since last call
POST   /fill_form             Batch form population → result JSON
POST   /extract               Structured data extraction from DOM
GET    /metrics               Live session pool metrics
GET    /health                Health check with version info
POST   /sessions              Create a new named session (tab)
DELETE /sessions/{session_id} Destroy a session
GET    /sse/events            SSE stream of real-time browser events
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict, List, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from .client import AsyncObscuraAgentEngine
from .middleware import ApiKeyMiddleware, RateLimitMiddleware, TimingMiddleware
from .types import (
    ActionType,
    BrowserAction,
    DistilledSnapshot,
    DomDiff,
    EngineMetrics,
    FormFieldEntry,
    TabSession,
)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=os.getenv("OBSCURA_LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("obscura_engine.api_server")

# ---------------------------------------------------------------------------
# Version
# ---------------------------------------------------------------------------
_API_VERSION = "1.0.0"
_ENGINE_VERSION = "1.0.0"


# ---------------------------------------------------------------------------
# Shared engine state
# ---------------------------------------------------------------------------

class _EngineState:
    """Holds the global engine and a per-session engine map, protected by an async lock."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        # Default engine (session_id = "default")
        self._engines: Dict[str, AsyncObscuraAgentEngine] = {}
        self._start_time: float = time.time()

        # SSE event bus: list of asyncio.Queue per subscriber
        self._sse_queues: List[asyncio.Queue] = []

    async def get_or_create_engine(
        self,
        session_id: str = "default",
        agent_id: Optional[str] = None,
    ) -> AsyncObscuraAgentEngine:
        async with self._lock:
            if session_id not in self._engines:
                engine = AsyncObscuraAgentEngine(max_tabs=8)
                await engine.initialize(agent_id=agent_id or session_id)
                self._engines[session_id] = engine
                logger.info("Created engine for session '%s'", session_id)
            return self._engines[session_id]

    async def destroy_engine(self, session_id: str) -> bool:
        async with self._lock:
            engine = self._engines.pop(session_id, None)
            if engine:
                await engine.close()
                logger.info("Destroyed engine for session '%s'", session_id)
                return True
            return False

    def list_sessions(self) -> List[str]:
        return list(self._engines.keys())

    async def publish_event(self, event: Dict[str, Any]) -> None:
        """Broadcast a browser event to all SSE subscribers."""
        for q in list(self._sse_queues):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                pass

    def subscribe_events(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=256)
        self._sse_queues.append(q)
        return q

    def unsubscribe_events(self, q: asyncio.Queue) -> None:
        try:
            self._sse_queues.remove(q)
        except ValueError:
            pass

    async def close_all(self) -> None:
        async with self._lock:
            for engine in self._engines.values():
                await engine.close()
            self._engines.clear()


_state = _EngineState()


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup: create a default engine. Shutdown: clean up all engines."""
    logger.info("Obscura API server starting up (v%s)", _API_VERSION)
    await _state.get_or_create_engine(session_id="default", agent_id="default-agent")
    yield
    logger.info("Obscura API server shutting down — cleaning up engines.")
    await _state.close_all()


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

def create_app() -> FastAPI:
    app = FastAPI(
        title="Obscura Enchanted Agent Engine — HTTP API",
        description=(
            "Production-grade REST + SSE API for the Obscura headless browser engine. "
            "Provides navigation, action dispatch, DOM distillation, diffs, form filling, "
            "structured extraction, and real-time SSE events."
        ),
        version=_API_VERSION,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # ---- CORS ----------------------------------------------------------------
    app.add_middleware(
        CORSMiddleware,
        allow_origins=os.getenv("OBSCURA_CORS_ORIGINS", "*").split(","),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ---- Custom middleware (applied inner → outer) ---------------------------
    app.add_middleware(TimingMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(ApiKeyMiddleware)

    # ---- Request / response logging ------------------------------------------
    @app.middleware("http")
    async def _request_logger(request: Request, call_next):
        req_id = request.headers.get("X-Request-Id", uuid.uuid4().hex[:8])
        logger.info(
            "[%s] ▶ %s %s  client=%s",
            req_id,
            request.method,
            request.url.path,
            request.client.host if request.client else "?",
        )
        response = await call_next(request)
        logger.info("[%s] ◀ %s", req_id, response.status_code)
        response.headers["X-Request-Id"] = req_id
        return response

    # ---- Register routers ----------------------------------------------------
    app.include_router(_router)

    return app


# ---------------------------------------------------------------------------
# Pydantic request / response models
# ---------------------------------------------------------------------------

class NavigateRequest(BaseModel):
    url: str = Field(..., description="Fully-qualified URL to navigate to.")
    session_id: str = Field("default", description="Target session / tab identifier.")

class ActRequest(BaseModel):
    action: ActionType
    ref: Optional[str] = Field(None, description="Ref ID from the latest DistilledSnapshot.")
    selector: Optional[str] = Field(None, description="Fallback CSS selector.")
    value: Optional[str] = Field(None, description="Text value for type/select actions.")
    key: Optional[str] = Field(None, description="Key name for press_key (e.g. 'Enter').")
    scroll_delta_y: Optional[int] = Field(None, description="Vertical scroll distance (px).")
    session_id: str = Field("default")

class FillFormRequest(BaseModel):
    fields: List[FormFieldEntry]
    session_id: str = Field("default")

class ExtractRequest(BaseModel):
    container_selector: str = Field(..., description="CSS selector for the repeating container element.")
    fields: Dict[str, str] = Field(..., description="Mapping of field_name → sub-selector within each container.")
    session_id: str = Field("default")

class CreateSessionRequest(BaseModel):
    session_id: Optional[str] = Field(None, description="Desired session ID; auto-generated if omitted.")
    agent_id: Optional[str] = Field(None, description="Agent identifier to associate with the session.")

class SnapshotQueryParams(BaseModel):
    session_id: str = "default"

# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

from fastapi import APIRouter

_router = APIRouter()


# --- helpers ---

async def _resolve_engine(session_id: str) -> AsyncObscuraAgentEngine:
    return await _state.get_or_create_engine(session_id=session_id)


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------

@_router.get("/health", tags=["System"])
async def health_check() -> Dict[str, Any]:
    """Health check with version and uptime information."""
    return {
        "status": "ok",
        "api_version": _API_VERSION,
        "engine_version": _ENGINE_VERSION,
        "active_sessions": len(_state.list_sessions()),
        "uptime_seconds": round(time.time() - _state._start_time, 2),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


# ---------------------------------------------------------------------------
# GET /metrics
# ---------------------------------------------------------------------------

@_router.get("/metrics", response_model=EngineMetrics, tags=["System"])
async def get_metrics(session_id: str = Query("default")) -> EngineMetrics:
    """Live session pool metrics: memory, tokens saved, action counts, uptime."""
    engine = await _resolve_engine(session_id)
    return engine.session_pool.get_metrics()


# ---------------------------------------------------------------------------
# GET /sessions
# ---------------------------------------------------------------------------

@_router.get("/sessions", tags=["Sessions"])
async def list_sessions() -> Dict[str, Any]:
    """List all active browser session IDs."""
    sessions = _state.list_sessions()
    return {"sessions": sessions, "count": len(sessions)}


# ---------------------------------------------------------------------------
# POST /sessions
# ---------------------------------------------------------------------------

@_router.post("/sessions", status_code=status.HTTP_201_CREATED, tags=["Sessions"])
async def create_session(body: CreateSessionRequest) -> Dict[str, Any]:
    """Create a new named browser session (tab)."""
    session_id = body.session_id or f"session_{uuid.uuid4().hex[:8]}"
    engine = await _state.get_or_create_engine(
        session_id=session_id,
        agent_id=body.agent_id or session_id,
    )
    tab = engine._active_tab
    return {
        "session_id": session_id,
        "tab_id": tab.tab_id if tab else None,
        "agent_id": tab.agent_id if tab else session_id,
        "created": True,
    }


# ---------------------------------------------------------------------------
# DELETE /sessions/{session_id}
# ---------------------------------------------------------------------------

@_router.delete("/sessions/{session_id}", tags=["Sessions"])
async def destroy_session(session_id: str) -> Dict[str, Any]:
    """Destroy a browser session and free its resources."""
    if session_id == "default":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot destroy the default session via API.",
        )
    destroyed = await _state.destroy_engine(session_id)
    if not destroyed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found.",
        )
    return {"session_id": session_id, "destroyed": True}


# ---------------------------------------------------------------------------
# POST /navigate
# ---------------------------------------------------------------------------

@_router.post("/navigate", response_model=DistilledSnapshot, tags=["Browser"])
async def navigate(body: NavigateRequest) -> DistilledSnapshot:
    """Navigate to a URL and return the token-compressed semantic snapshot."""
    engine = await _resolve_engine(body.session_id)
    snapshot = await engine.navigate(body.url)

    await _state.publish_event({
        "type": "page_load",
        "session_id": body.session_id,
        "url": snapshot.url,
        "title": snapshot.title,
        "timestamp": time.time(),
    })
    return snapshot


# ---------------------------------------------------------------------------
# POST /act
# ---------------------------------------------------------------------------

@_router.post("/act", tags=["Browser"])
async def act(body: ActRequest) -> Dict[str, Any]:
    """Dispatch an atomic browser action (click, type, select, scroll, press_key)."""
    engine = await _resolve_engine(body.session_id)
    browser_action = BrowserAction(
        action=body.action,
        ref=body.ref,
        selector=body.selector,
        value=body.value,
        key=body.key,
        scroll_delta_y=body.scroll_delta_y,
    )
    result = await engine.act(browser_action)

    await _state.publish_event({
        "type": "action",
        "session_id": body.session_id,
        "action": body.action.value,
        "ref": body.ref,
        "selector": body.selector,
        "timestamp": time.time(),
    })
    return result


# ---------------------------------------------------------------------------
# GET /snapshot
# ---------------------------------------------------------------------------

@_router.get("/snapshot", response_model=DistilledSnapshot, tags=["Browser"])
async def get_snapshot(session_id: str = Query("default")) -> DistilledSnapshot:
    """Return the current token-compressed semantic snapshot without navigation."""
    engine = await _resolve_engine(session_id)
    return engine.snapshot()


# ---------------------------------------------------------------------------
# GET /diff
# ---------------------------------------------------------------------------

@_router.get("/diff", response_model=DomDiff, tags=["Browser"])
async def get_diff(session_id: str = Query("default")) -> DomDiff:
    """Return the semantic DOM mutation diff since the last call."""
    engine = await _resolve_engine(session_id)
    diff = engine.diff_snapshot()

    if diff.has_changed:
        await _state.publish_event({
            "type": "dom_change",
            "session_id": session_id,
            "summary": diff.summary,
            "timestamp": time.time(),
        })
    return diff


# ---------------------------------------------------------------------------
# POST /fill_form
# ---------------------------------------------------------------------------

@_router.post("/fill_form", tags=["Browser"])
async def fill_form(body: FillFormRequest) -> Dict[str, Any]:
    """Batch-populate multiple form fields in a single atomic call."""
    engine = await _resolve_engine(body.session_id)
    result = await engine.fill_form(body.fields)
    return result


# ---------------------------------------------------------------------------
# POST /extract
# ---------------------------------------------------------------------------

@_router.post("/extract", tags=["Browser"])
async def extract(body: ExtractRequest) -> Dict[str, Any]:
    """Extract structured JSON from repeating DOM containers matching the given CSS selector."""
    engine = await _resolve_engine(body.session_id)
    rows = engine.extract_structured_data(body.container_selector, body.fields)
    return {
        "session_id": body.session_id,
        "container_selector": body.container_selector,
        "count": len(rows),
        "data": rows,
    }


# ---------------------------------------------------------------------------
# GET /sse/events
# ---------------------------------------------------------------------------

@_router.get("/sse/events", tags=["SSE"])
async def sse_events(request: Request) -> StreamingResponse:
    """Server-Sent Events stream of real-time browser events (page loads, DOM changes, actions)."""

    async def _event_generator() -> AsyncGenerator[str, None]:
        q = _state.subscribe_events()
        # Send a connected heartbeat immediately
        yield _sse_format({"type": "connected", "timestamp": time.time()})
        try:
            while True:
                # Check if client disconnected
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(q.get(), timeout=15.0)
                    yield _sse_format(event)
                except asyncio.TimeoutError:
                    # Send a keepalive comment every 15 s
                    yield ": keepalive\n\n"
        finally:
            _state.unsubscribe_events(q)

    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


def _sse_format(data: Dict[str, Any]) -> str:
    """Format a dict as an SSE data frame."""
    event_type = data.get("type", "event")
    payload = json.dumps(data)
    return f"event: {event_type}\ndata: {payload}\n\n"


# ---------------------------------------------------------------------------
# App instance (module-level, importable)
# ---------------------------------------------------------------------------

app = create_app()


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "obscura_engine.api_server:app",
        host=os.getenv("OBSCURA_HOST", "0.0.0.0"),
        port=int(os.getenv("OBSCURA_PORT", "8787")),
        reload=os.getenv("OBSCURA_RELOAD", "false").lower() == "true",
        log_level=os.getenv("OBSCURA_LOG_LEVEL", "info").lower(),
    )
