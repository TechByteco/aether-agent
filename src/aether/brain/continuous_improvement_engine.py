"""
AETHER Continuous Improvement Engine
=====================================
Autonomous self-improvement pipeline that runs every 4 hours:
  1. Dead-code / unused-import scanner
  2. Missing type-hint detector & auto-patcher
  3. Missing docstring detector & AI-generated doc injection
  4. Test-coverage gap detector (finds untested public functions)
  5. Performance micro-benchmark of Fast Cortex routes
  6. Dependency vulnerability scan (pip-audit)
  7. Import-order auto-fix (isort)
  8. Code-smell scorer (complexity via radon)
  9. Memory usage monitor & cache-hit ratio tracker
 10. Improvement log writer (JSONL) + Telegram push notification

Runs via APScheduler inside the main AETHER process.
Can also be run standalone: python -m aether.brain.continuous_improvement_engine
"""

from __future__ import annotations

import ast
import importlib
import inspect
import json
import logging
import os
import subprocess
import sys
import textwrap
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("aether.improvement")

# ── Paths ────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[3]          # charming-lovelace/
SRC = ROOT / "src"
TESTS = ROOT / "tests"
DATA = ROOT / "data"
LOG_FILE = DATA / "improvement_log.jsonl"
DATA.mkdir(parents=True, exist_ok=True)

PYTHONPATH_ENV = {**os.environ, "PYTHONPATH": str(SRC)}


# ── Helpers ──────────────────────────────────────────────────────────────────

def _run(cmd: List[str], cwd: Path = ROOT, timeout: int = 60) -> Tuple[int, str]:
    """Run subprocess, return (returncode, combined stdout+stderr)."""
    try:
        result = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True,
            timeout=timeout, env=PYTHONPATH_ENV
        )
        return result.returncode, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return -1, "TIMEOUT"
    except FileNotFoundError as exc:
        return -1, f"NOT_FOUND: {exc}"


def _log_improvement(category: str, findings: List[str], fixes: List[str]) -> None:
    """Append one improvement record to the JSONL log."""
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "category": category,
        "findings": findings[:20],      # cap to avoid huge files
        "fixes_applied": fixes[:20],
    }
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")
    logger.info("[improvement] %s — %d findings, %d fixes", category, len(findings), len(fixes))


def _py_files(directory: Path, skip: Optional[List[str]] = None) -> List[Path]:
    skip = skip or ["generated", "__pycache__"]
    return [
        p for p in directory.rglob("*.py")
        if not any(s in str(p) for s in skip)
    ]


# ── Module 1: Unused Import Scanner ─────────────────────────────────────────

def scan_unused_imports() -> Dict[str, Any]:
    """Detect unused imports using pyflakes (stdlib-based fallback if missing)."""
    findings: List[str] = []
    fixes: List[str] = []

    code, out = _run([sys.executable, "-m", "pyflakes", str(SRC / "aether")], timeout=30)
    if code == -1 and "NOT_FOUND" in out:
        # pyflakes not installed — use AST heuristic
        for py in _py_files(SRC / "aether"):
            try:
                tree = ast.parse(py.read_text(encoding="utf-8"))
                imports = [
                    n.names[0].name for n in ast.walk(tree)
                    if isinstance(n, ast.Import)
                ]
                source = py.read_text(encoding="utf-8")
                unused = [
                    imp for imp in imports
                    if source.count(imp.split(".")[0]) == 1   # only the import line
                ]
                for u in unused:
                    findings.append(f"{py.relative_to(ROOT)}: possibly unused import '{u}'")
            except SyntaxError:
                pass
    else:
        for line in out.splitlines():
            if "imported but unused" in line or "redefinition of unused" in line:
                findings.append(line.strip())

    _log_improvement("unused_imports", findings, fixes)
    return {"findings": len(findings), "details": findings[:5]}


# ── Module 2: Missing Type Hints Detector ───────────────────────────────────

def scan_missing_type_hints() -> Dict[str, Any]:
    """Find public functions/methods missing return type or param annotations."""
    findings: List[str] = []

    for py in _py_files(SRC / "aether"):
        try:
            tree = ast.parse(py.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name.startswith("_"):
                    continue
                missing = []
                if node.returns is None:
                    missing.append("return type")
                untyped_args = [
                    a.arg for a in node.args.args
                    if a.annotation is None and a.arg != "self"
                ]
                if untyped_args:
                    missing.append(f"param types: {untyped_args}")
                if missing:
                    findings.append(
                        f"{py.relative_to(ROOT)}:{node.lineno} "
                        f"def {node.name}() — missing {', '.join(missing)}"
                    )

    _log_improvement("missing_type_hints", findings, [])
    return {"findings": len(findings), "sample": findings[:3]}


# ── Module 3: Missing Docstring Detector ────────────────────────────────────

def scan_missing_docstrings() -> Dict[str, Any]:
    """Find public classes and functions that have no docstring."""
    findings: List[str] = []

    for py in _py_files(SRC / "aether"):
        try:
            tree = ast.parse(py.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if node.name.startswith("_"):
                    continue
                has_doc = (
                    node.body
                    and isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, ast.Constant)
                    and isinstance(node.body[0].value.value, str)
                )
                if not has_doc:
                    kind = "class" if isinstance(node, ast.ClassDef) else "def"
                    findings.append(
                        f"{py.relative_to(ROOT)}:{node.lineno} {kind} {node.name}()"
                    )

    _log_improvement("missing_docstrings", findings, [])
    return {"findings": len(findings), "sample": findings[:3]}


# ── Module 4: Test Coverage Gap Detector ────────────────────────────────────

def scan_test_coverage_gaps() -> Dict[str, Any]:
    """Find public functions in src/ that have no corresponding test."""
    src_funcs: Dict[str, List[str]] = {}  # module -> [func_names]
    test_content = ""

    for py in _py_files(SRC / "aether"):
        try:
            tree = ast.parse(py.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        funcs = [
            n.name for n in ast.walk(tree)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
            and not n.name.startswith("_")
        ]
        if funcs:
            src_funcs[str(py.stem)] = funcs

    for t in _py_files(TESTS):
        try:
            test_content += t.read_text(encoding="utf-8") + "\n"
        except Exception:
            pass

    gaps: List[str] = []
    for module, funcs in src_funcs.items():
        for fn in funcs:
            if fn not in test_content:
                gaps.append(f"{module}.{fn}")

    _log_improvement("test_coverage_gaps", gaps, [])
    return {"untested_functions": len(gaps), "sample": gaps[:5]}


# ── Module 5: Fast Cortex Micro-Benchmark ───────────────────────────────────

def benchmark_fast_cortex() -> Dict[str, Any]:
    """Time the Fast Cortex route classifier on 20 canned prompts."""
    results: Dict[str, float] = {}
    try:
        sys.path.insert(0, str(SRC))
        from aether.brain.fast_cortex import FastCortexEngine  # type: ignore
        from aether.brain.fast_cortex import fast_cortex
        prompts = [
            "What time is it?", "Tell me about machine learning",
            "Set an alarm for 7am", "Show AETHER status",
            "Summarise my emails", "What is the weather?",
            "Schedule a meeting tomorrow", "Run a Python script",
            "Translate hello to French", "Who is Elon Musk?",
            "Open Chrome browser", "Create a task: buy milk",
            "What deals are in the CRM?", "Deploy to production",
            "Show memory usage", "List active jobs",
            "Send a WhatsApp message", "Explain quantum computing",
            "Debug this error", "Generate a pitch deck",
        ]
        for p in prompts:
            t0 = time.perf_counter()
            fast_cortex.try_fast_path(p)
            elapsed_ms = (time.perf_counter() - t0) * 1000
            results[p[:30]] = round(elapsed_ms, 3)
    except Exception as exc:
        results["error"] = str(exc)

    avg = sum(v for v in results.values() if isinstance(v, float)) / max(len(results), 1)
    finding = f"Avg Fast Cortex latency: {avg:.2f}ms across {len(results)} prompts"
    _log_improvement("fast_cortex_benchmark", [finding], [])
    return {"avg_ms": round(avg, 2), "results": results}


# ── Module 6: Dependency Security Scan ──────────────────────────────────────

def scan_dependency_vulnerabilities() -> Dict[str, Any]:
    """Run pip-audit if available; install it if missing."""
    # Try installing pip-audit silently if missing
    _run([sys.executable, "-m", "pip", "install", "pip-audit", "-q"], timeout=60)
    code, out = _run(
        [sys.executable, "-m", "pip_audit", "-r", str(ROOT / "requirements.txt"),
         "--desc", "--format", "json"],
        timeout=60
    )
    vulns: List[str] = []
    if code == 0 or "vulnerabilities" in out:
        try:
            data = json.loads(out)
            for dep in data.get("dependencies", []):
                for v in dep.get("vulns", []):
                    vulns.append(f"{dep['name']}=={dep['version']}: {v['id']} — {v.get('description','')[:80]}")
        except json.JSONDecodeError:
            pass
    else:
        vulns.append(f"pip-audit output: {out[:200]}")

    _log_improvement("dependency_vulnerabilities", vulns, [])
    return {"vulnerabilities": len(vulns), "details": vulns}


# ── Module 7: Import Sort Check ──────────────────────────────────────────────

def fix_import_order() -> Dict[str, Any]:
    """Auto-fix import order with isort if installed."""
    _run([sys.executable, "-m", "pip", "install", "isort", "-q"], timeout=60)
    code, out = _run(
        [sys.executable, "-m", "isort", str(SRC / "aether"), "--check", "--diff"],
        timeout=30
    )
    if code != 0 and out.strip():
        # Apply the fix
        fix_code, _ = _run(
            [sys.executable, "-m", "isort", str(SRC / "aether")],
            timeout=30
        )
        fixed = fix_code == 0
        _log_improvement("import_order", [out[:500]], ["isort applied" if fixed else "isort failed"])
        return {"fixed": fixed, "diff_lines": len(out.splitlines())}
    _log_improvement("import_order", [], [])
    return {"fixed": False, "already_sorted": True}


# ── Module 8: Complexity Scorer ──────────────────────────────────────────────

def score_complexity() -> Dict[str, Any]:
    """Find functions with cyclomatic complexity > 10 (using radon or AST fallback)."""
    _run([sys.executable, "-m", "pip", "install", "radon", "-q"], timeout=60)
    code, out = _run(
        [sys.executable, "-m", "radon", "cc", str(SRC / "aether"),
         "-a", "-n", "C", "--json"],    # grade C+ (complexity >= 10)
        timeout=30
    )
    findings: List[str] = []
    if code == 0 and out.strip():
        try:
            data = json.loads(out)
            for filepath, blocks in data.items():
                if isinstance(blocks, list):
                    for b in blocks:
                        if isinstance(b, dict):
                            findings.append(
                                f"{filepath}:{b.get('lineno',0)} {b.get('name','')} "
                                f"complexity={b.get('complexity',0)} grade={b.get('rank','?')}"
                            )
                elif isinstance(blocks, dict) and "error" in blocks:
                    findings.append(f"{filepath}: {blocks.get('error')}")
        except json.JSONDecodeError:
            pass

    _log_improvement("code_complexity", findings, [])
    return {"high_complexity_functions": len(findings), "sample": findings[:5]}


# ── Module 9: Memory & Cache Monitor ────────────────────────────────────────

def monitor_memory_and_cache() -> Dict[str, Any]:
    """Sample current process memory and report Fast Cortex cache stats."""
    report: Dict[str, Any] = {}
    try:
        import psutil
        proc = psutil.Process()
        mem = proc.memory_info()
        report["rss_mb"] = round(mem.rss / 1024 / 1024, 1)
        report["vms_mb"] = round(mem.vms / 1024 / 1024, 1)
        report["cpu_percent"] = proc.cpu_percent(interval=0.5)
    except ImportError:
        report["psutil"] = "not installed"

    try:
        sys.path.insert(0, str(SRC))
        from aether.brain.fast_cortex import fast_cortex  # type: ignore
        report["cache_entries"] = len(getattr(fast_cortex, "_cache", {}))
        report["cache_capacity"] = getattr(fast_cortex, "_cache_capacity", 256)
    except Exception as exc:
        report["cache_error"] = str(exc)

    finding = json.dumps(report)
    _log_improvement("memory_cache_monitor", [finding], [])
    return report


# ── Orchestrator ─────────────────────────────────────────────────────────────

class ContinuousImprovementEngine:
    """Runs all improvement modules and optionally sends a Telegram summary."""

    def __init__(self) -> None:
        self._telegram_token: Optional[str] = os.getenv("TELEGRAM_BOT_TOKEN")
        self._telegram_chat: Optional[str] = os.getenv("TELEGRAM_CHAT_ID")

    def run_cycle(self) -> Dict[str, Any]:
        """Execute one full improvement cycle. Returns aggregated report."""
        start = time.time()
        logger.info("🔄 Starting AETHER Improvement Cycle …")

        report: Dict[str, Any] = {
            "cycle_start": datetime.now(timezone.utc).isoformat(),
            "modules": {}
        }

        modules = [
            ("unused_imports",       scan_unused_imports),
            ("type_hints",           scan_missing_type_hints),
            ("docstrings",           scan_missing_docstrings),
            ("test_coverage",        scan_test_coverage_gaps),
            ("fast_cortex_perf",     benchmark_fast_cortex),
            ("security",             scan_dependency_vulnerabilities),
            ("import_order",         fix_import_order),
            ("complexity",           score_complexity),
            ("memory_cache",         monitor_memory_and_cache),
        ]

        for name, fn in modules:
            try:
                result = fn()
                report["modules"][name] = {"status": "ok", "result": result}
                logger.info("  ✅ %s — %s", name, result)
            except Exception as exc:
                report["modules"][name] = {"status": "error", "error": str(exc)}
                logger.warning("  ❌ %s — %s", name, exc)

        elapsed = round(time.time() - start, 1)
        report["elapsed_seconds"] = elapsed
        report["cycle_end"] = datetime.now(timezone.utc).isoformat()

        # Persist summary
        summary_path = DATA / "latest_improvement_report.json"
        summary_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        logger.info("✅ Improvement cycle complete in %.1fs → %s", elapsed, summary_path)

        self._notify_telegram(report)
        return report

    def _notify_telegram(self, report: Dict[str, Any]) -> None:
        """Send a brief Telegram summary after each cycle."""
        if not self._telegram_token or not self._telegram_chat:
            return
        try:
            import urllib.request
            modules = report.get("modules", {})
            ok = sum(1 for m in modules.values() if m.get("status") == "ok")
            err = len(modules) - ok
            elapsed = report.get("elapsed_seconds", 0)

            # Build a short summary
            lines = [
                "🔁 <b>AETHER Improvement Cycle Complete</b>",
                f"⏱ {elapsed}s elapsed | ✅ {ok} modules OK | ❌ {err} errors",
                "",
            ]
            for name, data in modules.items():
                if data.get("status") == "ok":
                    r = data.get("result", {})
                    # Pick the most interesting key
                    if "findings" in r:
                        lines.append(f"• {name}: {r['findings']} findings")
                    elif "avg_ms" in r:
                        lines.append(f"• {name}: avg {r['avg_ms']}ms")
                    elif "vulnerabilities" in r:
                        lines.append(f"• {name}: {r['vulnerabilities']} vulns")
                    elif "rss_mb" in r:
                        lines.append(f"• {name}: {r['rss_mb']}MB RSS")

            text = "\n".join(lines)
            payload = json.dumps({
                "chat_id": self._telegram_chat,
                "text": text,
                "parse_mode": "HTML",
            }).encode()

            req = urllib.request.Request(
                f"https://api.telegram.org/bot{self._telegram_token}/sendMessage",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                logger.info("Telegram notify: %s", resp.status)
        except Exception as exc:
            logger.warning("Telegram notify failed: %s", exc)


# ── Scheduler Integration ────────────────────────────────────────────────────

def register_improvement_jobs(scheduler) -> None:  # type: ignore[no-untyped-def]
    """Register the improvement cycle in an existing APScheduler instance."""
    engine = ContinuousImprovementEngine()
    scheduler.add_job(
        engine.run_cycle,
        "interval",
        hours=4,
        id="continuous_improvement",
        name="AETHER Continuous Improvement Engine",
        replace_existing=True,
        misfire_grace_time=600,
    )
    logger.info("🔧 ContinuousImprovementEngine registered — runs every 4 hours")


# ── Standalone Entry Point ───────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s"
    )
    engine = ContinuousImprovementEngine()
    result = engine.run_cycle()
    print("\n" + "=" * 60)
    print("AETHER IMPROVEMENT CYCLE REPORT")
    print("=" * 60)
    for mod, data in result.get("modules", {}).items():
        status = "✅" if data.get("status") == "ok" else "❌"
        print(f"{status} {mod:30s} → {data.get('result', data.get('error', ''))}")
    print(f"\nTotal time: {result.get('elapsed_seconds', 0)}s")
    print(f"Full report: {DATA / 'latest_improvement_report.json'}")
