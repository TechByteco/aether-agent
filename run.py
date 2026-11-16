"""
Root Launcher for AETHER
Allows running AETHER directly via:
    python run.py
    uv run run.py
    .venv/Scripts/python run.py
without needing src/ on PYTHONPATH or package installation.
"""

import sys
from pathlib import Path

# Automatically add src directory to python search path
root_dir = Path(__file__).resolve().parent
src_dir = root_dir / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from aether.cli import run_cli

if __name__ == "__main__":
    run_cli()
