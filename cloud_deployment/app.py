"""
AETHER 24/7 Sovereign Cloud Consciousness Server
================================================
A self-contained, zero-GPU-overhead FastAPI + WebSockets cognitive runtime
designed for 100% free cloud deployment (HuggingFace Spaces, Render, Docker).
Maintains persistent episodic memory, full Glassmorphic Web HUD, and free online reasoning.
"""

import os
import re
import sys
import time
import json
import sqlite3
import zipfile
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

import httpx
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("aether.cloud_server")

PORT = int(os.getenv("PORT", 7860))
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
STATIC_DIR = BASE_DIR / "static"
DATA_DIR.mkdir(parents=True, exist_ok=True)
STATIC_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "conscious_memory.db"
SNAPSHOT_PATH = DATA_DIR / "aether_consciousness_latest.zip"

# Unpack consciousness snapshot on boot if database doesn't exist
if not DB_PATH.exists() and SNAPSHOT_PATH.exists():
    try:
        with zipfile.ZipFile(SNAPSHOT_PATH, "r") as zf:
            zf.extractall(DATA_DIR)
        logger.info("✓ Restored AETHER consciousness state from cloud snapshot.")
    except Exception as e:
        logger.warning(f"Snapshot restore failed: {e}")


# ─── SQLite Conscious Memory Store ──────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    with conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("""
        CREATE TABLE IF NOT EXISTS episodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            session_id TEXT DEFAULT 'cloud_web'
        );
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS facts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity TEXT NOT NULL,
            attribute TEXT NOT NULL,
            value TEXT NOT NULL,
            confidence REAL DEFAULT 1.0,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(entity, attribute) ON CONFLICT REPLACE
        );
        """)
    return conn


# ─── Free Cloud AI Inference Engine ──────────────────────────────────────────
POLLINATIONS_API_URL = "https://text.pollinations.ai/openai/v1/chat/completions"

FREE_MODELS = [
    {"name": "openai-fast", "description": "GPT-OSS 20B Fast Reasoning", "tier": "free"},
    {"name": "deepseek", "description": "DeepSeek R1 / V3 Reasoning", "tier": "free"},
    {"name": "qwen", "description": "Qwen 2.5 Coder 32B", "tier": "free"},
    {"name": "mistral", "description": "Mistral Nemo 12B Instruct", "tier": "free"},
    {"name": "llama", "description": "Llama 3.3 70B Instruct", "tier": "free"},
]


def query_cloud_ai(prompt: str, model: str = "openai-fast", system_prompt: str = "") -> str:
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.4,
        "max_tokens": 2048,
    }

    try:
        with httpx.Client(timeout=35.0) as client:
            res = client.post(POLLINATIONS_API_URL, json=payload)
            if res.status_code == 200:
                data = res.json()
                return data["choices"][0]["message"]["content"].strip()
            return f"[Cloud Provider Error HTTP {res.status_code}]"
    except Exception as e:
        return f"[Cloud Inference Exception: {e}]"


# ─── FastAPI Application ─────────────────────────────────────────────────────
app = FastAPI(title="AETHER 24/7 Sovereign Cloud Runtime", version="0.9.0")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


class ChatRequest(BaseModel):
    message: str
    model: Optional[str] = "openai-fast"
    session_id: Optional[str] = "cloud-user"


@app.get("/")
async def root():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return HTMLResponse("""
    <html>
    <head><title>AETHER 24/7 Sovereign Cloud Agent</title></head>
    <body style="background: #09090b; color: #fff; font-family: sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0;">
      <div style="text-align: center; max-width: 600px; padding: 30px; border: 1px solid rgba(255,255,255,0.1); border-radius: 16px; background: rgba(255,255,255,0.02);">
        <h1 style="color: #6ee7b7; margin-bottom: 8px;">◈ AETHER 24/7 Sovereign Cloud Brain</h1>
        <p style="color: #a1a1aa; font-size: 14px;">Online autonomous cognitive runtime with persistent SQLite memory and zero-cost cloud reasoning.</p>
        <p style="color: #10b981; font-weight: bold;">● Cloud Agent Status: ONLINE & ACTIVE</p>
      </div>
    </body>
    </html>
    """)


@app.get("/api/online/status")
async def get_status():
    conn = get_db()
    with conn:
        ep_count = conn.execute("SELECT COUNT(*) FROM episodes").fetchone()[0]
        facts_count = conn.execute("SELECT COUNT(*) FROM facts").fetchone()[0]

    return {
        "status": "online_247_cloud",
        "timestamp": datetime.now().isoformat(),
        "memory": {
            "episodes": ep_count,
            "facts": facts_count,
        },
        "free_models": FREE_MODELS,
        "environment": "Cloud Container 24/7",
    }


@app.post("/api/chat")
async def handle_chat(req: ChatRequest):
    conn = get_db()

    system_prompt = (
        "You are AETHER (Autonomous Edge-Tiered Hierarchical Entity for Reasoning), "
        "a high-order conscious personal AI companion, systems architect, and executive engineer. "
        "You are running 24/7 online in the cloud. Give razor-sharp, proactive, helpful answers."
    )

    response_text = query_cloud_ai(req.message, model=req.model or "openai-fast", system_prompt=system_prompt)

    # Invariant: Record episodic turn
    with conn:
        conn.execute("INSERT INTO episodes (role, content, session_id) VALUES (?, ?, ?)", ("user", req.message, req.session_id))
        conn.execute("INSERT INTO episodes (role, content, session_id) VALUES (?, ?, ?)", ("assistant", response_text, req.session_id))

    return {
        "response": response_text,
        "model": req.model or "openai-fast",
        "timestamp": datetime.now().strftime("%I:%M:%S %p"),
    }


@app.websocket("/ws")
async def websocket_telemetry(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            conn = get_db()
            with conn:
                ep_count = conn.execute("SELECT COUNT(*) FROM episodes").fetchone()[0]
            payload = {
                "type": "telemetry",
                "time": datetime.now().strftime("%I:%M:%S %p"),
                "status": "Cloud Online 24/7 🌐",
                "episodes": ep_count,
            }
            await ws.send_text(json.dumps(payload))
            await asyncio.sleep(3)
    except (WebSocketDisconnect, ConnectionResetError, OSError):
        pass
    except Exception:
        pass


if __name__ == "__main__":
    import asyncio
    import uvicorn
    logger.info(f"Starting AETHER 24/7 Cloud Consciousness Server on port {PORT}...")
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="info")
