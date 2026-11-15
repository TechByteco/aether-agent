"""
AETHER Self-Improvement Retrainer
==================================
Called by the nightly ``job_self_evaluation`` in the AutonomousOperator.

When the mean asset score falls below RETRAIN_THRESHOLD, this module:
  1. Writes a retrain manifest to ``data/leon_intelligence/retrain_manifest.json``
     documenting *why* the retrain was triggered and which asset types failed.
  2. Launches ``scripts/train_loop.py`` as a subprocess (non-blocking by default).
  3. Logs the outcome to the ops log.

If ``scripts/train_loop.py`` does not exist, it creates a minimal placeholder
so the system never crashes — the placeholder can be replaced with a real
fine-tuning pipeline later.
"""

from __future__ import annotations

import json
import logging
import os
import pathlib
import subprocess
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger("aether.retrainer")

_WORKSPACE = pathlib.Path(__file__).resolve().parents[3]
_SCRIPTS_DIR = _WORKSPACE / "scripts"
_INTEL_DIR = _WORKSPACE / "data" / "leon_intelligence"
_TRAIN_SCRIPT = _SCRIPTS_DIR / "train_loop.py"
_MANIFEST_FILE = _INTEL_DIR / "retrain_manifest.json"

RETRAIN_THRESHOLD: float = float(os.getenv("AETHER_RETRAIN_THRESHOLD", "0.85"))
BLOCKING: bool = os.getenv("AETHER_RETRAIN_BLOCKING", "0") == "1"


def _ensure_train_script() -> None:
    """Create a minimal placeholder training script if it doesn't exist."""
    if _TRAIN_SCRIPT.exists():
        return
    _SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
    placeholder = '''\
"""
AETHER Training Loop Placeholder
=================================
Replace this file with your actual fine-tuning pipeline.
This placeholder is created automatically so the system never crashes
when the retrainer is triggered for the first time.
"""
import logging
import sys

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("aether.train_loop")

def main():
    logger.info("Training loop placeholder executed — no-op.")
    logger.info("Replace scripts/train_loop.py with your real training code.")

if __name__ == "__main__":
    main()
    sys.exit(0)
'''
    _TRAIN_SCRIPT.write_text(placeholder, encoding="utf-8")
    logger.info("Created placeholder training script at %s", _TRAIN_SCRIPT)


def maybe_trigger_retrain(
    scores: List[float],
    health_report: Optional[Dict[str, Any]] = None,
) -> bool:
    """
    Trigger a retrain cycle if the mean score is below RETRAIN_THRESHOLD.

    Args:
        scores:         List of float scores from evaluate_assets().
        health_report:  Optional dict from compute_portfolio_health().

    Returns:
        True if retrain was triggered, False otherwise.
    """
    if not scores:
        return False

    avg = sum(scores) / len(scores)
    if avg >= RETRAIN_THRESHOLD:
        logger.info(
            "Retrain not required — avg score %.3f >= threshold %.2f",
            avg, RETRAIN_THRESHOLD,
        )
        return False

    logger.warning(
        "Retrain triggered — avg score %.3f < threshold %.2f",
        avg, RETRAIN_THRESHOLD,
    )

    # Write manifest
    _INTEL_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {
        "triggered_at": datetime.now(timezone.utc).isoformat() + "Z",
        "avg_score": round(avg, 4),
        "threshold": RETRAIN_THRESHOLD,
        "num_assets": len(scores),
        "health_report": health_report or {},
        "status": "launched",
    }
    _MANIFEST_FILE.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    logger.info("Retrain manifest written to %s", _MANIFEST_FILE)

    # Ensure the script exists (creates placeholder if needed)
    _ensure_train_script()

    # Launch training script
    try:
        kwargs: Dict[str, Any] = {
            "cwd": str(_WORKSPACE),
            "env": {**os.environ, "PYTHONPATH": str(_WORKSPACE / "src")},
        }
        if BLOCKING:
            result = subprocess.run(
                ["python", str(_TRAIN_SCRIPT)],
                check=True,
                capture_output=True,
                text=True,
                **kwargs,
            )
            logger.info("Retrain completed (blocking): %s", result.stdout[-500:])
        else:
            subprocess.Popen(
                ["python", str(_TRAIN_SCRIPT)],
                **kwargs,
            )
            logger.info("Retrain launched in background (non-blocking).")
        return True
    except subprocess.CalledProcessError as exc:
        logger.error("Retrain script failed: %s", exc.stderr[-500:])
        # Update manifest with failure
        manifest["status"] = "failed"
        manifest["error"] = exc.stderr[-200:]
        _MANIFEST_FILE.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return False
    except Exception as exc:
        logger.error("Retrain launch error: %s", exc)
        return False
