"""
AETHER Autonomous Heartbeat Daemon ("The Will")
Proactive background engine that awakens periodically to monitor hardware vitals,
deliver circadian morning briefings, track active goals, and safeguard system health.
Operates with near-zero RAM footprint (<15 MB).
"""

import gc
import logging
import threading
import time
from datetime import date, datetime
from pathlib import Path
from typing import Callable, Optional

import psutil

from aether.config import config
from aether.memory.persona import persona
from aether.memory.store import memory
from aether.tools.guardrails import get_system_vitals
from aether.tools.voice import voice

logger = logging.getLogger("aether.heartbeat")


class AutonomousHeartbeat:
    def __init__(self, interval_seconds: int = 900):  # Default: Every 15 minutes
        self.interval_seconds = interval_seconds
        self.running = False
        self._thread: Optional[threading.Thread] = None
        self._last_briefing_date: Optional[date] = None
        self._last_battery_alert_level: Optional[int] = None
        self.on_notification: Optional[Callable[[str], None]] = None

    def start(self) -> None:
        """Launch the autonomous heartbeat loop in a background daemon thread."""
        if self.running:
            return
        self.running = True
        self._thread = threading.Thread(target=self._run_loop, name="AETHER-Heartbeat", daemon=True)
        self._thread.start()
        logger.info("Autonomous Heartbeat daemon initiated.")

    def stop(self) -> None:
        """Gracefully signal the heartbeat loop to stop."""
        self.running = False

    def _notify(self, message: str, speak: bool = True) -> None:
        """Dispatch notification to HUD, log, and optionally speak via voice."""
        timestamp = datetime.now().strftime("%I:%M %p")
        formatted = f"[Heartbeat Pulse {timestamp}] {message}"
        if self.on_notification:
            try:
                self.on_notification(formatted)
            except Exception:
                pass
        if speak and voice.enabled:
            voice.speak_async(message)

    def pulse_check(self) -> str:
        """
        Execute one synchronous heartbeat pulse check.
        Returns a human-readable status summary.
        """
        now = datetime.now()
        vitals = get_system_vitals()
        events = []

        # 1. Hardware Power & Battery Guardianship
        battery = psutil.sensors_battery()
        if battery:
            pct = round(battery.percent)
            plugged = battery.power_plugged
            if not plugged and pct <= 20:
                if self._last_battery_alert_level != pct:
                    self._last_battery_alert_level = pct
                    msg = f"Battery is at {pct}%. Please plug in the charger to sustain full performance."
                    self._notify(msg, speak=True)
                    events.append(f"Battery alert triggered ({pct}%).")
            elif plugged:
                self._last_battery_alert_level = None

        # 2. RAM Pressure Guard
        if vitals["ram_percent"] > 85:
            gc.collect()
            events.append(f"RAM pressure high ({vitals['ram_percent']}%). Executed garbage collection.")

        # 3. Circadian Morning Briefing (Once daily between 7 AM and 11 AM)
        if 7 <= now.hour <= 11 and self._last_briefing_date != now.date():
            self._last_briefing_date = now.date()
            goals_text = persona.get_active_goals()
            goals_count = len([line for line in goals_text.splitlines() if line.strip() and line.strip()[0].isdigit()])
            time_str = now.strftime("%I:%M %p")
            
            briefing = (
                f"Good morning! It is {time_str}. System vitals are optimal at {vitals['ram_percent']}% RAM. "
                f"You have {goals_count} active objectives in memory. Ready whenever you are."
            )
            self._notify(briefing, speak=True)
            events.append("Delivered daily morning briefing.")

        # 4. Periodic Memory Flush
        try:
            memory.add_episode(
                role="system",
                content=f"Heartbeat pulse check: RAM {vitals['ram_percent']}%, Battery {vitals.get('battery_percent', 'N/A')}%",
                session_id="heartbeat"
            )
        except Exception:
            pass

        # 5. Autonomous Evolutionary Pulse (Self-directed learning cycle)
        self._pulse_count = getattr(self, "_pulse_count", 0) + 1
        if self._pulse_count % 4 == 0:
            try:
                from aether.brain.evolution import evolution_engine
                evo_res = evolution_engine.run_evolution_cycle()
                events.append(f"Autonomous Evolution: Gen {evo_res['generation']} → {evo_res['next_generation']} ({evo_res['topic'][:35]}...)")
            except Exception as e:
                logger.debug(f"Heartbeat evolution cycle skipped: {e}")

        # 6. Autonomous Memory Compaction & Learning Health Audit
        if self._pulse_count % 8 == 0:
            try:
                memory.compact_episodes(keep_recent=6, watermark_tokens=3000)
                from aether.brain.auto_learner import auto_learner
                stats = auto_learner.get_learning_metrics()
                events.append(f"Auto-Learning Audit: {stats['total_rules_in_memory']} rules, {stats['synthetic_dataset_samples']} dataset samples")
            except Exception as e:
                logger.debug(f"Auto-learning audit skipped: {e}")

        # 7. Autonomous Teacher-Student Mentorship Pulse
        if self._pulse_count % 6 == 0:
            try:
                from aether.brain.teacher_student_engine import \
                    teacher_student_engine
                m_res = teacher_student_engine.run_autonomous_mentorship_cycle()
                events.append(f"Teacher-Student Mentorship: {m_res['stage']} (Score: {m_res['verdict']['score']})")
            except Exception as e:
                logger.debug(f"Teacher-student mentorship pulse skipped: {e}")

        return "; ".join(events) if events else "All systems optimal. Vitals nominal."




    def _run_loop(self) -> None:
        """Continuous background loop sleeping in small slices for instant responsiveness."""
        # Initial delayed check 10 seconds after boot
        time.sleep(10)
        while self.running:
            try:
                self.pulse_check()
            except Exception as e:
                logger.error(f"Error in heartbeat cycle: {str(e)}")

            # Sleep in 1-second chunks to allow instant shutdown
            for _ in range(self.interval_seconds):
                if not self.running:
                    break
                time.sleep(1)


heartbeat = AutonomousHeartbeat()


if __name__ == "__main__":
    print("AETHER Autonomous Heartbeat Daemon active. Press Ctrl+C to stop.")
    heartbeat.on_notification = lambda msg: print(msg)
    heartbeat.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping Heartbeat...")
        heartbeat.stop()
