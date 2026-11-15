"""
AETHER Asset Evaluator
======================
Scores every registered asset against three heuristics:
  1. Freshness   — assets older than 30 days lose 0.1 points.
  2. Git hygiene — assets without a recorded git hash lose 0.2 points.
  3. Uniqueness  — duplicate identifiers in the registry lose 0.3 points each.

The resulting scores (0.0–1.0) are consumed by the retrainer to decide
whether a self-improvement cycle should be triggered.
"""

from __future__ import annotations

import logging
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Tuple

logger = logging.getLogger("aether.evaluator")

# Score thresholds
RETRAIN_THRESHOLD = 0.85      # below this → trigger retrain
AGE_PENALTY = 0.10            # per asset older than 30 days
MISSING_HASH_PENALTY = 0.20   # no git hash recorded
DUPLICATE_PENALTY = 0.30      # duplicate identifier in registry


def evaluate_assets(records: List[Dict[str, Any]]) -> List[float]:
    """
    Score each asset record on a 0.0–1.0 scale.

    Returns a list of float scores in the same order as ``records``.
    An empty list is returned if ``records`` is empty.
    """
    if not records:
        logger.info("Asset evaluator: no records to evaluate.")
        return []

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=30)
    dup_counter = Counter(r.get("identifier", "") for r in records)
    scores: List[float] = []

    for rec in records:
        score = 1.0

        # 1. Freshness
        try:
            ts_str = rec.get("timestamp", "")
            if ts_str:
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                if ts < cutoff:
                    score -= AGE_PENALTY
        except Exception:
            score -= AGE_PENALTY / 2

        # 2. Git hygiene
        if not rec.get("git_hash"):
            score -= MISSING_HASH_PENALTY

        # 3. Uniqueness — penalise duplicates
        ident = rec.get("identifier", "")
        if dup_counter[ident] > 1:
            score -= DUPLICATE_PENALTY

        scores.append(max(0.0, min(1.0, score)))

    avg = sum(scores) / len(scores)
    logger.info(
        "Asset evaluation: %d records — avg score=%.3f (threshold=%.2f) — %s",
        len(records),
        avg,
        RETRAIN_THRESHOLD,
        "✅ healthy" if avg >= RETRAIN_THRESHOLD else "⚠️ retrain needed",
    )
    return scores


def compute_portfolio_health(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Compute per-type health buckets alongside the overall average score.
    Returns a dict suitable for logging to the ops log.
    """
    scores = evaluate_assets(records)
    if not scores:
        return {"total": 0, "avg_score": 1.0, "healthy": True}

    avg = sum(scores) / len(scores)
    buckets: Dict[str, List[float]] = {}
    for rec, score in zip(records, scores):
        t = rec.get("type", "unknown")
        buckets.setdefault(t, []).append(score)

    type_avgs = {t: sum(ss) / len(ss) for t, ss in buckets.items()}
    return {
        "total": len(records),
        "avg_score": round(avg, 4),
        "healthy": avg >= RETRAIN_THRESHOLD,
        "by_type": {t: round(v, 4) for t, v in type_avgs.items()},
    }
