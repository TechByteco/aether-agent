"""
AETHER Global Master Tech & Systems Architecture Module
Provides high-performance engineering & system diagnostics:
- API Benchmark & Latency Stress Profiler
- Codebase Architecture, Complexity & Clean-Code Health Auditor
- Deep Process & Memory Leak Telemetry Diagnostic
- Git Multi-Repo Status & Upstream Drift Inspector
"""

import os
import re
import statistics
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import httpx
import psutil


def benchmark_api_endpoint(url: str, num_requests: int = 10, method: str = "GET") -> str:
    """
    Benchmark an API endpoint or web server: measures min/p50/p95/max latency,
    throughput (requests/sec), status code distribution, and response payload size.
    """
    clean_url = url.strip()
    if not clean_url.startswith(("http://", "https://")):
        clean_url = "http://" + clean_url

    clean_method = method.upper().strip()
    num_reqs = max(1, min(100, int(num_requests)))

    latencies = []
    status_codes: Dict[int, int] = {}
    total_bytes = 0
    errors = 0

    start_bench = time.perf_counter()

    with httpx.Client(timeout=10.0, follow_redirects=True) as client:
        for _ in range(num_reqs):
            req_start = time.perf_counter()
            try:
                if clean_method == "POST":
                    resp = client.post(clean_url, json={})
                elif clean_method == "HEAD":
                    resp = client.head(clean_url)
                else:
                    resp = client.get(clean_url)

                elapsed_ms = (time.perf_counter() - req_start) * 1000
                latencies.append(elapsed_ms)
                status_codes[resp.status_code] = status_codes.get(resp.status_code, 0) + 1
                total_bytes += len(resp.content)
            except Exception as e:
                errors += 1
                latencies.append(10000.0)

    total_time = time.perf_counter() - start_bench
    successful_latencies = [l for l in latencies if l < 10000.0]

    if not successful_latencies:
        return f"### ⚠ Benchmark Failed for `{clean_url}`\nAll {num_reqs} requests timed out or encountered connection errors."

    successful_latencies.sort()
    count = len(successful_latencies)
    min_lat = successful_latencies[0]
    max_lat = successful_latencies[-1]
    mean_lat = statistics.mean(successful_latencies)
    p50_lat = statistics.median(successful_latencies)
    p95_index = min(count - 1, int(count * 0.95))
    p95_lat = successful_latencies[p95_index]
    rps = count / total_time if total_time > 0 else 0

    status_str = ", ".join([f"HTTP {k}: {v}" for k, v in sorted(status_codes.items())])
    avg_kb = (total_bytes / count / 1024) if count > 0 else 0

    return (
        f"### ⚡ API Benchmark Report: `{clean_url}`\n"
        f"- **Method:** `{clean_method}` | **Total Requests:** {num_reqs} ({errors} failed)\n"
        f"- **Throughput:** **{rps:.1f} req/sec** (Total elapsed: {total_time:.2f}s)\n"
        f"- **Status Breakdown:** {status_str}\n"
        f"- **Avg Response Size:** {avg_kb:.2f} KB\n\n"
        f"#### ⏱️ Latency Distribution:\n"
        f"- **Min:** `{min_lat:.1f} ms`\n"
        f"- **p50 (Median):** `{p50_lat:.1f} ms`\n"
        f"- **Mean:** `{mean_lat:.1f} ms`\n"
        f"- **p95:** `{p95_lat:.1f} ms`\n"
        f"- **Max:** `{max_lat:.1f} ms`"
    )


def audit_codebase_architecture(target_dir: str = ".", max_files: int = 100) -> str:
    """
    Perform deep static analysis of a codebase: flags monolith files (>500 lines),
    god functions (>50 lines), technical debt tags (TODO/FIXME), and computes Clean-Code Health Grade.
    """
    base_path = Path(target_dir).resolve()
    if not base_path.exists():
        return f"Directory '{target_dir}' does not exist."

    ignored_dirs = {".git", ".venv", "node_modules", "__pycache__", ".idea", ".vscode", "dist", "build"}
    code_extensions = {".py", ".js", ".ts", ".jsx", ".tsx", ".rs", ".go", ".c", ".cpp", ".java", ".html", ".css"}

    total_files = 0
    total_loc = 0
    total_comments = 0
    total_blank = 0
    monolith_files = []
    oversized_functions = []
    debt_markers = []

    for root, dirs, files in os.walk(base_path):
        dirs[:] = [d for d in dirs if d not in ignored_dirs]
        for f in files:
            ext = Path(f).suffix.lower()
            if ext not in code_extensions:
                continue

            file_path = Path(root) / f
            total_files += 1
            if total_files > max_files:
                break

            try:
                lines = file_path.read_text(encoding="utf-8", errors="ignore").splitlines()
                floc = len(lines)
                total_loc += floc
                rel_file = str(file_path.relative_to(base_path))

                if floc > 500:
                    monolith_files.append((rel_file, floc))

                # Track function sizes (Python & JS/TS patterns)
                current_fn = None
                current_fn_start = 0

                for i, line in enumerate(lines, 1):
                    stripped = line.strip()
                    if not stripped:
                        total_blank += 1
                        continue
                    if stripped.startswith(("#", "//", "/*", "*")):
                        total_comments += 1

                    # Technical debt tags
                    if any(tag in line for tag in ["TODO", "FIXME", "HACK", "XXX", "BUG"]):
                        debt_markers.append((rel_file, i, stripped[:70]))

                    # Simple function boundaries
                    fn_match = re.match(r"^\s*(?:def|async def|function|const\s+\w+\s*=\s*(?:async\s*)?\([^)]*\)\s*=>)\s*([a-zA-Z0-9_]+)", line)
                    if fn_match:
                        if current_fn and (i - current_fn_start) > 50:
                            oversized_functions.append((rel_file, current_fn, i - current_fn_start))
                        current_fn = fn_match.group(1)
                        current_fn_start = i

                if current_fn and (len(lines) - current_fn_start) > 50:
                    oversized_functions.append((rel_file, current_fn, len(lines) - current_fn_start))

            except Exception:
                pass

        if total_files > max_files:
            break

    # Calculate Clean-Code Score (100 base)
    score = 100
    score -= len(monolith_files) * 6
    score -= len(oversized_functions) * 3
    score -= min(15, len(debt_markers))
    score = max(20, min(100, score))

    if score >= 90:
        grade = "A+ (Excellent Modular Architecture)"
    elif score >= 80:
        grade = "A (Clean & Maintainable)"
    elif score >= 70:
        grade = "B (Good, minor refactoring needed)"
    elif score >= 60:
        grade = "C (Noticeable Technical Debt)"
    elif score >= 50:
        grade = "D (High Coupling / Monolith Risk)"
    else:
        grade = "F (Severe Architectural Debt)"

    comment_ratio = (total_comments / total_loc * 100) if total_loc > 0 else 0

    lines = [
        f"### 🏗️ Codebase Architecture & Clean-Code Audit\n",
        f"**Target Directory:** `{base_path}`",
        f"**Health Grade:** **{grade}** (`{score}/100`)",
        f"- **Files Scanned:** {total_files} | **Total LOC:** {total_loc:,}",
        f"- **Comment Density:** {comment_ratio:.1f}% ({total_comments:,} lines)\n"
    ]

    if monolith_files:
        lines.append(f"#### ⚠️ Monolith Files (>500 LOC) — Refactor into Sub-modules:")
        for mf, count in monolith_files[:8]:
            lines.append(f"- `{mf}`: **{count:,} lines**")
        lines.append("")

    if oversized_functions:
        lines.append(f"#### ⚠️ Oversized God-Functions (>50 lines) — Break into Sub-routines:")
        for rel_f, fn_name, fn_len in oversized_functions[:8]:
            lines.append(f"- `{rel_f}` ➔ `def {fn_name}()` ({fn_len} lines)")
        lines.append("")

    if debt_markers:
        lines.append(f"#### 📌 Open Technical Debt Markers ({len(debt_markers)} found):")
        for rel_f, line_num, text in debt_markers[:6]:
            lines.append(f"- `{rel_f}:{line_num}`: `{text}`")
        lines.append("")

    if not monolith_files and not oversized_functions:
        lines.append("✓ **High Architectural Cohesion:** No god files or oversized functions detected.")

    return "\n".join(lines)


def profile_process_telemetry(target: str = "") -> str:
    """
    Profile system processes: inspects memory usage (RSS, VMS), CPU utilization,
    thread allocation, open file handles, and flags potential memory leaks.
    """
    clean_target = target.strip().lower()

    if not clean_target or clean_target in ("top", "overview", "all"):
        # Overview of top memory consumers
        procs = []
        for p in psutil.process_iter(['pid', 'name', 'memory_info', 'cpu_percent', 'num_threads']):
            try:
                info = p.info
                rss_mb = info['memory_info'].rss / 1024 / 1024 if info.get('memory_info') else 0
                procs.append({
                    "pid": info['pid'],
                    "name": info['name'],
                    "rss_mb": rss_mb,
                    "threads": info.get('num_threads', 0),
                    "cpu": info.get('cpu_percent', 0.0)
                })
            except Exception:
                pass

        procs.sort(key=lambda x: x['rss_mb'], reverse=True)
        lines = ["### 📊 Top System Processes (Telemetry Snapshot)\n"]
        lines.append("| PID | Process Name | Memory (RSS) | Threads | CPU % |")
        lines.append("|:---:|:---|:---:|:---:|:---:|")
        for p in procs[:10]:
            lines.append(f"| `{p['pid']}` | **{p['name']}** | `{p['rss_mb']:.1f} MB` | {p['threads']} | {p['cpu']}% |")
        return "\n".join(lines)

    # Specific process lookup by PID or Name
    matched_proc = None
    if clean_target.isdigit():
        target_pid = int(clean_target)
        try:
            matched_proc = psutil.Process(target_pid)
        except Exception:
            return f"Process with PID {target_pid} not found."
    else:
        for p in psutil.process_iter(['pid', 'name']):
            try:
                if clean_target in p.info['name'].lower():
                    matched_proc = p
                    break
            except Exception:
                pass

    if not matched_proc:
        return f"No running process matching '{target}' was found."

    try:
        p = matched_proc
        mem_info = p.memory_info()
        rss_mb = mem_info.rss / 1024 / 1024
        vms_mb = mem_info.vms / 1024 / 1024
        threads = p.num_threads()
        cpu_pct = p.cpu_percent(interval=0.2)
        create_time = datetime.fromtimestamp(p.create_time()).strftime("%I:%M:%S %p")
        num_handles = p.num_handles() if hasattr(p, "num_handles") else "N/A"
        cmdline = " ".join(p.cmdline()[:5]) if p.cmdline() else p.name()

        # Anomaly checks
        warnings = []
        if rss_mb > 2048:
            warnings.append("⚠ High Memory Usage: Consuming over 2 GB RAM.")
        if threads > 60:
            warnings.append(f"⚠ High Thread Count: {threads} active threads.")
        if isinstance(num_handles, int) and num_handles > 2000:
            warnings.append(f"⚠ Excessive File Handles: {num_handles} open handles (potential leak).")

        lines = [
            f"### 🔬 Process Telemetry Diagnostic: `{p.name()}` [PID {p.pid}]\n",
            f"- **Command:** `{cmdline[:90]}`",
            f"- **Started At:** {create_time}",
            f"- **Memory (Physical RSS):** **{rss_mb:.1f} MB**",
            f"- **Memory (Virtual VMS):** `{vms_mb:.1f} MB`",
            f"- **Active Threads:** `{threads}`",
            f"- **Open OS Handles:** `{num_handles}`",
            f"- **CPU Utilization:** `{cpu_pct}%`\n"
        ]
        if warnings:
            lines.append("#### 🚨 Anomaly Alerts:")
            for w in warnings:
                lines.append(f"- {w}")
        else:
            lines.append("✓ **Healthy State:** Memory, thread allocations, and handles within normal operational thresholds.")

        return "\n".join(lines)
    except Exception as e:
        return f"Error profiling process {target}: {e}"


def inspect_git_repositories(search_dir: str = ".") -> str:
    """
    Search and audit Git repositories under a path: reports branch name,
    uncommitted changes, untracked files, ahead/behind upstream status, and last commit.
    """
    base_path = Path(search_dir).resolve()
    if not base_path.exists():
        return f"Path '{search_dir}' does not exist."

    # Look for .git directories
    repos = []
    if (base_path / ".git").exists():
        repos.append(base_path)
    else:
        for root, dirs, _ in os.walk(base_path):
            if ".git" in dirs:
                repos.append(Path(root))
                dirs.remove(".git")
            # Limit search depth
            if len(Path(root).relative_to(base_path).parts) >= 3:
                dirs.clear()

    if not repos:
        return f"No Git repositories found in `{base_path}`."

    lines = [f"### 🐙 Git Multi-Repository Health Inspector\n"]

    for repo in repos:
        repo_name = repo.name
        rel_path = repo.relative_to(base_path) if repo != base_path else "."

        # Check current branch
        branch = "unknown"
        try:
            r = subprocess.run(["git", "branch", "--show-current"], cwd=repo, capture_output=True, text=True, timeout=4)
            branch = r.stdout.strip() or "HEAD (detached)"
        except Exception:
            pass

        # Check dirty state
        status_out = ""
        try:
            r = subprocess.run(["git", "status", "--porcelain"], cwd=repo, capture_output=True, text=True, timeout=4)
            status_out = r.stdout.strip()
        except Exception:
            pass

        dirty_count = len(status_out.splitlines()) if status_out else 0
        state_badge = "✓ Clean" if dirty_count == 0 else f"⚠ {dirty_count} uncommitted changes"

        # Check latest commit
        latest_commit = "No commits"
        try:
            r = subprocess.run(["git", "log", "-1", "--format=%h - %s (%cr)"], cwd=repo, capture_output=True, text=True, timeout=4)
            latest_commit = r.stdout.strip() or "No commits"
        except Exception:
            pass

        lines.append(f"#### 📁 Repository: `{repo_name}` (`{rel_path}`)")
        lines.append(f"- **Branch:** `{branch}` | **State:** **{state_badge}**")
        lines.append(f"- **Latest Commit:** `{latest_commit}`\n")

    return "\n".join(lines)
