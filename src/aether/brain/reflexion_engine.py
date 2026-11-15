"""
AETHER Autonomous Reflexion Loop Engine (Option B)
===================================================
Intercepts tool execution failures, command errors, and subagent faults in real-time.
Derives permanent cognitive invariant rules via automated post-mortem critique,
commits them to persistent SQLite FTS5 memory, synchronizes with the workspace
cognitive invariants rule file (.agents/rules/aether-cognitive-invariants.md),
and facilitates real-time self-healing retries.

Architecture:
  1. Failure Interception: Catches exceptions or error returns from TOOL_DISPATCHER and ReWOO.
  2. Critique & Invariant Derivation: LLM-guided (or heuristic fallback) root-cause analysis.
  3. Memory Persistence: Commits to SQLite `heuristic_rules` (domain='reflexion').
  4. Rule Synchronization: Appends unique rules to `.agents/rules/aether-cognitive-invariants.md`.
  5. Context Injection: Injects the verbal critique back into the turn context for immediate model self-correction.
"""

import json
import logging
import re
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import ollama

from aether.config import config
from aether.memory.store import memory

logger = logging.getLogger("aether.reflexion_engine")

RULES_FILE_PATH = Path(__file__).parent.parent.parent.parent / ".agents" / "rules" / "aether-cognitive-invariants.md"

REFLEXION_PROMPT = """You are AETHER's Cognitive Reflexion Critic.
An operational failure occurred during agent tool execution. Analyse the failure and produce a definitive corrective rule.

TASK CONTEXT:
Objective: {task}
Failed Action/Tool: {failed_tool}
Arguments: {args}
Error Traceback/Message:
{error_message}

Provide your response in JSON format with EXACTLY the following keys:
{{
  "diagnosis": "Precise 1-sentence root-cause diagnosis of why this specific action failed.",
  "critique": "Actionable guidance on how the model should modify its approach right now.",
  "suggested_fix": "Concrete corrected parameters, replacement command, or alternative tool to use.",
  "invariant_rule": "A universal permanent invariant rule starting with '[Invariant]' that prevents repeating this exact class of error."
}}
"""


class ReflexionEngine:
    def __init__(self, rules_file: Optional[Path] = None):
        self.rules_file = rules_file or RULES_FILE_PATH
        self._lock = threading.Lock()
        self._recent_reflections: List[Dict[str, Any]] = []

    def _rule_based_diagnosis(
        self,
        failed_tool: str,
        args: Dict[str, Any],
        error_message: str,
    ) -> Dict[str, str]:
        """Fast-path deterministic heuristic error analyzer when LLM is offline or fast recovery is needed."""
        err_lower = error_message.lower()
        tool_lower = failed_tool.lower()

        # 1. PowerShell / Command syntax error
        if "is not recognized" in err_lower or "term is not recognized" in err_lower:
            cmd = str(args.get("command", "")).split()[0] if args.get("command") else "command"
            return {
                "diagnosis": f"The CLI command '{cmd}' is not found in PATH or not installed on Windows ARM64.",
                "critique": f"Avoid invoking non-existent binary '{cmd}'. Use built-in PowerShell or Python tools instead.",
                "suggested_fix": "Use execute_python_code or verify the executable path using Get-Command in PowerShell.",
                "invariant_rule": f"[Invariant] Before executing external tool '{cmd}', verify its existence in PATH or use native Python standard library fallbacks.",
            }

        # 2. File not found
        if "filenotfound" in err_lower or "does not exist" in err_lower or "cannot find the file" in err_lower:
            file_arg = args.get("file_path") or args.get("path") or args.get("target_file") or "target"
            return {
                "diagnosis": f"Target path '{file_arg}' does not exist on the filesystem.",
                "critique": f"Always inspect the directory or use tool_find_files before reading/editing '{file_arg}'.",
                "suggested_fix": "Run tool_find_files to locate the correct file path.",
                "invariant_rule": f"[Invariant] Always verify file existence via tool_find_files or tool_inspect_directory before attempting surgical reads or edits.",
            }

        # 3. Surgical edit target not found / ambiguous
        if "string not found" in err_lower or "count == 0" in err_lower or "not found in" in err_lower:
            return {
                "diagnosis": "Surgical edit search block was not found verbatim in target file.",
                "critique": "Line endings, indentation, or whitespace differed from the actual file content.",
                "suggested_fix": "Read the file window using tool_read_file_window first to copy the exact lines verbatim.",
                "invariant_rule": "[Invariant] When performing surgical code patches (tool_patch_file_block), view the exact line window first to ensure character-level verbatim matching.",
            }

        # 4. Port already in use / Connection refused
        if "address already in use" in err_lower or "10048" in err_lower or "connection refused" in err_lower:
            return {
                "diagnosis": "Network socket or target port is unavailable or refused connection.",
                "critique": "Verify whether another daemon process is occupying the requested port.",
                "suggested_fix": "Use tool_audit_active_connections or select an alternative port (e.g. port + 1).",
                "invariant_rule": "[Invariant] For network operations and local servers, dynamically check port availability or use socket test before binding.",
            }

        # 5. Permission denied
        if "permission denied" in err_lower or "access is denied" in err_lower:
            return {
                "diagnosis": "The operation lacks sufficient administrative privileges or target file is locked.",
                "critique": "Avoid writing to protected system directories; redirect output to user workspace.",
                "suggested_fix": "Target the workspace directory `c:\\Users\\saali\\Documents\\antigravity\\charming-lovelace` instead.",
                "invariant_rule": "[Invariant] Confine all automated writes, scripts, and temporary files strictly within the active user workspace directory.",
            }

        # 6. Default Fallback
        first_line = error_message.strip().splitlines()[0][:120] if error_message else "Unknown runtime error"
        return {
            "diagnosis": f"Action {failed_tool} failed with: {first_line}",
            "critique": f"Review input arguments {args} and handle boundary conditions for {failed_tool}.",
            "suggested_fix": f"Re-attempt {failed_tool} with sanitized parameters.",
            "invariant_rule": f"[Invariant] Tool {failed_tool}: Verify parameter types and guard against '{first_line}'.",
        }

    def reflect_and_heal(
        self,
        failed_tool: str,
        args: Dict[str, Any],
        error_message: str,
        original_task: str = "",
        context: str = "",
        model_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Intercepts tool execution failure, conducts post-mortem critique,
        stores permanent heuristic invariant in SQLite, syncs with .agents/rules,
        and returns actionable self-healing guidance.
        """
        active_model = model_name or config.local_model
        diag_data: Dict[str, str] = {}

        # 1. Attempt LLM Critique
        try:
            formatted_prompt = REFLEXION_PROMPT.format(
                task=original_task or "Unspecified user task",
                failed_tool=failed_tool,
                args=json.dumps(args, default=str),
                error_message=str(error_message)[:2000],
            )
            resp = ollama.chat(
                model=active_model,
                messages=[{"role": "user", "content": formatted_prompt}],
                format="json",
                options={"temperature": 0.1, "top_p": 0.8},
                keep_alive=config.keep_alive,
            )
            parsed = json.loads(resp.message.content or "{}")
            if parsed.get("invariant_rule"):
                diag_data = parsed
        except Exception as e:
            logger.debug(f"[ReflexionEngine] LLM critique failed ({e}), falling back to heuristic analyzer.")

        # 2. Heuristic fallback if LLM returned incomplete data
        if not diag_data or not diag_data.get("invariant_rule"):
            diag_data = self._rule_based_diagnosis(failed_tool, args, error_message)

        invariant_rule = diag_data.get("invariant_rule", f"[Invariant] Avoid error in {failed_tool}: {error_message[:60]}")
        diagnosis = diag_data.get("diagnosis", "Error occurred during execution.")
        critique = diag_data.get("critique", "Adjust parameters and retry.")
        suggested_fix = diag_data.get("suggested_fix", "")

        with self._lock:
            # 3. Commit to SQLite Memory Store
            rule_domain = f"reflexion:{failed_tool.replace('tool_', '')}"
            rule_id = memory.add_heuristic_rule(invariant_rule, domain=rule_domain)

            # 4. Synchronize with workspace .agents/rules file
            self._sync_rule_to_file(invariant_rule)

            reflection_record = {
                "timestamp": datetime.now().isoformat(),
                "failed_tool": failed_tool,
                "error": str(error_message)[:250],
                "diagnosis": diagnosis,
                "critique": critique,
                "suggested_fix": suggested_fix,
                "invariant_rule": invariant_rule,
                "rule_id": rule_id,
            }
            self._recent_reflections.append(reflection_record)
            if len(self._recent_reflections) > 50:
                self._recent_reflections.pop(0)

        logger.info(f"[ReflexionEngine] ✓ Healed & Committed Reflexion Invariant #{rule_id}: {invariant_rule}")

        return {
            "success": True,
            "rule_id": rule_id,
            "diagnosis": diagnosis,
            "critique": critique,
            "suggested_fix": suggested_fix,
            "invariant_rule": invariant_rule,
            "self_heal_directive": (
                f"⚠️ **Self-Correction Triggered (Reflexion)**:\n"
                f"- **Diagnosis:** {diagnosis}\n"
                f"- **Critique:** {critique}\n"
                f"- **Suggested Fix:** {suggested_fix}\n"
                f"- **Learned Invariant (#{rule_id}):** `{invariant_rule}`"
            ),
        }

    def _sync_rule_to_file(self, invariant_rule: str) -> bool:
        """Appends unique invariant rules to .agents/rules/aether-cognitive-invariants.md."""
        try:
            if not self.rules_file.exists():
                return False

            content = self.rules_file.read_text(encoding="utf-8")
            clean_rule = invariant_rule.strip()
            if clean_rule in content:
                return True  # Already present, deduplicated

            section_header = "## 5. Autonomous Learned Runtime Invariants"
            if section_header not in content:
                content += f"\n\n{section_header}\n- {clean_rule}\n"
            else:
                content += f"- {clean_rule}\n"

            self.rules_file.write_text(content, encoding="utf-8")
            return True
        except Exception as e:
            logger.warning(f"[ReflexionEngine] Failed to sync rule to file: {e}")
            return False

    def get_recent_reflections(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieve recent post-mortem reflections."""
        with self._lock:
            return list(reversed(self._recent_reflections[-limit:]))

    def get_reflexion_stats(self) -> Dict[str, Any]:
        """Get summary statistics of learned invariants and self-healing operations."""
        rules = memory.recall_heuristic_rules("reflexion", limit=100)
        return {
            "total_invariants_learned": len(rules),
            "recent_reflections_count": len(self._recent_reflections),
            "rules_file_synced": self.rules_file.exists(),
        }


# Global singleton instance
reflexion_engine = ReflexionEngine()


# ── Exposed Tool Wrappers for Model & Dispatcher ──────────────────────────────

def tool_reflect_on_error(failed_action: str, error_trace: str, context: str = "") -> str:
    """
    Manually or programmatically trigger a Reflexion post-mortem critique on an error,
    synthesizing a permanent invariant rule committed to long-term memory and invariants configuration.
    """
    res = reflexion_engine.reflect_and_heal(
        failed_tool=failed_action,
        args={},
        error_message=error_trace,
        original_task=context,
    )
    return res["self_heal_directive"]


def tool_audit_error_invariants(domain: str = "") -> str:
    """
    Audit all active Reflexion cognitive invariants and learned rules stored across memory.
    """
    rules = memory.recall_heuristic_rules(domain if domain.strip() else "reflexion", limit=15)
    if not rules:
        return "No Reflexion invariants recorded for this domain."

    lines = [f"### 🛡️ Active Reflexion Invariants ({len(rules)} Rules Active)\n"]
    for idx, r in enumerate(rules, 1):
        lines.append(f"{idx}. {r}")
    return "\n".join(lines)
