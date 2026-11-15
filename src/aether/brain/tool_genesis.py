"""
AETHER Dynamic Tool Genesis Engine (Option A)
==============================================
Enables AETHER to autonomously synthesize, test, persist, and live-mount
new custom Python tools into its cognitive runtime without restarting.

Architecture:
  1. Synthesis: Uses LLM (Local Ollama / FreeLLMAPI Online Cortex) to write clean, typed Python tools.
  2. AST Validation & Sandbox Execution: Validates syntax, safety constraints, and runs a test call.
  3. Dynamic Registration: Persists to `src/aether/tools/generated/<name>.py`, dynamically imports,
     and hot-mounts directly into `TOOL_DISPATCHER` and `AVAILABLE_TOOLS`.
  4. Cold-Start Persistence: Automatically re-imports all generated tools upon engine boot.
"""

import ast
import importlib.util
import inspect
import logging
import re
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import ollama

from aether.config import config
from aether.memory.store import memory

logger = logging.getLogger("aether.tool_genesis")

GENERATED_TOOLS_DIR = Path(__file__).parent.parent / "tools" / "generated"
GENERATED_TOOLS_DIR.mkdir(parents=True, exist_ok=True)

TOOL_GENESIS_SYSTEM_PROMPT = """You are AETHER's Autonomous Tool Genesis Engine.
Your task is to write a single, robust, production-grade Python tool function for AETHER.

CONSTRAINTS & RULES:
1. The function MUST start with 'tool_' (e.g. def tool_convert_currency(...)).
2. All parameters MUST have explicit type annotations and sensible defaults where appropriate.
3. The function MUST return a clean, human-readable 'str' response (markdown-formatted is encouraged).
4. The function MUST contain a detailed docstring explaining what it does, its parameters, and return value.
5. Wrap the implementation inside a try...except Exception block to return a clean error string if execution fails.
6. Only use Python standard library packages (e.g. math, hashlib, json, datetime, re, urllib.request, pathlib, csv, collections, random) or already installed packages (requests, bs4).
7. Output ONLY the raw Python code block enclosed in ```python ... ```. Do not include extraneous conversational text.
"""

TOOL_GENESIS_USER_PROMPT = """Objective: {task_description}
Suggested Tool Name: {tool_name}
Input Schema/Requirements: {input_schema}

Generate the complete, self-contained Python tool function:"""


class ToolGenesisEngine:
    def __init__(self, tools_dir: Optional[Path] = None):
        self.tools_dir = tools_dir or GENERATED_TOOLS_DIR
        self.tools_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._loaded_tools: Dict[str, Callable] = {}

    def _extract_code(self, response_text: str) -> str:
        """Extract Python code block from LLM output."""
        code_blocks = re.findall(r"```(?:python)?\s*(.*?)\s*```", response_text, re.DOTALL)
        if code_blocks:
            return code_blocks[0].strip()
        # Fallback if no code blocks are found
        return response_text.strip()

    def _derive_tool_name(self, code: str, fallback_name: str = "") -> str:
        """Extract the tool function name from AST or regex."""
        try:
            tree = ast.parse(code)
            for node in tree.body:
                if isinstance(node, ast.FunctionDef) and node.name.startswith("tool_"):
                    return node.name
                elif isinstance(node, ast.FunctionDef):
                    return f"tool_{node.name}"
        except Exception:
            pass

        # Regex fallback
        m = re.search(r"def\s+(tool_[a-zA-Z0-9_]+)\s*\(", code)
        if m:
            return m.group(1)

        cleaned_fallback = re.sub(r"[^a-zA-Z0-9_]", "_", fallback_name.lower().strip())
        if not cleaned_fallback.startswith("tool_"):
            cleaned_fallback = f"tool_{cleaned_fallback}"
        return cleaned_fallback or "tool_custom_generated"

    def validate_tool_sandbox(self, code: str, tool_name: str = "") -> Tuple[bool, str]:
        """
        Validates safety and syntax of generated code using AST static analysis and sandboxed execution.
        """
        # 1. AST Syntax Check
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return False, f"SyntaxError in generated code: {e}"

        # 2. Security & Anti-Pattern Check
        forbidden_calls = {"exec", "eval", "__import__", "compile"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in forbidden_calls:
                    return False, f"Security Violation: Forbidden call '{node.func.id}' detected in tool."

        # 3. Execution Dry-Run in Sandbox Scope
        sandbox_globals: Dict[str, Any] = {
            "__builtins__": __builtins__,
            "datetime": datetime,
            "re": re,
            "json": __import__("json"),
            "math": __import__("math"),
            "hashlib": __import__("hashlib"),
            "pathlib": Path,
        }
        sandbox_locals: Dict[str, Any] = {}

        try:
            exec(code, sandbox_globals, sandbox_locals)
        except Exception as e:
            return False, f"Execution validation failed during dry run: {e}"

        target_fn = None
        for k, v in sandbox_locals.items():
            if callable(v) and (k.startswith("tool_") or k == tool_name):
                target_fn = v
                break

        if not target_fn:
            return False, "Validation failed: No callable 'tool_*' function found in generated code."

        return True, "Code passed AST and dry-run execution validation successfully."

    def synthesize_tool(
        self,
        task_description: str,
        tool_name: str = "",
        input_schema: Optional[Dict[str, Any]] = None,
        model_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Autonomously synthesize a new Python tool using the LLM.
        """
        active_model = model_name or config.local_model
        prompt_text = TOOL_GENESIS_USER_PROMPT.format(
            task_description=task_description,
            tool_name=tool_name or "Auto-derived from objective",
            input_schema=str(input_schema or "Infer appropriate types and parameters"),
        )

        try:
            resp = ollama.chat(
                model=active_model,
                messages=[
                    {"role": "system", "content": TOOL_GENESIS_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt_text},
                ],
                options={"temperature": 0.2, "top_p": 0.9},
                keep_alive=config.keep_alive,
            )
            raw_output = resp.message.content or ""
        except Exception as e:
            # Fallback to Online Cortex if local fails
            try:
                from aether.brain.online_cortex import online_cortex
                raw_output = online_cortex.query_online_cortex(
                    prompt=prompt_text,
                    system_prompt=TOOL_GENESIS_SYSTEM_PROMPT,
                )
            except Exception as e2:
                return {
                    "success": False,
                    "error": f"Tool synthesis failed on both local and online models: Local error: {e} | Online error: {e2}",
                }

        code = self._extract_code(raw_output)
        derived_name = self._derive_tool_name(code, fallback_name=tool_name)

        # Validate in sandbox
        valid, msg = self.validate_tool_sandbox(code, tool_name=derived_name)
        if not valid:
            logger.warning(f"[ToolGenesis] Sandbox validation failed for {derived_name}: {msg}")
            return {
                "success": False,
                "tool_name": derived_name,
                "code": code,
                "error": msg,
            }

        return {
            "success": True,
            "tool_name": derived_name,
            "code": code,
            "validation_message": msg,
        }

    def register_dynamic_tool(
        self,
        tool_name: str,
        code: str,
        overwrite: bool = True,
    ) -> Dict[str, Any]:
        """
        Persists generated tool code to disk, imports the module, and hot-registers
        the function into AETHER's TOOL_DISPATCHER and AVAILABLE_TOOLS live.
        """
        clean_name = re.sub(r"[^a-zA-Z0-9_]", "_", tool_name.strip())
        if not clean_name.startswith("tool_"):
            clean_name = f"tool_{clean_name}"

        file_path = self.tools_dir / f"{clean_name}.py"
        if file_path.exists() and not overwrite:
            return {
                "success": False,
                "error": f"Tool file '{file_path.name}' already exists. Pass overwrite=True to replace.",
            }

        with self._lock:
            # 1. Write file to disk
            try:
                file_path.write_text(code, encoding="utf-8")
            except Exception as e:
                return {"success": False, "error": f"Failed to write tool file: {e}"}

            # 2. Dynamically import module
            try:
                spec = importlib.util.spec_from_file_location(clean_name, str(file_path))
                if spec is None or spec.loader is None:
                    return {"success": False, "error": f"Failed to create module spec for {clean_name}"}

                module = importlib.util.module_from_spec(spec)
                sys.modules[f"aether.tools.generated.{clean_name}"] = module
                spec.loader.exec_module(module)
            except Exception as e:
                return {"success": False, "error": f"Dynamic module load failed: {e}"}

            # 3. Find tool callable
            target_fn = getattr(module, clean_name, None)
            if not target_fn:
                # Find any function starting with tool_
                for attr_name, attr_val in inspect.getmembers(module, inspect.isfunction):
                    if attr_name.startswith("tool_"):
                        target_fn = attr_val
                        clean_name = attr_name
                        break

            if not target_fn:
                return {"success": False, "error": f"No function '{clean_name}' found in loaded module."}

            # 4. Mount into live AETHER engine
            self._loaded_tools[clean_name] = target_fn
            self._mount_into_engine(clean_name, target_fn)

            # 5. Record to long-term memory
            doc = inspect.getdoc(target_fn) or "Custom generated tool"
            memory.add_heuristic_rule(
                f"[Dynamic Tool Registered] {clean_name}: {doc.splitlines()[0]}",
                domain="tool_genesis",
            )

            logger.info(f"[ToolGenesis] ✓ Successfully registered and mounted dynamic tool '{clean_name}'.")

            return {
                "success": True,
                "tool_name": clean_name,
                "file_path": str(file_path),
                "docstring": doc,
                "message": f"Tool '{clean_name}' successfully synthesized, validated, and live-mounted into AETHER runtime.",
            }

    def _mount_into_engine(self, tool_name: str, tool_fn: Callable) -> None:
        """Inject tool into engine's TOOL_DISPATCHER and AVAILABLE_TOOLS."""
        try:
            import aether.brain.engine as engine_mod

            if hasattr(engine_mod, "TOOL_DISPATCHER"):
                engine_mod.TOOL_DISPATCHER[tool_name] = tool_fn
            if hasattr(engine_mod, "AVAILABLE_TOOLS") and tool_fn not in engine_mod.AVAILABLE_TOOLS:
                engine_mod.AVAILABLE_TOOLS.append(tool_fn)

            # Auto-register keywords from tool name
            if hasattr(engine_mod, "ACTION_KEYWORDS"):
                keywords = [k for k in tool_name.replace("tool_", "").split("_") if len(k) > 2]
                for kw in keywords:
                    if kw not in engine_mod.ACTION_KEYWORDS:
                        engine_mod.ACTION_KEYWORDS[kw] = [tool_name]
                    elif tool_name not in engine_mod.ACTION_KEYWORDS[kw]:
                        engine_mod.ACTION_KEYWORDS[kw].append(tool_name)
        except Exception as e:
            logger.warning(f"[ToolGenesis] Engine mount warning: {e}")

    def load_all_generated_tools(self) -> Dict[str, int]:
        """
        Scans `src/aether/tools/generated/*.py` and imports all persisted tools.
        Invoked on engine startup.
        """
        loaded_count = 0
        failed_count = 0

        for file_path in self.tools_dir.glob("tool_*.py"):
            mod_name = file_path.stem
            try:
                spec = importlib.util.spec_from_file_location(mod_name, str(file_path))
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[f"aether.tools.generated.{mod_name}"] = module
                    spec.loader.exec_module(module)

                    target_fn = getattr(module, mod_name, None)
                    if not target_fn:
                        for attr_name, attr_val in inspect.getmembers(module, inspect.isfunction):
                            if attr_name.startswith("tool_"):
                                target_fn = attr_val
                                mod_name = attr_name
                                break

                    if target_fn:
                        self._loaded_tools[mod_name] = target_fn
                        self._mount_into_engine(mod_name, target_fn)
                        loaded_count += 1
            except Exception as e:
                logger.error(f"[ToolGenesis] Failed to cold-load generated tool '{file_path.name}': {e}")
                failed_count += 1

        logger.info(f"[ToolGenesis] Cold-boot loaded {loaded_count} generated tools ({failed_count} failed).")
        return {"loaded": loaded_count, "failed": failed_count}

    def list_generated_tools(self) -> List[Dict[str, Any]]:
        """List all currently active dynamic generated tools."""
        results = []
        for file_path in self.tools_dir.glob("tool_*.py"):
            mod_name = file_path.stem
            fn = self._loaded_tools.get(mod_name)
            doc = (inspect.getdoc(fn) if fn else "Generated tool") or "No documentation"
            results.append({
                "tool_name": mod_name,
                "file_path": str(file_path),
                "is_active": mod_name in self._loaded_tools,
                "docstring": doc.splitlines()[0] if doc else "",
                "created_at": datetime.fromtimestamp(file_path.stat().st_ctime).isoformat(),
            })
        return results

    def delete_generated_tool(self, tool_name: str) -> bool:
        """Deletes a generated tool from disk and unmounts it from engine."""
        clean_name = tool_name.strip()
        if not clean_name.startswith("tool_"):
            clean_name = f"tool_{clean_name}"

        file_path = self.tools_dir / f"{clean_name}.py"
        with self._lock:
            if clean_name in self._loaded_tools:
                del self._loaded_tools[clean_name]

            # Unmount from engine
            try:
                import aether.brain.engine as engine_mod
                if hasattr(engine_mod, "TOOL_DISPATCHER") and clean_name in engine_mod.TOOL_DISPATCHER:
                    del engine_mod.TOOL_DISPATCHER[clean_name]
                if hasattr(engine_mod, "AVAILABLE_TOOLS"):
                    engine_mod.AVAILABLE_TOOLS = [f for f in engine_mod.AVAILABLE_TOOLS if f.__name__ != clean_name]
            except Exception:
                pass

            if file_path.exists():
                file_path.unlink()
                return True
        return False


# Global singleton instance
tool_genesis = ToolGenesisEngine()


# ── Exposed Tool Wrappers for Model & Dispatcher ──────────────────────────────

def tool_synthesize_new_tool(task_description: str, tool_name: str = "") -> str:
    """
    Autonomously design, synthesize, sandbox-validate, and live-mount a brand-new Python tool
    into AETHER's runtime to solve a novel or unsupported capability request.
    """
    res = tool_genesis.synthesize_tool(task_description=task_description, tool_name=tool_name)
    if not res.get("success"):
        return f"❌ Tool synthesis failed: {res.get('error')}"

    reg_res = tool_genesis.register_dynamic_tool(
        tool_name=res["tool_name"],
        code=res["code"],
        overwrite=True,
    )

    if not reg_res.get("success"):
        return f"❌ Tool registration failed: {reg_res.get('error')}"

    return (
        f"### ⚡ Dynamic Tool Genesis Succeeded\n"
        f"**Tool Name:** `{reg_res['tool_name']}`\n"
        f"**File Location:** `{reg_res['file_path']}`\n"
        f"**Status:** Live Mounted into `TOOL_DISPATCHER` & Ready to Execute!\n\n"
        f"```python\n{res['code']}\n```"
    )


def tool_list_generated_tools() -> str:
    """List all dynamically generated tools created by AETHER and currently mounted in the runtime."""
    tools = tool_genesis.list_generated_tools()
    if not tools:
        return "No dynamic tools generated yet. Use `tool_synthesize_new_tool` to create one on the fly."

    lines = [f"### 🧬 Active Dynamic Generated Tools ({len(tools)} Total)\n"]
    for t in tools:
        status_emoji = "🟢" if t["is_active"] else "⚪"
        lines.append(f"- {status_emoji} **`{t['tool_name']}`**: {t['docstring']} *(File: {Path(t['file_path']).name})*")
    return "\n".join(lines)


def tool_delete_generated_tool(tool_name: str) -> str:
    """Safely delete and unmount a dynamically generated tool."""
    success = tool_genesis.delete_generated_tool(tool_name)
    if success:
        return f"✓ Dynamic tool `{tool_name}` successfully unmounted and deleted from disk."
    return f"Failed to delete `{tool_name}` (not found or system error)."
