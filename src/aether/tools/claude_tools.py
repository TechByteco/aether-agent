r"""
AETHER Claude Code Agent Tools Specification
============================================
Implements the exact tool interface and execution contracts used by Anthropic's Claude Code:
1. Bash (Terminal execution with exit codes, timeouts, directory support)
2. View / Read (Cat with line numbers, range slicing, offset bounds)
3. Edit / StrReplace (Strict unique substring replacement with diff reporting)
4. Write (Clean file creation and atomic overwrites)
5. Grep (Ripgrep-compatible fast regex code search with line numbers)
6. Glob / Find (Fast pattern and file tree matching)
7. Todo / TaskTracker (Claude Code's internal task management: pending, in_progress, completed)
8. Subagent Dispatch (Spawns specialized child agents with isolated contexts)
"""

import difflib
import fnmatch
import json
import logging
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("aether.claude_tools")


class ClaudeTodoManager:
    """
    Claude Code internal task management engine.
    Tracks pending, in_progress, and completed tasks during multi-step development.
    """
    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or (Path.home() / ".aether" / "claude_todos.json")
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.todos: List[Dict[str, Any]] = []
        self._load()

    def _load(self) -> None:
        if self.storage_path.exists():
            try:
                self.todos = json.loads(self.storage_path.read_text(encoding="utf-8"))
            except Exception:
                self.todos = []

    def _save(self) -> None:
        try:
            self.storage_path.write_text(json.dumps(self.todos, indent=2), encoding="utf-8")
        except Exception as e:
            logger.debug(f"Failed to persist todos: {e}")

    def add(self, text: str) -> Dict[str, Any]:
        task_id = str(len(self.todos) + 1)
        item = {
            "id": task_id,
            "text": text.strip(),
            "status": "pending",
            "created_at": time.time(),
        }
        self.todos.append(item)
        self._save()
        return item

    def update_status(self, task_id: str, status: str) -> Optional[Dict[str, Any]]:
        valid = {"pending", "in_progress", "completed", "cancelled"}
        if status.lower() not in valid:
            return None
        for t in self.todos:
            if t["id"] == str(task_id):
                t["status"] = status.lower()
                self._save()
                return t
        return None

    def list_all(self) -> List[Dict[str, Any]]:
        return self.todos

    def clear(self) -> None:
        self.todos = []
        self._save()

    def format_markdown(self) -> str:
        if not self.todos:
            return "No active tasks in Claude todo list."
        lines = ["### 📋 Claude Agent Active Tasks"]
        for t in self.todos:
            icon = "⚪"
            if t["status"] == "in_progress":
                icon = "🟡 [IN PROGRESS]"
            elif t["status"] == "completed":
                icon = "🟢 [DONE]"
            elif t["status"] == "cancelled":
                icon = "❌ [CANCELLED]"
            lines.append(f"{t['id']}. {icon} {t['text']}")
        return "\n".join(lines)


claude_todos = ClaudeTodoManager()


# ── 1. Claude Bash Tool ────────────────────────────────────────────────────────

def claude_bash(command: str, timeout_secs: int = 45, cwd: Optional[str] = None) -> str:
    """
    Execute shell commands in PowerShell/CMD with strict exit code reporting,
    streaming stdout/stderr, and working directory management.
    """
    target_cwd = cwd or os.getcwd()
    try:
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
            cwd=target_cwd,
            capture_output=True,
            text=True,
            timeout=timeout_secs,
            encoding="utf-8",
            errors="replace"
        )
        out = proc.stdout.strip()
        err = proc.stderr.strip()
        code = proc.returncode

        res = []
        if out:
            res.append(out)
        if err:
            res.append(f"[STDERR]\n{err}")
        res.append(f"\n[Exit code: {code}]")
        return "\n".join(res)
    except subprocess.TimeoutExpired:
        return f"Error: Command timed out after {timeout_secs} seconds.\nCommand: {command}"
    except Exception as e:
        return f"Execution error: {str(e)}"


# ── 2. Claude View / Read Tool ─────────────────────────────────────────────────

def claude_view(file_path: str, start_line: int = 1, end_line: Optional[int] = None) -> str:
    """
    Read file contents with 1-indexed line numbers (cat -n style).
    Supports pagination with start_line and end_line to avoid context saturation.
    """
    p = Path(file_path).expanduser().resolve()
    if not p.exists():
        return f"Error: File '{file_path}' does not exist."
    if not p.is_file():
        return f"Error: Path '{file_path}' is a directory, not a file."

    try:
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        total = len(lines)
        if total == 0:
            return f"[{p.name} — Empty file (0 lines)]"

        s_idx = max(0, start_line - 1)
        e_idx = min(total, end_line) if end_line is not None else min(total, s_idx + 120)

        numbered = [f"{i + 1:5d} | {lines[i]}" for i in range(s_idx, e_idx)]
        header = f"[{p.name} — Displaying lines {s_idx + 1}–{e_idx} of {total}]\n"
        footer = ""
        if e_idx < total:
            footer = f"\n... ({total - e_idx} more lines not shown. Use claude_view with start_line={e_idx + 1} to continue)"
        return header + "\n".join(numbered) + footer
    except Exception as e:
        return f"Error reading file '{file_path}': {str(e)}"


# ── 3. Claude Edit / StrReplace Tool ──────────────────────────────────────────

def claude_edit(file_path: str, old_string: str, new_string: str) -> str:
    """
    Surgical string replacement editor (Anthropic str_replace_editor contract).
    Requires old_string to match exactly and uniquely within the file.
    Produces a unified diff preview of the applied modification.
    """
    p = Path(file_path).expanduser().resolve()
    if not p.exists():
        return f"Error: File '{file_path}' does not exist."
    if not p.is_file():
        return f"Error: '{file_path}' is a directory."

    try:
        content = p.read_text(encoding="utf-8", errors="replace")

        if old_string not in content:
            return (
                f"Error: old_string was not found in '{p.name}'.\n"
                f"Ensure exact whitespace, indentation, and capitalization match."
            )

        occurrences = content.count(old_string)
        if occurrences > 1:
            return (
                f"Error: old_string is ambiguous ({occurrences} occurrences in '{p.name}').\n"
                f"Include more surrounding lines of context to make the replacement unique."
            )

        new_content = content.replace(old_string, new_string, 1)

        # Generate unified diff for verification
        orig_lines = content.splitlines(keepends=True)
        mod_lines = new_content.splitlines(keepends=True)
        diff = list(difflib.unified_diff(
            orig_lines,
            mod_lines,
            fromfile=f"a/{p.name}",
            tofile=f"b/{p.name}",
            n=3
        ))

        p.write_text(new_content, encoding="utf-8")
        diff_str = "".join(diff[:80])
        return f"✓ Successfully replaced text in {p.name}.\n\n```diff\n{diff_str}\n```"
    except Exception as e:
        return f"Error editing file '{file_path}': {str(e)}"


# ── 4. Claude Write Tool ───────────────────────────────────────────────────────

def claude_write(file_path: str, content: str) -> str:
    """
    Create a new file or overwrite an existing file with complete content.
    Automatically creates missing parent directories.
    """
    try:
        p = Path(file_path).expanduser().resolve()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        lines_count = len(content.splitlines())
        return f"✓ Successfully wrote {lines_count} lines ({len(content)} bytes) to `{p}`."
    except Exception as e:
        return f"Error writing file '{file_path}': {str(e)}"


# ── 5. Claude Grep Tool ────────────────────────────────────────────────────────

def claude_grep(
    query: str,
    path: str = ".",
    glob_filter: str = "*",
    case_sensitive: bool = False,
    max_matches: int = 50,
) -> str:
    """
    Fast regex and text search matching Claude Code's Grep tool.
    Searches file contents and returns file:line: content.
    """
    target = Path(path).expanduser().resolve()
    if not target.exists():
        return f"Error: Path '{path}' does not exist."

    # Try native ripgrep if available
    rg_bin = shutil_which_rg()
    if rg_bin:
        cmd = [rg_bin, "-n", "--no-heading", "--max-count", str(max_matches)]
        if not case_sensitive:
            cmd.append("-i")
        if glob_filter != "*":
            cmd.extend(["-g", glob_filter])
        cmd.extend([query, str(target)])
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=15, encoding="utf-8", errors="replace")
            if res.stdout:
                matches = res.stdout.strip().splitlines()[:max_matches]
                return f"Found {len(matches)} match(es):\n" + "\n".join(matches)
            return f"No matches found for '{query}' in '{path}'."
        except Exception:
            pass  # Fallback to Python implementation

    # Python fallback implementation
    try:
        flags = 0 if case_sensitive else re.IGNORECASE
        pattern = re.compile(query, flags)
    except re.error as e:
        return f"Invalid regex pattern: {e}"

    matches = []
    text_extensions = {
        '.py', '.ts', '.js', '.tsx', '.jsx', '.json', '.md', '.txt',
        '.html', '.css', '.toml', '.yaml', '.yml', '.rs', '.go', '.c', '.cpp', '.h', '.bat', '.ps1'
    }

    try:
        files = target.rglob("*") if target.is_dir() else [target]
        for f in files:
            if f.is_file() and f.suffix.lower() in text_extensions:
                if glob_filter != "*" and not fnmatch.fnmatch(f.name, glob_filter):
                    continue
                try:
                    for idx, line in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                        if pattern.search(line):
                            rel = f.relative_to(target) if target.is_dir() else f.name
                            matches.append(f"{rel}:{idx}: {line.strip()}")
                            if len(matches) >= max_matches:
                                break
                except Exception:
                    pass
            if len(matches) >= max_matches:
                break

        if not matches:
            return f"No matches found for '{query}' in '{path}'."
        return f"Found {len(matches)} match(es):\n" + "\n".join(matches)
    except Exception as e:
        return f"Grep search error: {str(e)}"


def shutil_which_rg() -> Optional[str]:
    import shutil
    return shutil.which("rg.exe") or shutil.which("rg")


# ── 6. Claude Glob / Find Tool ─────────────────────────────────────────────────

def claude_find(pattern: str, path: str = ".", max_results: int = 50) -> str:
    """
    Fast filename and directory search using glob patterns.
    """
    target = Path(path).expanduser().resolve()
    if not target.exists():
        return f"Error: Path '{path}' does not exist."

    matches = []
    try:
        for p in target.rglob(pattern):
            rel = p.relative_to(target)
            kind = "DIR " if p.is_dir() else "FILE"
            matches.append(f"{kind:4s} | {rel}")
            if len(matches) >= max_results:
                break

        if not matches:
            return f"No files or directories matching '{pattern}' in '{path}'."
        return f"Found {len(matches)} match(es):\n" + "\n".join(matches)
    except Exception as e:
        return f"Find error: {str(e)}"


# ── 7. Claude Todo Tool ────────────────────────────────────────────────────────

def claude_todo(action: str, text: str = "", task_id: str = "") -> str:
    """
    Manage Claude Code's internal task tracking list.
    Actions: 'add', 'start' (mark in-progress), 'done' (mark completed), 'list', 'clear'.
    """
    act = action.strip().lower()
    if act == "add":
        if not text:
            return "Error: text parameter required for adding a task."
        item = claude_todos.add(text)
        return f"✓ Task #{item['id']} added: '{item['text']}'"
    elif act in ("start", "in_progress"):
        if not task_id:
            return "Error: task_id parameter required."
        item = claude_todos.update_status(task_id, "in_progress")
        return f"🟡 Task #{task_id} marked IN PROGRESS" if item else f"Error: Task #{task_id} not found."
    elif act in ("done", "complete", "completed"):
        if not task_id:
            return "Error: task_id parameter required."
        item = claude_todos.update_status(task_id, "completed")
        return f"🟢 Task #{task_id} marked COMPLETED" if item else f"Error: Task #{task_id} not found."
    elif act == "clear":
        claude_todos.clear()
        return "✓ Cleared Claude task list."
    else:
        return claude_todos.format_markdown()


# ── 8. Claude Subagent Tool ────────────────────────────────────────────────────

def claude_subagent(role: str, objective: str, context: str = "") -> str:
    """
    Spawn an autonomous specialized subagent (e.g. 'researcher', 'coder', 'security_auditor', 'tester')
    running in an isolated context to execute a sub-task and report back findings.
    """
    from aether.brain.online_cortex import online_cortex
    valid_roles = ["code_architect", "security_auditor", "ui_specialist", "reasoning_analyst", "research_scientist"]
    matched_role = role.lower().replace(" ", "_")
    if matched_role not in valid_roles:
        matched_role = "code_architect"

    logger.info(f"[ClaudeAgent] Spawning subagent: {matched_role} for objective: {objective[:60]}...")
    try:
        result = online_cortex.dispatch_online_agent_task(
            role=matched_role,
            objective=objective,
            context=context
        )
        return (
            f"### 🤖 Subagent Report: `{matched_role.upper()}`\n"
            f"- **Objective:** {objective}\n\n"
            f"{result}"
        )
    except Exception as e:
        return f"Subagent error: {str(e)}"
