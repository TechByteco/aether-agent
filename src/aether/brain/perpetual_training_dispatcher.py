"""
AETHER Perpetual Training Dispatcher & Multi-Environment Engine
===============================================================
Coordinates 24/7 continuous training cycles across local and cloud GPU runtimes:
1. Synthesizes new skills via SkillGenesisFactory
2. Formats multi-turn training curricula via AutonomousCurriculumSynthesizer
3. Pushes training jobs to Kaggle Tesla T4 cluster via KaggleController
4. Downloads compiled Q4_K_M GGUF models and mounts them into local Ollama
5. Evaluates benchmark scores and triggers the next domain cycle without stopping!
"""

import json
import logging
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from aether.brain.ast_guard import ast_guard
from aether.brain.autonomous_curriculum_synthesizer import \
    curriculum_synthesizer
from aether.brain.infinite_evolution_orchestrator import infinite_orchestrator
from aether.brain.kaggle_controller import kaggle_controller
from aether.brain.self_play_rlaif_engine import self_play_engine
from aether.brain.skill_genesis_factory import (ALL_ROUNDER_DOMAINS,
                                                skill_factory)
from aether.config import config
from aether.memory.store import memory

logger = logging.getLogger("aether.perpetual_dispatcher")



class PerpetualTrainingDispatcher:
    """
    Perpetual, non-stop autonomous training and domain evolution manager.
    """

    def __init__(self, workspace_root: Optional[Path] = None):
        self.workspace_root = workspace_root or Path(__file__).resolve().parent.parent.parent.parent
        self.state_file = self.workspace_root / "data" / "perpetual_dispatcher_state.json"
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self.current_domain_index = 0
        self.total_dispatched_cycles = 0
        self._load_state()

    def _load_state(self) -> None:
        if self.state_file.exists():
            try:
                data = json.loads(self.state_file.read_text(encoding="utf-8"))
                self.current_domain_index = data.get("current_domain_index", 0) % len(ALL_ROUNDER_DOMAINS)
                self.total_dispatched_cycles = data.get("total_dispatched_cycles", 0)
                return
            except Exception as e:
                logger.warning(f"Error loading dispatcher state: {e}")

        self.current_domain_index = 0
        self.total_dispatched_cycles = 0
        self._save_state()

    def _save_state(self) -> None:
        data = {
            "current_domain_index": self.current_domain_index,
            "current_domain": ALL_ROUNDER_DOMAINS[self.current_domain_index],
            "total_dispatched_cycles": self.total_dispatched_cycles,
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }
        self.state_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def get_current_domain(self) -> str:
        return ALL_ROUNDER_DOMAINS[self.current_domain_index]

    def advance_domain(self) -> str:
        self.total_dispatched_cycles += 1
        self.current_domain_index = (self.current_domain_index + 1) % len(ALL_ROUNDER_DOMAINS)
        self._save_state()
        return self.get_current_domain()

    def execute_evolution_pulse(self) -> Dict[str, Any]:
        """
        Execute a complete end-to-end evolution pulse:
        1. Synthesize domain skill
        2. Synthesize domain training dataset
        3. Execute self-play RLAIF verification cycle
        4. Evaluate model capabilities
        5. Advance domain
        """
        current_dom = self.get_current_domain()
        logger.info(f"⚡ [PerpetualDispatcher] Executing evolution pulse for domain: '{current_dom}'...")

        # 1. Synthesize skill
        skill_ok, skill, msg = skill_factory.synthesize_skill_for_domain(
            current_dom,
            f"Autonomous high-precision handler for {current_dom.replace('_', ' ')}"
        )

        # 2. Synthesize curriculum
        dataset_path = curriculum_synthesizer.synthesize_curriculum_for_domain(current_dom, num_samples=10)

        # 3. Execute self-play RLAIF verification cycle
        self_play_trace = self_play_engine.execute_self_play_cycle(current_dom)

        # 4. Evaluate benchmark
        benchmark = infinite_orchestrator.evaluate_model_capabilities("aether:v3")

        # 5. Advance domain
        next_dom = self.advance_domain()

        return {
            "status": "success",
            "domain_processed": current_dom,
            "skill_created": skill.name if skill else None,
            "dataset_path": str(dataset_path),
            "self_play_trace_id": self_play_trace.trace_id,
            "self_play_reward": self_play_trace.reward_score,
            "benchmark_index": benchmark.get("overall_frontier_index"),
            "next_domain": next_dom,
            "total_completed_pulses": self.total_dispatched_cycles,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def get_status(self) -> Dict[str, Any]:
        return {
            "is_running": self._running,
            "current_domain": self.get_current_domain(),
            "domain_index": self.current_domain_index + 1,
            "total_domains": len(ALL_ROUNDER_DOMAINS),
            "total_dispatched_cycles": self.total_dispatched_cycles,
            "active_vault_skills": len(skill_factory.vault),
            "rlaif_telemetry": self_play_engine.get_telemetry(),
        }



perpetual_dispatcher = PerpetualTrainingDispatcher()
