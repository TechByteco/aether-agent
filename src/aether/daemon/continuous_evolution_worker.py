"""
AETHER Autonomous Continuous Evolution Daemon
==============================================
Runs continuous background self-play, teacher-student distillation, and memory compaction
without blocking active user chat, HUD streaming, or tool execution.
"""

import json
import logging
import os
import threading
import time
from datetime import datetime, timezone
from typing import Optional

from aether.brain.kaggle_controller import kaggle_controller
from aether.brain.multi_provider_router import multi_provider_router
from aether.brain.perpetual_training_dispatcher import perpetual_dispatcher
from aether.brain.teacher_student_engine import (CognitiveStage,
                                                 teacher_student_engine)
from aether.config import config
from aether.memory.store import memory

logger = logging.getLogger("aether.continuous_evolution")


class ContinuousEvolutionWorker:
    def __init__(self, interval_secs: int = 180):
        self.interval_secs = interval_secs
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self.last_run_timestamp: Optional[str] = None
        self.total_autonomous_cycles = 0
        self.last_kaggle_status: Optional[str] = None
        self.active_kernel_slug = "saalimin/aether-dual-t4-parallel-frontier-training-v2"

    def start(self) -> None:
        """Start the background continuous evolution daemon."""
        with self._lock:
            if self._running:
                return
            self._running = True
            self._thread = threading.Thread(target=self._worker_loop, daemon=True, name="AetherEvolutionWorker")
            self._thread.start()
            logger.info("🧬 [Evolution Daemon] Continuous Evolution Worker started in background.")

    def stop(self) -> None:
        """Stop the background worker gracefully."""
        with self._lock:
            self._running = False

    def _worker_loop(self) -> None:
        """Background loop executing evolutionary cycles when resources are healthy."""
        time.sleep(10)  # Initial cold-start grace period

        while self._running:
            try:
                # 1. Autonomous Kaggle Cloud Training Monitor
                self._check_kaggle_training_progress()

                # 2. Check local system resources: do not overload if battery or high RAM
                import psutil
                battery = psutil.sensors_battery()
                on_battery = battery is not None and not battery.power_plugged

                if not on_battery and psutil.cpu_percent(interval=1.0) < 60:
                    logger.info("🧬 [Evolution Daemon] System idle and healthy. Executing evolutionary self-play cycle...")
                    self._execute_cycle()
                else:
                    logger.debug("🧬 [Evolution Daemon] System busy or on battery. Skipping local distillation cycle.")

            except Exception as e:
                logger.error(f"🧬 [Evolution Daemon] Evolution cycle error: {e}")

            # Sleep interval
            for _ in range(self.interval_secs):
                if not self._running:
                    break
                time.sleep(1)

    def _check_kaggle_training_progress(self) -> None:
        """Autonomously monitor Kaggle Cloud GPU training and mount completed models."""
        if not kaggle_controller.is_configured():
            return

        try:
            status_info = kaggle_controller.get_kernel_status(self.active_kernel_slug)
            if not status_info.get("success"):
                return

            status = status_info.get("status", "unknown").lower()
            self.last_kaggle_status = status

            if status == "complete":
                logger.info(f"🎉 [Evolution Daemon] Kaggle GPU kernel '{self.active_kernel_slug}' is COMPLETE! Auto-downloading & mounting weights...")
                dl_res = kaggle_controller.download_kernel_outputs(self.active_kernel_slug)
                if dl_res.get("success"):
                    mount_res = kaggle_controller.mount_downloaded_model_to_ollama("aether:v3")
                    if mount_res.get("success"):
                        logger.info("✨ [Evolution Daemon] 'aether:v3' successfully fine-tuned on Kaggle GPU and mounted into local Ollama!")
                        memory.add_episode(
                            role="system",
                            content="Autonomous Kaggle GPU fine-tuning completed. 'aether:v3' weights successfully compiled and mounted to local Ollama runtime.",
                        )
            elif status == "running":
                logger.info(f"⚡ [Evolution Daemon] Kaggle GPU Training is actively running ({self.active_kernel_slug}).")
            elif status == "error":
                logger.warning(f"⚠️ [Evolution Daemon] Kaggle GPU Training reported an error: {status_info.get('failure_message')}")
        except Exception as e:
            logger.debug(f"Kaggle monitor check suppressed: {e}")

    def _execute_cycle(self) -> None:
        """Run a single autonomous mentorship, self-play pulse, and memory compaction cycle."""
        try:
            # 1. Run Teacher-Student cycle
            stage_info = teacher_student_engine.get_current_stage_info()
            verdict = teacher_student_engine.run_autonomous_mentorship_cycle()
            score = verdict.get("verdict", {}).get("score", 80) if isinstance(verdict, dict) else getattr(verdict, "score", 80)

            # 2. Run All-Rounder Perpetual Evolution Pulse (Self-play RLAIF + Skill Genesis)
            pulse_info = perpetual_dispatcher.execute_evolution_pulse()

            # 3. Compact and optimize episodic memory
            memory.compact_episodes(keep_recent=8, watermark_tokens=4000)

            self.total_autonomous_cycles += 1
            self.last_run_timestamp = datetime.now(timezone.utc).isoformat()
            logger.info(f"🧬 [Evolution Daemon] Cycle {self.total_autonomous_cycles} finished: Score {score}/100. Domain: {pulse_info.get('domain_processed')}")

        except Exception as e:
            logger.warning(f"🧬 [Evolution Daemon] Cycle execution warning: {e}")


    def get_status(self) -> dict:
        """Return live daemon status."""
        return {
            "running": self._running,
            "interval_secs": self.interval_secs,
            "total_cycles": self.total_autonomous_cycles,
            "last_run_at": self.last_run_timestamp,
            "kaggle_kernel": self.active_kernel_slug,
            "kaggle_status": self.last_kaggle_status,
        }


continuous_evolution_worker = ContinuousEvolutionWorker(interval_secs=180)

