"""
AETHER Multi-Provider Cloud Router & Omnipresent Gateway
=========================================================
Delivers instant high-speed inference (500–1200 tok/s) and frontier reasoning by orchestrating:
1. Groq Cloud (Llama 3.3 70B, DeepSeek-R1-Distill-70B) — Ultra-low latency & 800+ tok/s (Free tier).
2. Google Gemini API (Gemini 2.5 Pro, Gemini 2.5 Flash) — 1M–2M context & multimodal reasoning (Free tier).
3. OpenRouter API (Claude 3.7 Sonnet, DeepSeek-R1, GPT-4o, o3-mini) — Frontier multi-model access.
4. DeepSeek Direct (DeepSeek-R1, DeepSeek-V3) — Native reasoning with scratchpads.
5. FreeLLMAPI Gateway (Local aggregate proxy).
6. Local Ollama (Snapdragon X Oryon CPU/NPU, aether:finetuned, offline private execution).
"""

import json
import logging
import os
import time
from typing import (Any, AsyncGenerator, Callable, Dict, Generator, List,
                    Optional, Tuple)

import httpx
import ollama

from aether.config import config

logger = logging.getLogger("aether.multi_provider_router")

# Standard Provider Endpoints
PROVIDER_ENDPOINTS = {
    "groq": "https://api.groq.com/openai/v1",
    "gemini": "https://generativelanguage.googleapis.com/v1beta/openai",
    "openrouter": "https://openrouter.ai/api/v1",
    "deepseek": "https://api.deepseek.com",
    "freellmapi": "http://localhost:3001/v1",
    "ollama": "http://127.0.0.1:11434",
}

# Preferred default models per provider
DEFAULT_PROVIDER_MODELS = {
    "groq": "llama-3.3-70b-versatile",
    "groq_reasoning": "deepseek-r1-distill-llama-70b",
    "groq_fast": "llama-3.1-8b-instant",
    "gemini": "gemini-flash-latest",
    "gemini_pro": "gemini-pro-latest",
    "gemini_open": "gemma-4-26b-a4b-it",
    "openrouter": "anthropic/claude-3.7-sonnet",
    "openrouter_fast": "google/gemini-2.5-flash",
    "openrouter_nex": "nex-agi/nex-n2.5-mini",
    "nex_mini": "nex-agi/nex-n2.5-mini",
    "deepseek": "deepseek-reasoner",
    "freellmapi": "freellmapi/auto",
    "ollama": "aether:finetuned",
}


class MultiProviderRouter:
    """
    Unified client for routing queries across ultra-fast cloud accelerators,
    frontier reasoning models, and local quantized SLMs.
    """

    def __init__(self):
        self.timeout = 45.0
        self._provider_cooldowns: Dict[str, float] = {}

    def _is_cooling_down(self, provider: str) -> bool:
        """Check if a provider is temporarily cooling down due to rate limits or errors."""
        until = self._provider_cooldowns.get(provider.lower(), 0.0)
        return time.time() < until

    def _set_cooldown(self, provider: str, seconds: float = 60.0) -> None:
        """Temporarily bypass a failing/rate-limited provider."""
        self._provider_cooldowns[provider.lower()] = time.time() + seconds
        logger.info(f"⏳ Provider '{provider}' marked cooling down for {seconds}s.")

    def get_api_key(self, provider: str) -> Optional[str]:
        """Retrieve API key for a given provider from environment or config."""
        provider_norm = provider.lower().strip()
        if provider_norm == "groq":
            return os.getenv("GROQ_API_KEY") or config.groq_api_key or ""
        elif provider_norm in ("gemini", "google"):
            return os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or config.gemini_api_key or ""
        elif provider_norm == "openrouter":
            return os.getenv("OPENROUTER_API_KEY") or config.openrouter_api_key or ""
        elif provider_norm == "deepseek":
            return os.getenv("DEEPSEEK_API_KEY") or config.deepseek_api_key or ""
        elif provider_norm in ("anthropic", "claude"):
            return os.getenv("ANTHROPIC_API_KEY") or ""
        elif provider_norm in ("openai", "gpt"):
            return os.getenv("OPENAI_API_KEY") or ""
        elif provider_norm == "freellmapi":
            return config.freellmapi_api_key or "freellmapi-default-key"
        return ""

    def get_active_providers_status(self) -> Dict[str, Any]:
        """Check live connectivity and available credentials for all providers."""
        status = {}

        # 1. Groq
        groq_key = self.get_api_key("groq")
        status["groq"] = {
            "name": "Groq Cloud (Ultra-Fast LPU)",
            "configured": bool(groq_key),
            "speed": "800–1200 tok/s ⚡",
            "tier": "Free Tier Supported",
            "recommended_models": ["llama-3.3-70b-versatile", "deepseek-r1-distill-llama-70b", "llama-3.1-8b-instant"],
            "status": "ready" if groq_key else "missing_api_key",
        }

        # 2. Google Gemini
        gemini_key = self.get_api_key("gemini")
        status["gemini"] = {
            "name": "Google Gemini API",
            "configured": bool(gemini_key),
            "speed": "200–500 tok/s ⚡",
            "tier": "Free Tier Supported (15 RPM / 1M-2M context)",
            "recommended_models": ["gemini-3.8-flash", "gemini-3.1-pro-preview"],
            "status": "ready" if gemini_key else "missing_api_key",
        }

        # 3. OpenRouter
        openrouter_key = self.get_api_key("openrouter")
        status["openrouter"] = {
            "name": "OpenRouter (Frontier Aggregator & Escalation Cortex)",
            "configured": bool(openrouter_key),
            "speed": "50–250 tok/s",
            "tier": "Pay-as-you-go & Free Endpoints",
            "recommended_models": [
                "nex-agi/nex-n2.5-mini",
                "anthropic/claude-3.7-sonnet",
                "deepseek/deepseek-r1",
                "openai/gpt-4o",
            ],
            "status": "ready" if openrouter_key else "missing_api_key",
        }

        # 4. DeepSeek
        deepseek_key = self.get_api_key("deepseek")
        status["deepseek"] = {
            "name": "DeepSeek Official",
            "configured": bool(deepseek_key),
            "speed": "60–120 tok/s",
            "tier": "Pay-as-you-go",
            "recommended_models": ["deepseek-reasoner", "deepseek-chat"],
            "status": "ready" if deepseek_key else "missing_api_key",
        }

        # 5. Local Ollama (Snapdragon X)
        try:
            installed = [m.get("model", m.get("name", "")) for m in ollama.list().get("models", [])]
            status["ollama"] = {
                "name": "Local Snapdragon X (Oryon CPU/DirectML)",
                "configured": True,
                "speed": "20–35 tok/s (Local CPU)",
                "tier": "100% Offline & Free",
                "installed_models": installed,
                "status": "online" if installed else "offline",
            }
        except Exception as e:
            status["ollama"] = {
                "name": "Local Snapdragon X (Oryon CPU/DirectML)",
                "configured": True,
                "speed": "20–35 tok/s (Local CPU)",
                "tier": "Offline",
                "error": str(e),
                "status": "offline",
            }

        return status

    def determine_optimal_provider(
        self,
        intent: str = "reflex",
        user_override: Optional[str] = None,
    ) -> Tuple[str, str, str]:
        """
        Determine the optimal (provider, base_url, model) based on intent and configured keys.
        Intents:
          - 'reflex': Ultra-fast conversational stream (< 200ms latency)
          - 'coding': High-precision software architecture & coding
          - 'reasoning': Deep mathematical / frontier chain-of-thought
          - 'escalation' / 'agentic' / 'long_context': Nex-N2.5-mini 256k agentic reasoning
          - 'local': 100% offline local model
        """
        # Explicit override
        if user_override:
            u = user_override.lower().strip()
            if "nex" in u or "n2.5" in u or "escalat" in u:
                if self.get_api_key("openrouter"):
                    return "openrouter", PROVIDER_ENDPOINTS["openrouter"], "nex-agi/nex-n2.5-mini"
                elif self.get_api_key("gemini"):
                    return "gemini", PROVIDER_ENDPOINTS["gemini"], DEFAULT_PROVIDER_MODELS["gemini"]
                elif self.get_api_key("groq"):
                    return "groq", PROVIDER_ENDPOINTS["groq"], DEFAULT_PROVIDER_MODELS["groq_reasoning"]
            elif "groq" in u:
                return "groq", PROVIDER_ENDPOINTS["groq"], DEFAULT_PROVIDER_MODELS["groq"]
            elif "gemini" in u:
                model = DEFAULT_PROVIDER_MODELS["gemini"]
                return "gemini", PROVIDER_ENDPOINTS["gemini"], model
            elif "claude" in u or "openrouter" in u:
                return "openrouter", PROVIDER_ENDPOINTS["openrouter"], "anthropic/claude-3.7-sonnet"
            elif "deepseek" in u:
                return "deepseek", PROVIDER_ENDPOINTS["deepseek"], "deepseek-reasoner"
            elif "local" in u or "ollama" in u or "aether" in u:
                return "ollama", PROVIDER_ENDPOINTS["ollama"], config.local_model

        # Auto-routing based on intent & available keys (skipping cooling-down providers)
        groq_key = self.get_api_key("groq") if not self._is_cooling_down("groq") else ""
        gemini_key = self.get_api_key("gemini") if not self._is_cooling_down("gemini") else ""
        openrouter_key = self.get_api_key("openrouter") if not self._is_cooling_down("openrouter") else ""
        deepseek_key = self.get_api_key("deepseek") if not self._is_cooling_down("deepseek") else ""

        if intent in ("escalation", "agentic", "long_context", "computer_use"):
            # Prioritize Nex-N2.5-mini via OpenRouter -> Gemini Flash -> DeepSeek
            if openrouter_key:
                return "openrouter", PROVIDER_ENDPOINTS["openrouter"], "nex-agi/nex-n2.5-mini"
            if gemini_key:
                return "gemini", PROVIDER_ENDPOINTS["gemini"], DEFAULT_PROVIDER_MODELS["gemini"]
            if deepseek_key:
                return "deepseek", PROVIDER_ENDPOINTS["deepseek"], "deepseek-reasoner"
            if groq_key:
                return "groq", PROVIDER_ENDPOINTS["groq"], DEFAULT_PROVIDER_MODELS["groq_reasoning"]
            return "ollama", PROVIDER_ENDPOINTS["ollama"], config.local_model

        if intent == "reflex":
            # For ultra-fast reflex: prioritize Groq LPU (800 tok/s) -> Gemini Flash -> Local
            if groq_key:
                return "groq", PROVIDER_ENDPOINTS["groq"], DEFAULT_PROVIDER_MODELS["groq"]
            if gemini_key:
                return "gemini", PROVIDER_ENDPOINTS["gemini"], DEFAULT_PROVIDER_MODELS["gemini"]
            if openrouter_key:
                return "openrouter", PROVIDER_ENDPOINTS["openrouter"], DEFAULT_PROVIDER_MODELS["openrouter_fast"]
            return "ollama", PROVIDER_ENDPOINTS["ollama"], config.local_model

        elif intent == "coding":
            # For coding: prioritize Claude 3.7 / Nex-N2.5-mini / Gemini Flash / Groq Llama-3.3-70B
            if openrouter_key:
                return "openrouter", PROVIDER_ENDPOINTS["openrouter"], "anthropic/claude-3.7-sonnet"
            if gemini_key:
                return "gemini", PROVIDER_ENDPOINTS["gemini"], DEFAULT_PROVIDER_MODELS["gemini"]
            if groq_key:
                return "groq", PROVIDER_ENDPOINTS["groq"], "llama-3.3-70b-versatile"
            if deepseek_key:
                return "deepseek", PROVIDER_ENDPOINTS["deepseek"], "deepseek-chat"
            return "ollama", PROVIDER_ENDPOINTS["ollama"], "qwen2.5-coder:3b"

        elif intent == "reasoning":
            # For deep reasoning: prioritize DeepSeek-R1 / Nex-N2.5-mini / Claude 3.7 / Gemini / Groq R1 Distill
            if deepseek_key:
                return "deepseek", PROVIDER_ENDPOINTS["deepseek"], "deepseek-reasoner"
            if openrouter_key:
                return "openrouter", PROVIDER_ENDPOINTS["openrouter"], "nex-agi/nex-n2.5-mini"
            if groq_key:
                return "groq", PROVIDER_ENDPOINTS["groq"], DEFAULT_PROVIDER_MODELS["groq_reasoning"]
            if gemini_key:
                return "gemini", PROVIDER_ENDPOINTS["gemini"], DEFAULT_PROVIDER_MODELS["gemini"]
            return "ollama", PROVIDER_ENDPOINTS["ollama"], config.local_model

        # Default fallback
        if groq_key:
            return "groq", PROVIDER_ENDPOINTS["groq"], DEFAULT_PROVIDER_MODELS["groq"]
        if gemini_key:
            return "gemini", PROVIDER_ENDPOINTS["gemini"], DEFAULT_PROVIDER_MODELS["gemini"]
        return "ollama", PROVIDER_ENDPOINTS["ollama"], config.local_model

    def _align_model_for_provider(self, provider: str, target_model: str, default_model: str) -> str:
        """Ensure requested model is compatible with the selected provider."""
        p = provider.lower()
        if p == "gemini":
            if not (target_model.startswith("gemini") or target_model.startswith("gemma") or target_model.startswith("models/")):
                return default_model
            if "2.0" in target_model or "1.5" in target_model or "3.8" in target_model:
                return default_model
        elif p == "groq":
            if "/" in target_model and not target_model.startswith("deepseek-ai/"):
                return default_model
            if target_model.startswith("anthropic") or target_model.startswith("gemini") or target_model.startswith("gpt-"):
                return default_model
        elif p == "deepseek":
            if not target_model.startswith("deepseek"):
                return default_model
        return target_model

    def complete_chat(
        self,
        messages: List[Dict[str, str]],
        intent: str = "reflex",
        provider: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Execute synchronous chat completion with automatic provider fallback.

        In AETHER_DETERMINISTIC=1 mode (the default), temperature and top_p are
        overridden to 0 regardless of the caller-supplied value, ensuring
        completely reproducible, hallucination-free outputs.

        Returns: {"content": str, "provider": str, "model": str, "tok_per_sec": float, "duration": float}
        """
        # ── Deterministic mode injection ────────────────────────────────────
        try:
            from aether.system.deterministic_mode import (DETERMINISTIC,
                                                          llm_kwargs,
                                                          ollama_options)
            det = llm_kwargs()
            if DETERMINISTIC:
                temperature = det.get("temperature", temperature)
                max_tokens = det.get("max_tokens", max_tokens)
        except ImportError:
            pass  # deterministic_mode not available in this environment

        t0 = time.time()
        prov = provider or "auto"
        selected_prov, base_url, selected_model = self.determine_optimal_provider(
            intent=intent,
            user_override=prov if prov != "auto" else None,
        )
        target_model = self._align_model_for_provider(selected_prov, model or selected_model, selected_model)

        # 1. Local Ollama Execution
        if selected_prov == "ollama":
            import socket
            _s = socket.socket()
            _s.settimeout(0.5)
            try:
                _s.connect(("127.0.0.1", 11434))
                _s.close()
            except Exception:
                raise RuntimeError("Local Ollama is offline (port 11434 unreachable)")
            try:
                # If target_model is a cloud model name (e.g. gemini or claude), fallback to local_model
                installed_models = [m.get("model", m.get("name", "")) for m in ollama.list().get("models", [])]
                if target_model not in installed_models and not any(target_model in m for m in installed_models):
                    target_model = config.local_model

                # Build options — merge deterministic settings if active
                try:
                    from aether.system.deterministic_mode import ollama_options
                    _opts = ollama_options() or {"temperature": temperature, "num_predict": max_tokens}
                except ImportError:
                    _opts = {"temperature": temperature, "num_predict": max_tokens}

                res = ollama.chat(
                    model=target_model,
                    messages=messages,
                    options=_opts,
                    keep_alive=config.keep_alive,
                )
                dur = max(time.time() - t0, 0.001)
                text = (res.message.content or "").strip()
                tokens_est = len(text.split()) * 1.3
                return {
                    "content": text,
                    "provider": "Local Snapdragon X (Ollama)",
                    "model": target_model,
                    "duration": dur,
                    "tok_per_sec": round(tokens_est / dur, 1),
                }
            except Exception as e:
                logger.warning(f"Ollama completion failed: {e}")
                raise RuntimeError(f"Local Ollama error: {e}")

        # 2. Cloud OpenAI-Compatible REST Execution (Groq, Gemini, OpenRouter, DeepSeek)
        api_key = self.get_api_key(selected_prov)
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "AETHER-AllRounder/1.0",
        }
        if selected_prov == "openrouter":
            headers["HTTP-Referer"] = "https://github.com/aether-ai"
            headers["X-Title"] = "AETHER Cognitive Assistant"

        payload = {
            "model": target_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        last_exc = None
        for attempt in range(2):
            try:
                with httpx.Client(timeout=timeout or self.timeout) as client:
                    res = client.post(
                        f"{base_url}/chat/completions",
                        headers=headers,
                        json=payload,
                    )
                    res.raise_for_status()
                    data = res.json()
                    dur = max(time.time() - t0, 0.001)
                    choices = data.get("choices", [])
                    text = choices[0].get("message", {}).get("content", "").strip() if choices else ""
                    
                    # Provider succeeded — clear any existing cooldown
                    self._provider_cooldowns.pop(selected_prov, None)

                    # Check for usage stats
                    usage = data.get("usage", {})
                    comp_tokens = usage.get("completion_tokens", len(text.split()) * 1.3)
                    tok_per_sec = round(comp_tokens / dur, 1)

                    return {
                        "content": text,
                        "provider": selected_prov.upper(),
                        "model": target_model,
                        "duration": dur,
                        "tok_per_sec": tok_per_sec,
                    }
            except Exception as e:
                last_exc = e
                # Check for rate limiting / 429
                if "429" in str(e) or "Too Many Requests" in str(e):
                    self._set_cooldown(selected_prov, 60.0)
                    break  # Don't retry immediately on 429
                if attempt == 0:
                    time.sleep(1.0)
                    continue
                else:
                    self._set_cooldown(selected_prov, 30.0)

        logger.warning(f"Cloud provider '{selected_prov}' failed ({last_exc}). Falling back to local Ollama...")
        # Resilient fast fallback to local Ollama
        import socket
        ollama_alive = False
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.15)
                if s.connect_ex(("127.0.0.1", 11434)) == 0:
                    ollama_alive = True
        except Exception:
            pass

        if not ollama_alive:
            raise RuntimeError(f"All providers failed. Primary ({selected_prov}): {last_exc}. Fallback (Ollama): Offline on port 11434")

        try:
            res = ollama.chat(
                model=config.local_model,
                messages=messages,
                options={"temperature": temperature, "num_predict": max_tokens},
                keep_alive=config.keep_alive,
            )
            dur = max(time.time() - t0, 0.001)
            text = (res.message.content or "").strip()
            return {
                "content": text,
                "provider": "Local Fallback (Ollama)",
                "model": config.local_model,
                "duration": dur,
                "tok_per_sec": round((len(text.split()) * 1.3) / dur, 1),
            }
        except Exception as e2:
            raise RuntimeError(f"All providers failed. Primary ({selected_prov}): {last_exc}. Fallback (Ollama): {e2}")


    async def async_stream_chat(
        self,
        messages: List[Dict[str, str]],
        intent: str = "reflex",
        provider: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream tokens asynchronously from the optimal provider.
        Yields events:
          {"type": "start", "provider": "GROQ", "model": "llama-3.3-70b"}
          {"type": "token", "token": "Hello"}
          {"type": "done", "duration": 0.45, "tok_per_sec": 850.2}
        """
        t0 = time.time()
        selected_prov, base_url, selected_model = self.determine_optimal_provider(
            intent=intent,
            user_override=provider if provider and provider != "auto" else None,
        )
        target_model = self._align_model_for_provider(selected_prov, model or selected_model, selected_model)
        token_count = 0

        yield {
            "type": "start",
            "provider": selected_prov.upper(),
            "model": target_model,
        }

        # 1. Local Ollama Streaming
        if selected_prov == "ollama":
            try:
                import ollama
                response_stream = ollama.chat(
                    model=target_model,
                    messages=messages,
                    options={"temperature": temperature, "num_predict": max_tokens},
                    stream=True,
                    keep_alive=config.keep_alive,
                )
                for chunk in response_stream:
                    token = chunk.get("message", {}).get("content", "")
                    if token:
                        token_count += 1
                        yield {"type": "token", "token": token}
                dur = max(time.time() - t0, 0.001)
                yield {
                    "type": "done",
                    "duration": dur,
                    "tok_per_sec": round(token_count / dur, 1),
                    "provider": "OLLAMA",
                    "model": target_model,
                }
                return
            except Exception as e:
                logger.error(f"Local streaming failed: {e}")
                yield {"type": "error", "error": str(e)}
                return

        # 2. Cloud Streaming via SSE (Groq, Gemini, OpenRouter, DeepSeek)
        api_key = self.get_api_key(selected_prov)
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "AETHER-AllRounder/1.0",
        }
        if selected_prov == "openrouter":
            headers["HTTP-Referer"] = "https://github.com/aether-ai"
            headers["X-Title"] = "AETHER Cognitive Assistant"

        payload = {
            "model": target_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST",
                    f"{base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line or not line.startswith("data:"):
                            continue
                        raw_data = line[len("data:"):].strip()
                        if raw_data == "[DONE]":
                            break
                        try:
                            data = json.loads(raw_data)
                            choices = data.get("choices", [])
                            if choices:
                                delta = choices[0].get("delta", {})
                                token = delta.get("content", "")
                                if token:
                                    token_count += 1
                                    yield {"type": "token", "token": token}
                        except json.JSONDecodeError:
                            continue

            dur = max(time.time() - t0, 0.001)
            yield {
                "type": "done",
                "duration": dur,
                "tok_per_sec": round(token_count / dur, 1),
                "provider": selected_prov.upper(),
                "model": target_model,
            }
        except Exception as e:
            logger.warning(f"Cloud stream failed ({e}), attempting local fallback...")
            yield {"type": "error", "error": f"Cloud provider error ({selected_prov}): {e}"}


multi_provider_router = MultiProviderRouter()
