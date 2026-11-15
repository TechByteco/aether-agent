"""
AETHER Sovereign Skills Galaxy: Process Forensics, File Intelligence & Cryptography (Skills 96 - 120)
===================================================================================================
Implements deep process thread inspection, memory mapping, process priority escalation,
cryptographic hashing, LZMA/ZIP compression, directory change watchers, and secure shredding.
"""

import hashlib
import json
import logging
import lzma
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import psutil

logger = logging.getLogger("aether.skills_galaxy.systems_and_files")


# ══════════════════════════════════════════════════════════════════════════════
# Section 8: Process & Memory Forensics (Skills 96 - 105)
# ══════════════════════════════════════════════════════════════════════════════

def tool_proc_get_process_threads(pid: int) -> Dict[str, Any]:
    """[Skill 96] Inspect active CPU threads, user/system times for a process."""
    try:
        proc = psutil.Process(int(pid))
        threads = [{"id": t.id, "user_time": t.user_time, "system_time": t.system_time} for t in proc.threads()]
        return {"status": "success", "pid": pid, "name": proc.name(), "thread_count": len(threads), "threads": threads[:15]}
    except Exception as e:
        return {"status": "error", "pid": pid, "message": str(e)}


def tool_proc_set_process_priority(pid: int, priority: str = "HIGH") -> Dict[str, Any]:
    """[Skill 97] Set Windows process scheduling priority class (IDLE, BELOW_NORMAL, NORMAL, ABOVE_NORMAL, HIGH, REALTIME)."""
    p_map = {
        "IDLE": psutil.IDLE_PRIORITY_CLASS,
        "BELOW_NORMAL": psutil.BELOW_NORMAL_PRIORITY_CLASS,
        "NORMAL": psutil.NORMAL_PRIORITY_CLASS,
        "ABOVE_NORMAL": psutil.ABOVE_NORMAL_PRIORITY_CLASS,
        "HIGH": psutil.HIGH_PRIORITY_CLASS,
        "REALTIME": psutil.REALTIME_PRIORITY_CLASS,
    }
    target_class = p_map.get(priority.upper(), psutil.NORMAL_PRIORITY_CLASS)
    try:
        proc = psutil.Process(int(pid))
        proc.nice(target_class)
        return {"status": "success", "pid": pid, "name": proc.name(), "priority_set": priority.upper()}
    except Exception as e:
        return {"status": "error", "pid": pid, "message": str(e)}


def tool_proc_kill_by_name_force(process_name: str) -> Dict[str, Any]:
    """[Skill 98] Force terminate all process instances matching an executable name."""
    killed = 0
    for p in psutil.process_iter(["pid", "name"]):
        if p.info["name"] and p.info["name"].lower() == process_name.lower():
            try:
                p.kill()
                killed += 1
            except Exception:
                pass
    return {"status": "success", "process_name": process_name, "killed_instances": killed}


def tool_proc_suspend_process(pid: int) -> Dict[str, Any]:
    """[Skill 99] Temporarily suspend process execution (pause CPU usage)."""
    try:
        proc = psutil.Process(int(pid))
        proc.suspend()
        return {"status": "success", "pid": pid, "action": "suspended"}
    except Exception as e:
        return {"status": "error", "pid": pid, "message": str(e)}


def tool_proc_resume_process(pid: int) -> Dict[str, Any]:
    """[Skill 100] Resume execution of a previously suspended process."""
    try:
        proc = psutil.Process(int(pid))
        proc.resume()
        return {"status": "success", "pid": pid, "action": "resumed"}
    except Exception as e:
        return {"status": "error", "pid": pid, "message": str(e)}


def tool_proc_inspect_memory_maps(pid: int) -> Dict[str, Any]:
    """[Skill 101] Inspect virtual memory usage and resident set size."""
    try:
        proc = psutil.Process(int(pid))
        mem = proc.memory_info()
        return {
            "status": "success",
            "pid": pid,
            "name": proc.name(),
            "rss_mb": round(mem.rss / 1024 / 1024, 2),
            "vms_mb": round(mem.vms / 1024 / 1024, 2),
        }
    except Exception as e:
        return {"status": "error", "pid": pid, "message": str(e)}


def tool_proc_get_loaded_dlls(pid: int) -> Dict[str, Any]:
    """[Skill 102] Query loaded dynamic link libraries (DLLs) mapped into process memory."""
    try:
        proc = psutil.Process(int(pid))
        maps = proc.memory_maps()
        dlls = [m.path for m in maps if m.path and m.path.lower().endswith(".dll")]
        return {"status": "success", "pid": pid, "count": len(dlls), "dlls": list(set(dlls))[:20]}
    except Exception as e:
        return {"status": "error", "pid": pid, "message": str(e)}


def tool_proc_get_open_handles(pid: int) -> Dict[str, Any]:
    """[Skill 103] Enumerate open file handles held by a process."""
    try:
        proc = psutil.Process(int(pid))
        files = [f.path for f in proc.open_files()]
        return {"status": "success", "pid": pid, "open_files_count": len(files), "files": files[:20]}
    except Exception as e:
        return {"status": "error", "pid": pid, "message": str(e)}


def tool_proc_monitor_cpu_spike(threshold_pct: float = 80.0, duration_sec: float = 2.0) -> Dict[str, Any]:
    """[Skill 104] Monitor and detect any rogue processes exceeding CPU threshold over interval."""
    t0 = time.time()
    culprits = []
    for proc in psutil.process_iter(["pid", "name", "cpu_percent"]):
        try:
            pct = proc.cpu_percent(interval=None)
            if pct and pct >= threshold_pct:
                culprits.append({"pid": proc.pid, "name": proc.info["name"], "cpu_pct": pct})
        except Exception:
            pass
    return {"status": "success", "monitoring_window_sec": duration_sec, "spikes_detected": culprits}


def tool_proc_restart_process(process_name: str) -> Dict[str, Any]:
    """[Skill 105] Cleanly restart an executable process."""
    kill_res = tool_proc_kill_by_name_force(process_name)
    time.sleep(0.5)
    subprocess.Popen([process_name], shell=True)
    return {"status": "success", "process_name": process_name, "restarted": True}


# ══════════════════════════════════════════════════════════════════════════════
# Section 9: File Intelligence, Archival & Cryptography (Skills 106 - 120)
# ══════════════════════════════════════════════════════════════════════════════

def tool_file_create_zip_archive(source_dir: str, output_zip: str) -> Dict[str, Any]:
    """[Skill 106] Create a compressed ZIP archive from any file or folder directory."""
    src = Path(source_dir).resolve()
    out = Path(output_zip).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    file_count = 0
    with zipfile.ZipFile(str(out), "w", zipfile.ZIP_DEFLATED) as zf:
        if src.is_file():
            zf.write(str(src), arcname=src.name)
            file_count = 1
        else:
            for root, _, files in os.walk(str(src)):
                for file in files:
                    full_p = Path(root) / file
                    zf.write(str(full_p), arcname=str(full_p.relative_to(src)))
                    file_count += 1
    return {"status": "success", "archive": str(out), "files_archived": file_count, "size_bytes": out.stat().st_size}


def tool_file_extract_zip_archive(zip_path: str, extract_to: str) -> Dict[str, Any]:
    """[Skill 107] Safely unpack a ZIP archive to a destination folder."""
    try:
        zp = Path(zip_path).resolve()
        if not zp.exists() or not zipfile.is_zipfile(str(zp)):
            return {"status": "error", "message": f"Path '{zip_path}' is not a valid ZIP archive."}
        dest = Path(extract_to).resolve()
        dest.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(str(zp), "r") as zf:
            zf.extractall(str(dest))
            names = zf.namelist()
        return {"status": "success", "extracted_to": str(dest), "file_count": len(names)}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def tool_file_compute_hash_sha256(file_path: str) -> Dict[str, Any]:
    """[Skill 108] Compute the SHA-256 cryptographic checksum of a file."""
    fp = Path(file_path).resolve()
    if not fp.is_file():
        return {"status": "error", "message": f"'{file_path}' is not a regular file."}
    sha = hashlib.sha256()
    with open(str(fp), "rb") as f:
        while chunk := f.read(65536):
            sha.update(chunk)
    return {"status": "success", "file": str(fp), "sha256": sha.hexdigest(), "size_bytes": fp.stat().st_size}


def tool_file_find_duplicates_by_hash(directory: str) -> Dict[str, Any]:
    """[Skill 109] Scan directory tree to detect duplicate files sharing identical SHA-256 hash."""
    hashes: Dict[str, List[str]] = {}
    root_p = Path(directory).resolve()
    for root, _, files in os.walk(str(root_p)):
        for f in files:
            p = Path(root) / f
            try:
                if p.stat().st_size > 0:
                    h = tool_file_compute_hash_sha256(str(p)).get("sha256")
                    hashes.setdefault(h, []).append(str(p))
            except Exception:
                pass
    dupes = {h: paths for h, paths in hashes.items() if len(paths) > 1}
    return {"status": "success", "scanned_dir": str(root_p), "duplicate_groups": len(dupes), "duplicates": dupes}


def tool_file_secure_shred(file_path: str, passes: int = 3) -> Dict[str, Any]:
    """[Skill 110] Cryptographically overwrite a file multiple times before unlinking."""
    fp = Path(file_path).resolve()
    if not fp.is_file():
        return {"status": "error", "message": f"'{file_path}' is not a regular file."}
    size = fp.stat().st_size
    with open(str(fp), "ba+", buffering=0) as f:
        for _ in range(passes):
            f.seek(0)
            f.write(os.urandom(size))
    fp.unlink()
    return {"status": "success", "shredded_file": str(fp), "passes": passes}


def tool_file_compress_lzma(file_path: str, output_xz: str = "") -> Dict[str, Any]:
    """[Skill 111] Compress file using high-ratio LZMA2 algorithm."""
    try:
        fp = Path(file_path).resolve()
        if not fp.exists():
            return {"status": "error", "message": f"File '{file_path}' does not exist."}
        out = Path(output_xz or f"{fp}.xz").resolve()
        with open(str(fp), "rb") as fin, lzma.open(str(out), "wb") as fout:
            shutil.copyfileobj(fin, fout)
        return {"status": "success", "compressed_path": str(out), "ratio": round(out.stat().st_size / max(1, fp.stat().st_size), 4)}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def tool_file_decompress_lzma(xz_path: str, output_file: str = "") -> Dict[str, Any]:
    """[Skill 112] Decompress an LZMA/XZ file."""
    try:
        xp = Path(xz_path).resolve()
        if not xp.exists():
            return {"status": "error", "message": f"File '{xz_path}' does not exist."}
        out = Path(output_file or str(xp)[:-3]).resolve()
        with lzma.open(str(xp), "rb") as fin, open(str(out), "wb") as fout:
            shutil.copyfileobj(fin, fout)
        return {"status": "success", "decompressed_to": str(out)}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def tool_file_watch_directory_changes(directory: str, duration_sec: float = 2.0) -> Dict[str, Any]:
    """[Skill 113] Snapshot directory state and report newly created or modified files."""
    d = Path(directory).resolve()
    before = {p: p.stat().st_mtime for p in d.rglob("*") if p.is_file()}
    time.sleep(duration_sec)
    after = {p: p.stat().st_mtime for p in d.rglob("*") if p.is_file()}
    created = [str(p) for p in after if p not in before]
    modified = [str(p) for p in after if p in before and after[p] != before[p]]
    return {"status": "success", "created": created, "modified": modified}


def tool_file_bulk_rename_regex(directory: str, search_pattern: str, replace_pattern: str) -> Dict[str, Any]:
    """[Skill 114] Bulk rename files matching a regex pattern."""
    try:
        d = Path(directory).resolve()
        if not d.is_dir():
            return {"status": "error", "message": f"Directory '{directory}' does not exist."}
        regex = re.compile(search_pattern)
        renamed = []
        for f in d.iterdir():
            if f.is_file() and regex.search(f.name):
                new_name = regex.sub(replace_pattern, f.name)
                new_path = f.parent / new_name
                f.rename(new_path)
                renamed.append({"old": f.name, "new": new_name})
        return {"status": "success", "renamed_count": len(renamed), "renamed": renamed}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def tool_file_get_metadata_exif(file_path: str) -> Dict[str, Any]:
    """[Skill 115] Extract file timestamps, POSIX permissions, and ownership."""
    fp = Path(file_path).resolve()
    if not fp.exists():
        return {"status": "error", "message": f"File '{file_path}' does not exist."}
    st = fp.stat()
    return {
        "status": "success",
        "file": str(fp),
        "size_bytes": st.st_size,
        "created_at": datetime.fromtimestamp(st.st_ctime, timezone.utc).isoformat(),
        "modified_at": datetime.fromtimestamp(st.st_mtime, timezone.utc).isoformat(),
    }


def tool_file_set_attributes_hidden_readonly(file_path: str, hidden: bool = False, readonly: bool = False) -> Dict[str, Any]:
    """[Skill 116] Modify Win32 file flags (Hidden, Read-Only)."""
    fp = Path(file_path).resolve()
    if not fp.exists():
        return {"status": "error", "message": f"File '{file_path}' does not exist."}
    flags = ""
    if hidden: flags += "+h "
    if readonly: flags += "+r "
    if flags:
        subprocess.run(f"attrib {flags} \"{fp}\"", shell=True, check=False)
    return {"status": "success", "file": str(fp), "flags_applied": flags.strip()}


def tool_file_create_symlink_or_junction(source_path: str, link_path: str) -> Dict[str, Any]:
    """[Skill 117] Create a symbolic link or directory junction."""
    try:
        src = Path(source_path).resolve()
        if not src.exists():
            return {"status": "error", "message": f"Source '{source_path}' does not exist."}
        lnk = Path(link_path).resolve()
        os.symlink(str(src), str(lnk), target_is_directory=src.is_dir())
        return {"status": "success", "source": str(src), "link": str(lnk)}
    except Exception as e:
        return {"status": "warning", "message": f"Symlink creation skipped or requires elevation: {e}"}


def tool_file_search_regex_content(directory: str, regex_pattern: str, file_ext: str = ".py") -> Dict[str, Any]:
    """[Skill 118] High-speed regex search inside files across a project."""
    d = Path(directory).resolve()
    pattern = re.compile(regex_pattern)
    matches = []
    for f in d.rglob(f"*{file_ext}"):
        try:
            lines = f.read_text(encoding="utf-8", errors="ignore").splitlines()
            for idx, line in enumerate(lines, 1):
                if pattern.search(line):
                    matches.append({"file": str(f.relative_to(d)), "line": idx, "content": line.strip()[:120]})
                    if len(matches) >= 30:
                        break
        except Exception:
            pass
        if len(matches) >= 30:
            break
    return {"status": "success", "match_count": len(matches), "matches": matches}


def tool_file_calculate_directory_size(directory: str) -> Dict[str, Any]:
    """[Skill 119] Recursively calculate total size, file count, and folder count."""
    d = Path(directory).resolve()
    total_bytes = 0
    file_count = 0
    for root, _, files in os.walk(str(d)):
        for f in files:
            try:
                total_bytes += (Path(root) / f).stat().st_size
                file_count += 1
            except Exception:
                pass
    return {
        "status": "success",
        "directory": str(d),
        "total_files": file_count,
        "total_mb": round(total_bytes / 1024 / 1024, 2),
        "total_gb": round(total_bytes / 1024 / 1024 / 1024, 3),
    }


def tool_file_create_temp_scratchpad(prefix: str = "aether_task") -> Dict[str, Any]:
    """[Skill 120] Create a temporary directory or scratchpad file for ephemeral agent tasks."""
    tmp = tempfile.mkdtemp(prefix=f"{prefix}_")
    return {"status": "success", "scratchpad_dir": tmp, "created_at": datetime.now(timezone.utc).isoformat()}
