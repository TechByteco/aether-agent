"""
AETHER Sovereign Online Tunnel Background Daemon
Spawns and continuously monitors a zero-cost public HTTPS tunnel (Serveo / Localtunnel / Pinggy)
and persists live connectivity state and public URL to data/online_tunnel.json.
"""

import os
import sys
import time
import json
import re
import shutil
import subprocess
import threading
from pathlib import Path

STATE_FILE = Path(__file__).resolve().parent.parent / "data" / "online_tunnel.json"
STATE_FILE.parent.mkdir(parents=True, exist_ok=True)


def update_state(data: dict):
    try:
        STATE_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
        sys.stdout.flush()
    except Exception as e:
        print(f"Failed to write state: {e}")


def run_tunnel(port: int = 8000):
    flags = 0x08000000 | 0x00000200 if sys.platform == "win32" else 0

    npx_bin = shutil.which("npx.cmd") or shutil.which("npx") or r"C:\Program Files\nodejs\npx.cmd"

    providers = [
        ("serveo", ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "ServerAliveInterval=30", "-R", f"80:localhost:{port}", "serveo.net"], r'https://[a-zA-Z0-9.\-_]+(?:\.serveousercontent\.com|\.serveo\.net)', False),
        ("localtunnel", f'"{npx_bin}" --yes localtunnel --port {port}', r'https://[a-zA-Z0-9.\-_]+loca\.lt', True),
        ("pinggy", ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "ServerAliveInterval=30", "-p", "443", f"-R0:localhost:{port}", "a.pinggy.io"], r'https://[a-zA-Z0-9.\-_]+\.pinggy\.(?:link|io)', False),
    ]

    for name, cmd, pattern, use_shell in providers:
        print(f"[AETHER Tunnel] Attempting provider: {name}...", flush=True)
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                creationflags=flags,
                shell=use_shell,
            )

            url_found = []

            def _reader():
                try:
                    for line in iter(proc.stdout.readline, ''):
                        if not line:
                            break
                        m = re.search(pattern, line)
                        if m:
                            url_found.append(m.group(0))
                            break
                except Exception:
                    pass

            t = threading.Thread(target=_reader, daemon=True)
            t.start()
            t.join(timeout=8.0)

            if url_found and proc.poll() is None:
                public_url = url_found[0]
                print(f"[AETHER Tunnel] Online via {name.upper()}: {public_url}", flush=True)
                state = {
                    "active": True,
                    "provider": name,
                    "url": public_url,
                    "port": port,
                    "pid": proc.pid,
                    "started_at": time.time(),
                    "updated_at": time.time(),
                }
                update_state(state)

                # Keep running and update state every 10 seconds
                while proc.poll() is None:
                    time.sleep(10)
                    state["updated_at"] = time.time()
                    update_state(state)

                print(f"[AETHER Tunnel] Process exited with code {proc.poll()}", flush=True)

        except Exception as e:
            print(f"[AETHER Tunnel] Error on {name}: {e}", flush=True)
            continue

    update_state({"active": False, "provider": None, "url": None, "port": port})


if __name__ == "__main__":
    port_arg = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    run_tunnel(port_arg)
