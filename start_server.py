"""
AETHER Sovereign Server & 24/7 Cloud Assistant Launcher
========================================================
Bootstraps PYTHONPATH and starts Uvicorn with the complete AutonomousOperator,
Telegram Polling Daemon, Calendar & Task Reminders, and Multi-Venture OS.
"""

import os
import sys
from pathlib import Path
import uvicorn

root_dir = Path(__file__).resolve().parent
src_dir = root_dir / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "0.0.0.0")
    print(f"Starting AETHER Sovereign Server on http://{host}:{port}")
    uvicorn.run("aether.web.server:app", host=host, port=port, log_level="info")

