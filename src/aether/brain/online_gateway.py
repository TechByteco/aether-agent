"""
AETHER Sovereign Online Gateway
Provides zero-cost, zero-API-key free public AI inference (Pollinations.ai / HuggingFace)
and instant zero-cost public HTTPS tunneling (Serveo, Localtunnel, Pinggy) for global remote access.
"""

import json
import logging
import os
import re
import socket
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

import httpx

logger = logging.getLogger("aether.brain.online_gateway")

# 100% Free Public AI Endpoints (No API key, No credit card required)
POLLINATIONS_API_URL = "https://text.pollinations.ai/openai/v1/chat/completions"
POLLINATIONS_MODELS_URL = "https://text.pollinations.ai/models"
POLLINATIONS_RAW_URL = "https://text.pollinations.ai"


class OnlineGateway:
    """
    Sovereign Gateway for Free Online AI Reasoning & Global Web Tunneling.
    """

    def __init__(self):
        self._tunnel_proc: Optional[subprocess.Popen] = None
        self._tunnel_provider: Optional[str] = None
        self._tunnel_url: Optional[str] = None
        self._tunnel_port: int = 8000
        self._tunnel_start_time: Optional[float] = None
        self._lock = threading.Lock()
        self._cached_models: List[Dict[str, Any]] = []

    # =========================================================================
    # 1. FREE ONLINE AI INFERENCE
    # =========================================================================

    def query_free_ai(
        self,
        prompt: str,
        model: str = "openai",
        system_prompt: str = "",
        temperature: float = 0.5,
        max_tokens: int = 2048,
        timeout: float = 25.0,
    ) -> Dict[str, Any]:
        """
        Query zero-cost online AI models via Pollinations.ai free public gateway.
        Supports models: 'openai' (GPT-OSS 20B / GPT-4o-mini), 'deepseek', 'mistral', 'qwen', 'llama'.
        """
        if not prompt or not prompt.strip():
            return {"error": "Prompt cannot be empty", "text": "", "model": model, "provider": "pollinations.ai"}

        # Build ChatML compliant message list enforcing role alternation
        messages = []
        if system_prompt and system_prompt.strip():
            messages.append({"role": "system", "content": system_prompt.strip()})
        messages.append({"role": "user", "content": prompt.strip()})

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }

        start_t = time.time()
        try:
            with httpx.Client(timeout=timeout) as client:
                res = client.post(
                    POLLINATIONS_API_URL,
                    json=payload,
                    headers={"Content-Type": "application/json", "Accept": "application/json"},
                )

                if res.status_code == 200:
                    data = res.json()
                    choices = data.get("choices", [])
                    if choices:
                        content = choices[0].get("message", {}).get("content", "").strip()
                        duration = time.time() - start_t
                        return {
                            "success": True,
                            "text": content,
                            "model": model,
                            "provider": "pollinations.ai (Free)",
                            "duration_secs": round(duration, 3),
                        }

                # Fallback: Raw text endpoint with URL encoding
                import urllib.parse
                encoded_prompt = urllib.parse.quote(prompt[:500], safe="")
                raw_url = f"{POLLINATIONS_RAW_URL}/{encoded_prompt}"
                res_raw = client.get(raw_url, params={"model": model, "system": system_prompt})
                if res_raw.status_code == 200 and res_raw.text.strip():
                    duration = time.time() - start_t
                    return {
                        "success": True,
                        "text": res_raw.text.strip(),
                        "model": model,
                        "provider": "pollinations.ai (Raw Free)",
                        "duration_secs": round(duration, 3),
                    }

                return {
                    "success": False,
                    "error": f"HTTP {res.status_code}: {res.text[:200]}",
                    "text": "",
                    "model": model,
                    "provider": "pollinations.ai",
                }

        except Exception as e:
            logger.warning(f"Free AI query failed on model '{model}': {e}")
            return {
                "success": False,
                "error": str(e),
                "text": "",
                "model": model,
                "provider": "pollinations.ai",
            }

    def stream_free_ai(
        self,
        prompt: str,
        model: str = "openai",
        system_prompt: str = "",
        timeout: float = 30.0,
    ) -> Generator[str, None, None]:
        """
        Stream tokens from free online AI endpoint for real-time rendering.
        """
        messages = []
        if system_prompt and system_prompt.strip():
            messages.append({"role": "system", "content": system_prompt.strip()})
        messages.append({"role": "user", "content": prompt.strip()})

        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
        }

        try:
            with httpx.stream("POST", POLLINATIONS_API_URL, json=payload, timeout=timeout) as response:
                for line in response.iter_lines():
                    if not line:
                        continue
                    if line.startswith("data: "):
                        line_data = line[6:].strip()
                        if line_data == "[DONE]":
                            break
                        try:
                            chunk_json = json.loads(line_data)
                            delta = chunk_json.get("choices", [{}])[0].get("delta", {})
                            token = delta.get("content", "")
                            if token:
                                yield token
                        except Exception:
                            continue
        except Exception as e:
            yield f"\n[Stream Error: {e}]"

    def list_free_models(self) -> List[Dict[str, Any]]:
        """
        List all active free models available on the public gateway.
        """
        if self._cached_models:
            return self._cached_models
        try:
            with httpx.Client(timeout=8.0) as client:
                res = client.get(POLLINATIONS_MODELS_URL)
                if res.status_code == 200:
                    self._cached_models = res.json()
                    return self._cached_models
        except Exception:
            pass

        # Built-in fallback catalog of known free models
        self._cached_models = [
            {"name": "openai", "description": "GPT-OSS 20B Reasoning / GPT-4o-mini", "reasoning": True, "tier": "free"},
            {"name": "openai-fast", "description": "High-Speed GPT-OSS 20B Reasoning LLM", "reasoning": True, "tier": "free"},
            {"name": "qwen", "description": "Qwen 2.5 Coder & Reasoning", "reasoning": True, "tier": "free"},
            {"name": "mistral", "description": "Mistral Nemo 12B Instruct", "reasoning": False, "tier": "free"},
            {"name": "deepseek", "description": "DeepSeek R1 / V3 Reasoning", "reasoning": True, "tier": "free"},
            {"name": "llama", "description": "Llama 3.3 70B Instruct", "reasoning": False, "tier": "free"},
        ]
        return self._cached_models

    # =========================================================================
    # 2. FREE PUBLIC HTTPS WEB TUNNELING
    # =========================================================================

    def start_tunnel(self, provider: str = "auto", port: int = 8000) -> Dict[str, Any]:
        """
        Launch a zero-cost public HTTPS tunnel to expose local AETHER Web HUD.
        Supports providers: 'serveo', 'localtunnel', 'pinggy', 'localhost_run', 'auto'.
        """
        with self._lock:
            if self._tunnel_proc and self._tunnel_proc.poll() is None and self._tunnel_url:
                return {
                    "success": True,
                    "status": "already_running",
                    "provider": self._tunnel_provider,
                    "url": self._tunnel_url,
                    "port": self._tunnel_port,
                    "uptime_secs": round(time.time() - (self._tunnel_start_time or time.time()), 1),
                }

            self.stop_tunnel()
            self._tunnel_port = port

            provider_order = ["localtunnel", "serveo", "pinggy"] if provider == "auto" else [provider]

            for prov in provider_order:
                try:
                    res = self._spawn_tunnel_process(prov, port)
                    if res.get("success") and res.get("url"):
                        self._tunnel_provider = prov
                        self._tunnel_url = res["url"]
                        self._tunnel_start_time = time.time()
                        return {
                            "success": True,
                            "status": "online",
                            "provider": prov,
                            "url": self._tunnel_url,
                            "port": port,
                            "started_at": datetime.now().isoformat(),
                        }
                except Exception as e:
                    logger.warning(f"Tunnel provider {prov} failed to launch: {e}")
                    continue

            return {
                "success": False,
                "error": "All public tunnel providers failed to establish a connection",
                "status": "offline",
            }

    def _spawn_tunnel_process(self, provider: str, port: int) -> Dict[str, Any]:
        """Spawn background process for specific tunnel provider and extract live URL."""
        import shutil
        flags = 0x08000000 | 0x00000200 if sys.platform == "win32" else 0  # CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP

        if provider == "localtunnel":
            npx_bin = shutil.which("npx.cmd") or shutil.which("npx") or r"C:\Program Files\nodejs\npx.cmd"
            cmd = [npx_bin, "--yes", "localtunnel", "--port", str(port)]
            pattern = r'https://[a-zA-Z0-9.\-_]+loca\.lt'
        elif provider == "serveo":
            cmd = ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "ServerAliveInterval=30", "-R", f"80:localhost:{port}", "serveo.net"]
            pattern = r'https://[a-zA-Z0-9.\-_]+(?:\.serveousercontent\.com|\.serveo\.net)'
        elif provider == "pinggy":
            cmd = ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "ServerAliveInterval=30", "-p", "443", f"-R0:localhost:{port}", "a.pinggy.io"]
            pattern = r'https://[a-zA-Z0-9.\-_]+\.pinggy\.(?:link|io)'
        elif provider == "localhost_run":
            cmd = ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "ServerAliveInterval=30", "-R", f"80:localhost:{port}", "nokey@localhost.run"]
            pattern = r'https://[a-zA-Z0-9.\-_]+\.lhr\.life'
        else:
            return {"success": False, "error": f"Unknown tunnel provider: {provider}"}

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            creationflags=flags,
        )

        extracted_url = []

        def _reader_worker():
            try:
                for line in iter(proc.stdout.readline, ''):
                    if not line:
                        break
                    m = re.search(pattern, line)
                    if m:
                        extracted_url.append(m.group(0))
                        break
            except Exception:
                pass

        reader_t = threading.Thread(target=_reader_worker, daemon=True)
        reader_t.start()
        reader_t.join(timeout=8.0)

        if extracted_url and proc.poll() is None:
            self._tunnel_proc = proc
            return {"success": True, "url": extracted_url[0]}

        try:
            proc.terminate()
            proc.wait(timeout=1.0)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass

        return {"success": False, "error": f"Provider {provider} did not return a public URL within timeout"}

    def get_tunnel_status(self) -> Dict[str, Any]:
        """Check live status of the public HTTPS tunnel."""
        with self._lock:
            if self._tunnel_proc and self._tunnel_proc.poll() is None and self._tunnel_url:
                uptime = round(time.time() - (self._tunnel_start_time or time.time()), 1)
                return {
                    "active": True,
                    "status": "online",
                    "provider": self._tunnel_provider,
                    "url": self._tunnel_url,
                    "port": self._tunnel_port,
                    "uptime_seconds": uptime,
                }
            return {
                "active": False,
                "status": "offline",
                "provider": None,
                "url": None,
                "port": self._tunnel_port,
                "uptime_seconds": 0,
            }

    def stop_tunnel(self) -> Dict[str, Any]:
        """Terminate the active public tunnel process and all child processes."""
        with self._lock:
            if self._tunnel_proc:
                try:
                    if sys.platform == "win32":
                        subprocess.run(["taskkill", "/F", "/T", "/PID", str(self._tunnel_proc.pid)], capture_output=True)
                    else:
                        self._tunnel_proc.terminate()
                        self._tunnel_proc.wait(timeout=2.0)
                except Exception:
                    try:
                        self._tunnel_proc.kill()
                    except Exception:
                        pass
                self._tunnel_proc = None
            old_url = self._tunnel_url
            self._tunnel_url = None
            self._tunnel_provider = None
            self._tunnel_start_time = None
            return {"success": True, "status": "stopped", "previous_url": old_url}


# Global singleton
online_gateway = OnlineGateway()


# =============================================================================
# Native Tool Definitions for AETHER Engine & Skills Galaxy
# =============================================================================

def tool_query_free_online_ai(prompt: str, model: str = "openai", system_directive: str = "") -> str:
    """Query 100% free, zero-cost, zero-API-key public AI models (e.g. GPT-OSS 20B, DeepSeek, Qwen, Mistral) via Pollinations.ai gateway."""
    res = online_gateway.query_free_ai(prompt=prompt, model=model, system_prompt=system_directive)
    if res.get("success"):
        return (
            f"### 🌐 Free Online AI Response ({res.get('model', model)} via {res.get('provider')})\n\n"
            f"{res.get('text')}\n\n"
            f"*Latency: {res.get('duration_secs')}s | Cost: $0.00 (100% Free Public Gateway)*"
        )
    return f"Free Online AI Query Error: {res.get('error', 'Unknown error')}"


def tool_start_online_tunnel(provider: str = "auto", port: int = 8000) -> str:
    """Launch an instant zero-cost public HTTPS tunnel (Serveo/Localtunnel/Pinggy) to make AETHER accessible from any internet browser or smartphone."""
    res = online_gateway.start_tunnel(provider=provider, port=int(port))
    if res.get("success"):
        return (
            f"### 🚀 AETHER Is Now Live Online!\n"
            f"- **Public URL:** {res['url']}\n"
            f"- **Provider:** {res['provider'].upper()} (100% Free Public Tunnel)\n"
            f"- **Local Port:** {res['port']}\n"
            f"- **Status:** ACTIVE & ACCESSIBLE\n\n"
            f"You can open this URL from any smartphone, remote laptop, or tablet to access AETHER's Glassmorphic HUD & Voice interface worldwide."
        )
    return f"Failed to launch online tunnel: {res.get('error', 'Unknown error')}"


def tool_get_online_tunnel_status() -> str:
    """Check the operational connectivity and public URL of the active online tunnel."""
    st = online_gateway.get_tunnel_status()
    if st.get("active"):
        return (
            f"### 🌐 Online Gateway Status: ONLINE\n"
            f"- **Public URL:** {st['url']}\n"
            f"- **Provider:** {str(st['provider']).upper()}\n"
            f"- **Local Port:** {st['port']}\n"
            f"- **Uptime:** {st['uptime_seconds']} seconds"
        )
    return "### 🌐 Online Gateway Status: OFFLINE (Localhost only on port 8000)"


def tool_stop_online_tunnel() -> str:
    """Stop the public online tunnel and return AETHER to localhost-only mode."""
    res = online_gateway.stop_tunnel()
    return f"Online tunnel stopped. AETHER is now in localhost-only mode. (Previous URL: {res.get('previous_url')})"


def tool_list_free_online_models() -> str:
    """List all available 100% free online AI models that require no API keys."""
    models = online_gateway.list_free_models()
    lines = ["### 🤖 Available Free Online AI Models (Zero-Cost / No API Key):"]
    for m in models:
        lines.append(f"- **{m.get('name')}**: {m.get('description', 'Reasoning / General LLM')}")
    return "\n".join(lines)
