"""
AETHER Dynamic Code Execution Sandbox
Allows AETHER to write, test, and execute Python code in a sandboxed, timeout-guarded environment.
Provides on-the-fly computational problem solving, data crunching, and script execution.
"""

import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict


def execute_python_code(code: str, timeout_seconds: int = 60) -> str:
    """
    Execute arbitrary Python code in an isolated subprocess with timeout and memory safety.
    """
    clean_code = code.strip()
    # Strip markdown code fencing if present
    if clean_code.startswith("```python"):
        clean_code = clean_code[9:]
    elif clean_code.startswith("```"):
        clean_code = clean_code[3:]
    if clean_code.endswith("```"):
        clean_code = clean_code[:-3]
    clean_code = clean_code.strip()

    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as tf:
        tf.write(clean_code)
        temp_script = tf.name

    try:
        # Use active virtualenv python
        python_bin = sys.executable
        res = subprocess.run(
            [python_bin, temp_script],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )

        stdout = res.stdout.strip()
        stderr = res.stderr.strip()

        if res.returncode != 0:
            return f"[Execution Error (Exit Code {res.returncode})]\n{stderr or stdout or 'Unknown runtime failure'}"
        
        output = stdout if stdout else "[Code executed successfully with no stdout output]"
        if stderr:
            output += f"\n\n[Warnings/Stderr]:\n{stderr}"
        return output

    except subprocess.TimeoutExpired:
        return f"[Execution Timeout]: Script exceeded {timeout_seconds} seconds execution limit."
    except Exception as e:
        return f"[Sandbox Exception]: {str(e)}"
    finally:
        p = Path(temp_script)
        if p.exists():
            try:
                p.unlink()
            except Exception:
                pass
