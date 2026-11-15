"""
AETHER Autonomous Continuous Self-Play & Trajectory Harvester
============================================================
Runs continuous autonomous self-play tournaments and teacher-student mentorship cycles.
Generates multi-discipline developmental trajectories, pairs them with frontier critiques
(Claude 3.7 / Gemini 2.5 Pro / DeepSeek-R1), and saves high-quality SFT and DPO training pairs
into `data/memory/training/` to prepare for cloud GPU fine-tuning.

Usage:
  python scripts/continuous_self_play.py --cycles 10
  python scripts/continuous_self_play.py --daemon
"""

import argparse
import logging
import sys
import time
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir / "src"))

from aether.brain.teacher_student_engine import (
    CognitiveStage,
    teacher_student_engine,
)
from aether.brain.curriculum_learner import (
    FRONTIER_DISCIPLINES,
    CurriculumLearner,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("aether.self_play")


def run_continuous_self_play(max_cycles: int = 5, daemon: bool = False, delay_seconds: int = 15):
    logger.info("=" * 70)
    logger.info("🧠 AETHER Continuous Neuro-Evolution & Self-Play Harvester Initiated")
    logger.info(f"Target: {'Infinite Daemon' if daemon else f'{max_cycles} Cycles'}")
    logger.info("=" * 70)

    learner = CurriculumLearner()
    completed = 0

    while daemon or completed < max_cycles:
        completed += 1
        logger.info(f"\n[Cycle {completed}] Starting Autonomous Mentorship & Tournament...")

        # 1. Execute Teacher-Student Mentorship Cycle
        try:
            m_res = teacher_student_engine.run_autonomous_mentorship_cycle()
            logger.info(f"✓ Mentorship Challenge: {m_res.get('challenge')}")
            logger.info(f"  Stage: {m_res.get('stage')}")
            logger.info(f"  Verdict: Score {m_res.get('verdict', {}).get('score')}/100 (Passed: {m_res.get('verdict', {}).get('passed')})")
            if m_res.get("verdict", {}).get("invariant"):
                logger.info(f"  ✨ Derived Invariant: {m_res['verdict']['invariant']}")
        except Exception as e:
            logger.error(f"Error in mentorship cycle: {e}")

        # 2. Execute Discipline Self-Play Tournament
        try:
            disc_keys = list(FRONTIER_DISCIPLINES.keys())
            chosen_disc = disc_keys[completed % len(disc_keys)]
            t_res = learner.run_adversarial_tournament(discipline=chosen_disc)
            logger.info(f"✓ Self-Play Tournament on: {chosen_disc}")
            logger.info(f"  Duration: {t_res.duration_secs:.2f}s | Sample Added: {t_res.dataset_sample_added}")
        except Exception as e:
            logger.error(f"Error in tournament cycle: {e}")


        # 3. Report Current Stage & Buffer Status
        state = teacher_student_engine.get_current_stage_info()
        sft_file = teacher_student_engine.sft_dataset_file
        dpo_file = teacher_student_engine.dpo_dataset_file
        sft_count = sum(1 for line in sft_file.read_text(encoding="utf-8").splitlines() if line.strip()) if sft_file.exists() else 0
        dpo_count = sum(1 for line in dpo_file.read_text(encoding="utf-8").splitlines() if line.strip()) if dpo_file.exists() else 0

        logger.info(f"📊 Progress: {state.get('current_stage')} ({state.get('stage_progress')}%) | Buffer: {sft_count} SFT, {dpo_count} DPO")

        if daemon or completed < max_cycles:
            logger.info(f"Sleeping {delay_seconds}s before next cycle...")
            time.sleep(delay_seconds)

    logger.info("\n🎉 Self-Play session finished successfully!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AETHER Continuous Self-Play & Trajectory Harvester")
    parser.add_argument("--cycles", type=int, default=3, help="Number of cycles to execute (default: 3)")
    parser.add_argument("--daemon", action="store_true", help="Run indefinitely in background")
    parser.add_argument("--delay", type=int, default=10, help="Delay between cycles in seconds (default: 10)")
    args = parser.parse_args()

    run_continuous_self_play(max_cycles=args.cycles, daemon=args.daemon, delay_seconds=args.delay)
