"""
AETHER Claude Frontier Distillation & Self-Play Harvester
==========================================================
Continuously harnesses Claude 3.7 Sonnet & Gemini 2.5 Pro mentors to:
1. Generate Stage 3 & 4 Frontier Engineering Challenges.
2. Evaluate student attempts and generate gold-standard SFT & DPO pairs.
3. Extract hard operational invariants and commit them to SQLite conscious memory.
4. Auto-update dataset buffers for subsequent free cloud GPU fine-tuning runs.
"""

import argparse
from datetime import datetime
import json
import logging
import sys
import time
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from aether.config import config
from aether.memory.store import memory
from aether.brain.teacher_student_engine import teacher_student_engine, CognitiveStage
from aether.brain.multi_provider_router import multi_provider_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("aether.distillation")

FRONTIER_DISCIPLINES = [
    {
        "domain": "distributed_systems",
        "topic": "Design a fault-tolerant Raft consensus heartbeat with dynamic split-brain reconciliation in Python.",
    },
    {
        "domain": "security_architecture",
        "topic": "Perform STRIDE threat modeling on a WebSocket streaming server, identifying race conditions and session hijacking mitigations.",
    },
    {
        "domain": "high_concurrency",
        "topic": "Engineer a lock-free ring buffer with asyncio zero-copy memoryview slices for audio streaming.",
    },
    {
        "domain": "ui_technologies",
        "topic": "Formulate a WCAG AAA compliant glassmorphic design token system with spring-physics microinteractions.",
    },
    {
        "domain": "hardware_acceleration",
        "topic": "Profile Qualcomm Snapdragon X Oryon CPU thread affinity and DirectML NPU memory paging for quantized LLM inference.",
    },
    {
        "domain": "cognitive_invariants",
        "topic": "Derive formal invariants for LLM tool call parsing to guarantee zero JSON leakage and resilient error recovery.",
    },
]


def run_distillation_cycle(iterations: int = 1, stage_name: str = "scholar") -> None:
    """Execute continuous Claude frontier distillation cycles."""
    print("=" * 70)
    print(f"🚀 Launching Claude Frontier Distillation Pipeline ({iterations} Cycles)")
    print(f"🎯 Target Stage: {stage_name.upper()}")
    print("=" * 70)

    # Determine stage enum
    stage = CognitiveStage.STAGE_3_SCHOLAR
    if "child" in stage_name.lower() or "1" in stage_name:
        stage = CognitiveStage.STAGE_1_CHILD
    elif "adolescent" in stage_name.lower() or "2" in stage_name:
        stage = CognitiveStage.STAGE_2_ADOLESCENT
    elif "sovereign" in stage_name.lower() or "4" in stage_name:
        stage = CognitiveStage.STAGE_4_SOVEREIGN

    status = multi_provider_router.get_active_providers_status()
    print(f"📡 Provider Matrix:")
    for p, info in status.items():
        print(f"  - {p.upper()}: configured={info.get('configured')}, speed={info.get('speed')}")

    successful_runs = 0

    for i in range(1, iterations + 1):
        disc = FRONTIER_DISCIPLINES[(i - 1) % len(FRONTIER_DISCIPLINES)]
        print(f"\n--- [Cycle {i}/{iterations}] Discipline: {disc['domain'].upper()} ---")
        print(f"📝 Topic: {disc['topic']}")

        t0 = time.time()
        try:
            verdict = teacher_student_engine.run_autonomous_mentorship_cycle(
                stage=stage,
                topic_override=disc["topic"]
            )
            elapsed = time.time() - t0
            score = verdict.score
            status_str = "✓ PASSED" if verdict.passed else "⚠ REFINED (DPO Added)"

            print(f"📊 Mentor Score: {score}/100 [{status_str}] in {elapsed:.1f}s")
            print(f"💬 Mentor Critique: {verdict.critique[:180]}...")
            if verdict.cognitive_invariant:
                print(f"🧬 Derived Invariant: {verdict.cognitive_invariant}")

            successful_runs += 1
        except Exception as e:
            logger.error(f"Cycle {i} failed: {e}")

    # Display updated buffer status
    train_status = teacher_student_engine.get_current_stage_info()
    sft_count = 0
    dpo_count = 0
    if teacher_student_engine.sft_dataset_file.exists():
        sft_count = sum(1 for line in teacher_student_engine.sft_dataset_file.read_text(encoding="utf-8").splitlines() if line.strip())
    if teacher_student_engine.dpo_dataset_file.exists():
        dpo_count = sum(1 for line in teacher_student_engine.dpo_dataset_file.read_text(encoding="utf-8").splitlines() if line.strip())

    print("\n" + "=" * 70)
    print(f"🏁 Distillation Complete: {successful_runs}/{iterations} cycles succeeded")
    print(f"📦 Total SFT Samples Buffered: {sft_count}")
    print(f"⚖️ Total DPO Preference Pairs: {dpo_count}")
    print(f"🎓 Current Developmental Stage: {train_status.get('current_stage')}")
    print(f"📈 Stage Progress: {train_status.get('stage_progress')}% (Avg Score: {train_status.get('average_score')}/100)")
    print("=" * 70)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Claude Frontier Distillation Harvester")
    parser.add_argument("--iterations", type=int, default=1, help="Number of mentorship cycles to run")
    parser.add_argument("--stage", type=str, default="scholar", help="Target stage (child, adolescent, scholar, sovereign)")
    args = parser.parse_args()

    run_distillation_cycle(iterations=args.iterations, stage_name=args.stage)
