"""
AETHER Asset Registry
=====================
Thread-safe JSONL log of every artifact created by AETHER + LEON:
  - Vercel deployments
  - Generated tool scripts
  - Model snapshots
  - Config patches

Each record carries:
  id, type, identifier, path, source, job_id, git_hash, timestamp, extra

The registry is intentionally append-only; expired entries are never
deleted in-place — the `prune()` method writes a compacted copy.
"""

from __future__ import annotations

import json
import logging
import pathlib
import subprocess
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger("aether.asset_registry")

_WORKSPACE = pathlib.Path(__file__).resolve().parents[3]
_DEFAULT_PATH = _WORKSPACE / "data" / "leon_intelligence" / "asset_registry.jsonl"
_LOCK = threading.Lock()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat() + "Z"


def _git_hash() -> Optional[str]:
    """Return the current HEAD short git hash, or None if not in a git repo."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(_WORKSPACE),
            capture_output=True,
            text=True,
            timeout=3,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


class AssetRegistry:
    """Thread-safe JSONL registry for every asset the system creates."""

    def __init__(self, path: pathlib.Path = _DEFAULT_PATH) -> None:
        self.path = pathlib.Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    # ── Write ────────────────────────────────────────────────────────────────

    def register(
        self,
        asset_type: str,
        identifier: str,
        path: str,
        source: str,
        job_id: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Append a single JSONL record and return the generated asset ID.

        Args:
            asset_type:  Category — 'deployment', 'tool', 'model', 'config'.
            identifier:  Human-readable name (e.g. venture slug or script name).
            path:        Absolute path or URL of the created artifact.
            source:      Module/job that created this asset (e.g. 'leon_deployer').
            job_id:      APScheduler job ID, if created by a scheduled job.
            extra:       Arbitrary key-value metadata.
        """
        entry: Dict[str, Any] = {
            "id": str(uuid.uuid4()),
            "type": asset_type,
            "identifier": identifier,
            "path": path,
            "source": source,
            "job_id": job_id,
            "git_hash": _git_hash(),
            "timestamp": _now_iso(),
            "extra": extra or {},
        }
        line = json.dumps(entry, ensure_ascii=False)
        with _LOCK:
            with self.path.open("a", encoding="utf-8") as f:
                f.write(line + "\n")
        logger.debug("Registered asset %s [%s]: %s", asset_type, identifier, path)
        return entry["id"]

    # ── Read ─────────────────────────────────────────────────────────────────

    def read_all(self) -> List[Dict[str, Any]]:
        """Return all records as a list of dicts."""
        if not self.path.exists():
            return []
        with _LOCK:
            lines = self.path.read_text(encoding="utf-8").splitlines()
        records = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                logger.warning("Skipping malformed registry line: %s", line[:80])
        return records

    def read_by_type(self, asset_type: str) -> List[Dict[str, Any]]:
        """Filter records by asset type."""
        return [r for r in self.read_all() if r.get("type") == asset_type]

    def read_by_identifier(self, identifier: str) -> List[Dict[str, Any]]:
        """Filter records by identifier (may return multiple versions)."""
        return [r for r in self.read_all() if r.get("identifier") == identifier]

    # ── Maintenance ──────────────────────────────────────────────────────────

    def prune(self, keep: int = 2000) -> int:
        """
        Compact the registry to the most recent `keep` entries.
        Returns the number of entries removed.
        """
        records = self.read_all()
        if len(records) <= keep:
            return 0
        to_keep = records[-keep:]
        removed = len(records) - len(to_keep)
        with _LOCK:
            with self.path.open("w", encoding="utf-8") as f:
                for r in to_keep:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
        logger.info("Asset registry pruned: removed %d old entries.", removed)
        return removed

    def summary(self) -> Dict[str, Any]:
        """Return a quick summary grouped by asset type."""
        records = self.read_all()
        by_type: Dict[str, int] = {}
        for r in records:
            t = r.get("type", "unknown")
            by_type[t] = by_type.get(t, 0) + 1
        return {"total": len(records), "by_type": by_type}


# Singleton convenience instance
asset_registry = AssetRegistry()
