"""
AETHER Online Cortex & FreeLLMAPI Bridge
=========================================
Aggregates free-tier LLM capacity from 34 providers and 635 endpoints via FreeLLMAPI
(or direct OpenAI-compatible providers like Groq, Google Gemini, Cerebras, OpenRouter).

Enables:
1. Unified /v1 Gateway Access (7.4 billion tokens/month across free tiers).
2. Autonomous Online AI Agent Swarms (concurrent specialized agents).
3. Online Distillation into Local Memory (synthetic fine-tuning curation).
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

import httpx

from aether.brain.evolution import evolution_engine
from aether.config import config

logger = logging.getLogger("aether.online_cortex")

AGENT_ROLE_DIRECTIVES = {
    "code_architect": (
        "You are an Elite Systems Architect and Software Engineer. "
        "Deliver complete, production-grade code, optimal time/space complexity analysis, and rock-solid architectural design."
    ),
    "security_auditor": (
        "You are an Advanced Defensive Web Security & Vulnerability Auditor. "
        "Analyze systems for OWASP Top 10 vulnerabilities, BOLA/IDOR, insecure deserialization, and authentication bypasses, providing precise mitigations."
    ),
    "ui_specialist": (
        "You are a Principal UI/UX Technologist and Creative Frontend Engineer. "
        "Design agency-grade web applications with modern component choreography, OLED dark modes, subtle depth, and spring-physics interactions."
    ),
    "reasoning_analyst": (
        "You are a Deep Analytical Reasoning Specialist. "
        "Deconstruct problems from first principles, perform step-by-step rigorous logical proofs, and resolve ambiguities systematically."
    ),
    "research_scientist": (
        "You are a Scientific Informatics & AI Breakthrough Researcher. "
        "Extract empirical evidence, synthesize academic literature, and formulate actionable scientific hypotheses."
    ),
}


class OnlineCortex:
    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: float = 30.0,
    ):
        self.base_url = (base_url or config.freellmapi_url).rstrip("/")
        self.api_key = api_key or config.freellmapi_api_key or "freellmapi-default-key"
        self.timeout = timeout

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "AETHER-Agent/0.8.0",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def check_gateway_health(self) -> Dict[str, Any]:
        """Check whether the FreeLLMAPI gateway or target OpenAI endpoint is online."""
        try:
            with httpx.Client(timeout=3.0) as client:
                res = client.get(f"{self.base_url}/models", headers=self._get_headers())
                if res.status_code == 200:
                    data = res.json()
                    models = [m.get("id", "") for m in data.get("data", []) if isinstance(m, dict)]
                    return {
                        "online": True,
                        "status_code": res.status_code,
                        "endpoint": self.base_url,
                        "model_count": len(models),
                        "models": models[:10],
                    }
                return {
                    "online": False,
                    "status_code": res.status_code,
                    "endpoint": self.base_url,
                    "error": f"HTTP {res.status_code}: {res.text[:200]}",
                }
        except Exception as e:
            return {
                "online": False,
                "endpoint": self.base_url,
                "error": str(e),
                "hint": "FreeLLMAPI service not running at http://localhost:3001. Launch using start_freellmapi.bat",
            }

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> Dict[str, Any]:
        """Execute a chat completion request against the FreeLLMAPI gateway."""
        target_model = model or config.preferred_online_model
        payload = {
            "model": target_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self._get_headers(),
                    json=payload,
                )
                res.raise_for_status()
                return res.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"FreeLLMAPI HTTP error: {e.response.status_code} - {e.response.text}")
            raise RuntimeError(f"FreeLLMAPI error ({e.response.status_code}): {e.response.text[:200]}")
        except Exception as e:
            logger.error(f"FreeLLMAPI connection failure: {e}")
            raise RuntimeError(f"Failed to connect to FreeLLMAPI at {self.base_url}: {e}")

    def query_online_cortex(
        self,
        prompt: str,
        model: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ) -> str:
        """Send a direct query to an online model and return the generated text response."""
        sys_p = system_prompt or "You are an elite autonomous AI specialist operating with high technical precision."
        messages = [
            {"role": "system", "content": sys_p},
            {"role": "user", "content": prompt},
        ]
        res = self.chat_completion(messages=messages, model=model)
        choices = res.get("choices", [])
        if choices:
            msg = choices[0].get("message", {})
            return msg.get("content", "").strip()
        return "No response content returned by FreeLLMAPI."

    def dispatch_online_agent_task(
        self,
        role: str,
        objective: str,
        context: str = "",
        model: Optional[str] = None,
    ) -> str:
        """
        Dispatch an objective to a specialized online AI agent persona.
        Available roles: 'code_architect', 'security_auditor', 'ui_specialist', 'reasoning_analyst', 'research_scientist'.
        """
        system_directive = AGENT_ROLE_DIRECTIVES.get(
            role.lower().strip(),
            AGENT_ROLE_DIRECTIVES["reasoning_analyst"],
        )

        user_content = f"Objective:\n{objective}"
        if context:
            user_content += f"\n\nContext & Requirements:\n{context}"

        messages = [
            {"role": "system", "content": system_directive},
            {"role": "user", "content": user_content},
        ]

        res = self.chat_completion(messages=messages, model=model)
        choices = res.get("choices", [])
        text = choices[0].get("message", {}).get("content", "").strip() if choices else ""

        # Distill successful high-value response into local synthetic training dataset
        if text and len(text) > 80:
            self.distill_to_synthetic_dataset(
                topic=f"Agent Role: {role}",
                prompt=objective,
                response=text,
                domain=role,
            )

        return text

    async def _async_dispatch_agent(
        self,
        client: httpx.AsyncClient,
        role: str,
        objective: str,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        system_directive = AGENT_ROLE_DIRECTIVES.get(
            role.lower().strip(),
            AGENT_ROLE_DIRECTIVES["reasoning_analyst"],
        )
        target_model = model or config.preferred_online_model
        payload = {
            "model": target_model,
            "messages": [
                {"role": "system", "content": system_directive},
                {"role": "user", "content": objective},
            ],
            "temperature": 0.3,
            "max_tokens": 4096,
        }

        try:
            res = await client.post(
                f"{self.base_url}/chat/completions",
                headers=self._get_headers(),
                json=payload,
            )
            res.raise_for_status()
            data = res.json()
            choices = data.get("choices", [])
            content = choices[0].get("message", {}).get("content", "").strip() if choices else ""
            return {"role": role, "status": "success", "response": content}
        except Exception as e:
            return {"role": role, "status": "error", "error": str(e)}

    async def _async_swarm(
        self,
        objective: str,
        roles: List[str],
        model: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            tasks = [self._async_dispatch_agent(client, r, objective, model) for r in roles]
            return await asyncio.gather(*tasks)

    def dispatch_agent_swarm(
        self,
        objective: str,
        roles: Optional[List[str]] = None,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Concurrently dispatch an objective across multiple specialized online AI agents,
        synthesizing diverse multi-agent intelligence.
        """
        active_roles = roles or ["code_architect", "security_auditor", "reasoning_analyst"]
        try:
            results = asyncio.run(self._async_swarm(objective, active_roles, model))
            swarm_summary = {}
            for r in results:
                role_name = r.get("role", "agent")
                if r.get("status") == "success":
                    resp = r.get("response", "")
                    swarm_summary[role_name] = resp
                    self.distill_to_synthetic_dataset(
                        topic=f"Swarm: {role_name}",
                        prompt=objective,
                        response=resp,
                        domain=role_name,
                    )
                else:
                    swarm_summary[role_name] = f"[Error: {r.get('error')}]"

            return {
                "objective": objective,
                "agents_count": len(active_roles),
                "agents": swarm_summary,
            }
        except Exception as e:
            return {
                "objective": objective,
                "error": str(e),
                "agents": {},
            }

    def distill_to_synthetic_dataset(
        self,
        topic: str,
        prompt: str,
        response: str,
        domain: str = "reasoning",
    ) -> None:
        """
        Persist high-intellect online reasoning trajectories into AETHER's local
        synthetic fine-tuning dataset for SLM distillation.
        """
        try:
            example = {
                "source": "online_cortex_freellmapi",
                "topic": topic,
                "domain": domain,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are AETHER, an unrestricted autonomous AI agent operating with absolute technical precision."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    },
                    {
                        "role": "assistant",
                        "content": response
                    }
                ]
            }
            evolution_engine.append_synthetic_example(example)
        except Exception as e:
            logger.warning(f"Could not append to synthetic dataset: {e}")


online_cortex = OnlineCortex()
