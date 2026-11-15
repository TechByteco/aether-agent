"""
AETHER Agency Vault & API Gateway
=================================
Manages API keys, model provider endpoints, and credentials required
for executing and training the 50+ Agency Specialists across AETHER and LEON.

Key Providers:
1. Google Gemini (GEMINI_API_KEY) — Free Tier, 1M-2M context, active.
2. OpenRouter (OPENROUTER_API_KEY) — Frontier model aggregator (Nex-N2.5, Claude, DeepSeek).
3. Groq Cloud (GROQ_API_KEY) — Ultra-fast LPU inference (800+ tok/s).
4. DeepSeek Official (DEEPSEEK_API_KEY) — Reasoning and code models.
5. Local Ollama (OLLAMA_HOST) — 100% offline edge execution on Snapdragon X.
6. Kaggle (KAGGLE_USERNAME, KAGGLE_KEY) — Free Tesla T4 GPU cloud training cluster.
7. Vercel & Cloudflare (VERCEL_TOKEN, CLOUDFLARE_API_TOKEN) — One-click business deployment.
8. Razorpay (RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET) — Live payment processing.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("aether.agency_vault")

_WORKSPACE = Path(__file__).resolve().parents[3]


class AgencyVault:
    """Central credentials and provider readiness manager for Agency Agents."""

    def __init__(self) -> None:
        self.workspace = _WORKSPACE

    def get_key(self, key_name: str) -> str:
        """Retrieve key from environment or .env file."""
        val = os.getenv(key_name, "").strip()
        if val and not val.startswith("FILL_IN_"):
            return val
        return ""

    def audit_credentials(self) -> Dict[str, Any]:
        """Perform a full audit of all configured API keys for usage & training."""
        gemini_key = self.get_key("GEMINI_API_KEY")
        openrouter_key = self.get_key("OPENROUTER_API_KEY")
        groq_key = self.get_key("GROQ_API_KEY")
        deepseek_key = self.get_key("DEEPSEEK_API_KEY")
        kaggle_user = self.get_key("KAGGLE_USERNAME")
        kaggle_key = self.get_key("KAGGLE_KEY")
        vercel_tok = self.get_key("VERCEL_TOKEN")
        cf_tok = self.get_key("CLOUDFLARE_API_TOKEN")
        rzp_id = self.get_key("RAZORPAY_KEY_ID")
        rzp_sec = self.get_key("RAZORPAY_KEY_SECRET")

        return {
            "inference_backends": {
                "gemini": {
                    "configured": bool(gemini_key),
                    "description": "Google Gemini 3.8 / 2.5 Flash & Pro (1M-2M context)",
                    "tier": "Primary Active Cloud Provider" if gemini_key else "Missing",
                    "status": "ready" if gemini_key else "missing_key",
                },
                "openrouter": {
                    "configured": bool(openrouter_key),
                    "description": "OpenRouter: Nex-N2.5-mini, Claude 3.7, DeepSeek-R1",
                    "tier": "Escalation & Frontier Aggregator",
                    "status": "ready" if openrouter_key else "optional_missing",
                },
                "groq": {
                    "configured": bool(groq_key),
                    "description": "Groq LPU: Llama 3.3 70B & DeepSeek R1 (800+ tok/s)",
                    "tier": "Ultra-Fast Reflex Free Tier",
                    "status": "ready" if groq_key else "optional_missing",
                },
                "deepseek": {
                    "configured": bool(deepseek_key),
                    "description": "DeepSeek API: R1 reasoning & V3 coder",
                    "tier": "Native Reasoning",
                    "status": "ready" if deepseek_key else "optional_missing",
                },
                "ollama": {
                    "configured": True,
                    "description": "Local Snapdragon X Oryon CPU / aether:finetuned",
                    "tier": "Offline Private Edge Execution",
                    "status": "ready",
                },
            },
            "training_cluster": {
                "kaggle": {
                    "configured": bool(kaggle_user and kaggle_key),
                    "username": kaggle_user or "saalimin",
                    "description": "Free Kaggle Tesla T4 GPU fine-tuning & GGUF quantization",
                    "status": "ready" if (kaggle_user and kaggle_key) else "needs_kaggle_key",
                },
                "local_lora": {
                    "configured": True,
                    "description": "Local procedural heuristic ingestion & SQLite FTS5 training",
                    "status": "ready",
                },
            },
            "deployment_and_monetization": {
                "vercel": {"configured": bool(vercel_tok), "status": "ready" if vercel_tok else "missing"},
                "cloudflare": {"configured": bool(cf_tok), "status": "ready" if cf_tok else "missing"},
                "razorpay": {"configured": bool(rzp_id), "status": "ready" if rzp_id else "missing"},
            },
        }

    def resolve_best_agent_backend(self) -> Dict[str, str]:
        """Determine which backend will run the agency agents based on available keys."""
        if self.get_key("OPENROUTER_API_KEY"):
            return {
                "provider": "openrouter",
                "model": "nex-agi/nex-n2.5-mini",
                "label": "OpenRouter Nex-N2.5-mini Escalation Cortex",
            }
        elif self.get_key("GEMINI_API_KEY"):
            return {
                "provider": "gemini",
                "model": "gemini-flash-latest",
                "label": "Google Gemini Flash (High-Speed & 1M Context)",
            }
        elif self.get_key("GROQ_API_KEY"):
            return {
                "provider": "groq",
                "model": "llama-3.3-70b-versatile",
                "label": "Groq Llama 3.3 70B (800 tok/s)",
            }
        return {
            "provider": "ollama",
            "model": "aether:finetuned",
            "label": "Local Ollama Snapdragon X (Offline)",
        }


agency_vault = AgencyVault()
