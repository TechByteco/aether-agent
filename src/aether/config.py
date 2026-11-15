"""
AETHER Configuration Module
Handles model selection, cloud acceleration keys, memory persistence paths, and hardware guardrails.
Optimized for ultra-low RAM footprint and Snapdragon Oryon CPU compute.

HARDWARE PROFILE — Snapdragon X (8-Core Oryon, 16GB LPDDR5x):
  - All 8 cores are high-performance Oryon (no big.LITTLE)
  - 135.3 GB/s peak memory bandwidth (LPDDR5x-8448, 8-channel)
  - ARM NEON + DotProd + I8MM (no SVE/SVE2)
  - 45 TOPS Hexagon NPU (future use)
  - Safe AI RAM budget: ≤10 GB (OS takes ~4.2 GB)
"""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Load environment variables from .env if present
_env_path = Path(__file__).resolve().parent.parent.parent / ".env"
if _env_path.exists():
    load_dotenv(dotenv_path=_env_path)
else:
    load_dotenv()


def _detect_power_profile() -> dict:
    """
    Detect AC vs battery power and return optimized inference parameters.
    
    AC Power:  6 threads, 10m keep_alive, 8192 context — max performance
    Battery:   4 threads, 2m keep_alive, 4096 context — race-to-sleep, cool & quiet
    """
    try:
        import psutil
        battery = psutil.sensors_battery()
        on_battery = battery is not None and not battery.power_plugged
    except Exception:
        on_battery = False

    if on_battery:
        return {
            "num_threads": 4,
            "keep_alive": "2m",
            "context_window": 4096,
            "temperature": 0.2,
        }
    else:
        return {
            "num_threads": 6,
            "keep_alive": "10m",
            "context_window": 8192,
            "temperature": 0.4,
        }


# Resolve power profile at import time (re-evaluate on restart or config reload)
_power = _detect_power_profile()


class AetherConfig(BaseModel):
    # ─── Cognitive Mode & Routing Settings ───────────────────────────────
    # Modes: 'auto', 'turbo_reflex', 'codex_agent', 'deep_reasoning', 'local_sovereign'
    cognitive_mode: str = "auto"

    # aether:finetuned — Native fine-tuned cognitive model on Snapdragon X
    local_model: str = "aether:finetuned"
    vision_model: str = "moondream:latest"         # Local screen & image vision
    code_model: str = "qwen2.5-coder:3b"         # High-precision coding
    embedding_model: str = "nomic-embed-text"     # 8192 ctx, 274MB, Matryoshka dims

    # Autonomous Self-Directed Continuous Learning
    auto_learning_enabled: bool = True

    # Dynamic power-aware inference parameters
    keep_alive: str = _power["keep_alive"]
    context_window: int = _power["context_window"]
    num_threads: int = _power["num_threads"]
    temperature: float = _power["temperature"]

    # Vision model uses a capped context (images need ≤2048 tokens)
    vision_context: int = 2048

    # ─── Cloud Acceleration & Multi-Provider Credentials ─────────────────
    groq_api_key: str = Field(default_factory=lambda: os.getenv("GROQ_API_KEY", ""))
    gemini_api_key: str = Field(default_factory=lambda: os.getenv("GEMINI_API_KEY", os.getenv("GOOGLE_API_KEY", "")))
    openrouter_api_key: str = Field(default_factory=lambda: os.getenv("OPENROUTER_API_KEY", ""))
    deepseek_api_key: str = Field(default_factory=lambda: os.getenv("DEEPSEEK_API_KEY", ""))
    active_cloud_provider: str = "auto"

    # ─── Online Cortex & FreeLLMAPI Bridge ──────────────────────────────
    freellmapi_url: str = "http://localhost:3001/v1"
    freellmapi_api_key: str = ""
    online_cortex_enabled: bool = True
    preferred_online_model: str = "freellmapi/auto"

    # ─── Memory Persistence ──────────────────────────────────────────────
    data_dir: Path = Field(
        default_factory=lambda: Path(__file__).resolve().parent.parent.parent / "data" / "memory"
    )

    # ─── Hardware Guardrails ─────────────────────────────────────────────
    max_ram_percent: float = 99.8
    min_free_ram_mb: int = 50
    warn_ram_percent: float = 95.0

    def init_storage(self) -> None:
        """Ensure memory directories exist."""
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def refresh_power_profile(self) -> None:
        """Re-detect AC/battery state and update inference parameters dynamically."""
        profile = _detect_power_profile()
        self.num_threads = profile["num_threads"]
        self.keep_alive = profile["keep_alive"]
        self.context_window = profile["context_window"]
        self.temperature = profile["temperature"]


config = AetherConfig()
config.init_storage()
