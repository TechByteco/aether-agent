"""
AETHER Sovereign Desktop Vision & Application Automation Controller
===================================================================
Enables AETHER to see the computer display, control active applications,
perform UI interactions (mouse/keyboard), manage Windows services,
and execute multi-step automated tasks in a hybrid Edge-Cloud architecture.
"""

import ctypes
import json
import logging
import os
import re
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import psutil
from PIL import Image

from aether.config import config

logger = logging.getLogger("aether.tools.desktop_controller")

# Windows Virtual-Key Codes
VK_CODES = {
    "enter": 0x0D,
    "tab": 0x09,
    "space": 0x20,
    "backspace": 0x08,
    "esc": 0x1B,
    "escape": 0x1B,
    "ctrl": 0x11,
    "alt": 0x12,
    "shift": 0x10,
    "win": 0x5B,
    "up": 0x26,
    "down": 0x28,
    "left": 0x25,
    "right": 0x27,
    "delete": 0x2E,
    "f5": 0x74,
}

# Mouse event flags
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_WHEEL = 0x0800

# Known common Windows application shortcuts & URI schemes
KNOWN_APP_SCHEMES = {
    "chrome": ["chrome.exe", r"C:\Program Files\Google\Chrome\Application\chrome.exe", "https://google.com"],
    "google chrome": ["chrome.exe", r"C:\Program Files\Google\Chrome\Application\chrome.exe"],
    "edge": ["msedge.exe", r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"],
    "notepad": ["notepad.exe"],
    "calc": ["calc.exe"],
    "calculator": ["calc.exe"],
    "explorer": ["explorer.exe"],
    "file explorer": ["explorer.exe"],
    "terminal": ["wt.exe", "powershell.exe"],
    "powershell": ["powershell.exe"],
    "cmd": ["cmd.exe"],
    "code": ["code.cmd", "code.exe"],
    "vscode": ["code.cmd", "code.exe"],
    "spotify": ["spotify.exe", "spotify:"],
    "settings": ["ms-settings:"],
}


def tool_list_running_applications(filter_name: Optional[str] = None) -> Dict[str, Any]:
    """
    List currently running desktop applications and system processes with RAM, CPU, and PID.
    """
    apps = []
    filter_lower = filter_name.strip().lower() if filter_name else ""

    for p in psutil.process_iter(["pid", "name", "memory_info", "cpu_percent"]):
        try:
            name = p.info["name"]
            if not name:
                continue
            if filter_lower and filter_lower not in name.lower():
                continue

            mem_mb = round(p.info["memory_info"].rss / (1024 * 1024), 1)
            # Focus on notable GUI/system processes
            if mem_mb > 15.0 or filter_lower:
                apps.append({
                    "name": name,
                    "pid": p.info["pid"],
                    "memory_mb": mem_mb,
                    "cpu_percent": p.info["cpu_percent"] or 0.0,
                })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    apps_sorted = sorted(apps, key=lambda x: x["memory_mb"], reverse=True)
    return {
        "status": "success",
        "total_active_apps": len(apps_sorted),
        "applications": apps_sorted[:40],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def tool_launch_or_focus_app(app_name: str, args: Optional[str] = None) -> Dict[str, Any]:
    """
    Launch or focus any Windows application, system tool, or URI.
    Supports Chrome, VSCode, Terminal, Spotify, Explorer, Notepad, Settings, etc.
    """
    clean = app_name.strip().lower()
    targets = KNOWN_APP_SCHEMES.get(clean, [clean])

    # Check if process is already running
    matching_pid = None
    for p in psutil.process_iter(["pid", "name"]):
        try:
            if clean in p.info["name"].lower():
                matching_pid = p.info["pid"]
                break
        except Exception:
            pass

    # Launch or switch
    launched = False
    details = ""
    for t in targets:
        # Check absolute path
        if os.path.exists(t):
            cmd = [t] + ([args] if args else [])
            subprocess.Popen(cmd, shell=False)
            launched = True
            details = f"Launched absolute path: {t}"
            break
        # Check PATH
        which = shutil.which(t)
        if which:
            cmd = [which] + ([args] if args else [])
            subprocess.Popen(cmd, shell=False)
            launched = True
            details = f"Launched executable via PATH: {which}"
            break
        # Check URI scheme or generic startfile
        if ":" in t or t.endswith(".exe"):
            try:
                os.startfile(t)
                launched = True
                details = f"Launched via Windows startfile: {t}"
                break
            except Exception:
                pass

    # Generic Windows Shell fallback
    if not launched:
        try:
            if args:
                os.startfile(app_name)
            else:
                subprocess.Popen(f"start {app_name}", shell=True)
            launched = True
            details = f"Dispatched Windows shell start command for '{app_name}'"
        except Exception as e:
            return {
                "status": "error",
                "message": f"Could not launch application '{app_name}': {str(e)}",
            }

    return {
        "status": "success",
        "app_name": app_name,
        "already_running": matching_pid is not None,
        "pid": matching_pid,
        "details": details,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def tool_manage_windows_service(service_name: str, action: str = "status") -> Dict[str, Any]:
    """
    Query or manage Windows background services (action: 'status', 'start', 'stop', 'restart').
    """
    action_clean = action.strip().lower()
    try:
        if action_clean == "status":
            res = subprocess.run(["sc.exe", "query", service_name], capture_output=True, text=True)
            return {
                "status": "success",
                "service": service_name,
                "output": res.stdout.strip() or res.stderr.strip(),
            }
        elif action_clean in ("start", "stop"):
            cmd = ["net", action_clean, service_name]
            res = subprocess.run(cmd, capture_output=True, text=True)
            return {
                "status": "success" if res.returncode == 0 else "failed",
                "service": service_name,
                "action": action_clean,
                "output": res.stdout.strip() or res.stderr.strip(),
            }
        elif action_clean == "restart":
            subprocess.run(["net", "stop", service_name], capture_output=True)
            time.sleep(1.0)
            res = subprocess.run(["net", "start", service_name], capture_output=True, text=True)
            return {
                "status": "success" if res.returncode == 0 else "failed",
                "service": service_name,
                "action": "restart",
                "output": res.stdout.strip() or res.stderr.strip(),
            }
        else:
            return {"status": "error", "message": f"Unsupported action '{action}'. Use status, start, stop, or restart."}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def tool_capture_desktop_display(output_filename: Optional[str] = None) -> Dict[str, Any]:
    """
    Capture the current computer display, extract dimensions, and save to screenshots repository.
    """
    shots_dir = config.data_dir.parent / "screenshots"
    shots_dir.mkdir(parents=True, exist_ok=True)

    fname = output_filename or f"screen_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
    raw_path = shots_dir / f"_raw_{fname}.png"
    target_path = shots_dir / fname

    ps_script = f"""
    Add-Type -AssemblyName System.Windows.Forms;
    Add-Type -AssemblyName System.Drawing;
    $screen = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds;
    $bitmap = New-Object System.Drawing.Bitmap $screen.Width, $screen.Height;
    $graphic = [System.Drawing.Graphics]::FromImage($bitmap);
    $graphic.CopyFromScreen($screen.Location, [System.Drawing.Point]::Empty, $screen.Size);
    $bitmap.Save('{str(raw_path).replace("\\", "\\\\")}');
    $graphic.Dispose();
    $bitmap.Dispose();
    """
    subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], check=True, capture_output=True)

    # Process and measure dimensions
    width, height = 1920, 1080
    if raw_path.exists():
        with Image.open(raw_path) as img:
            width, height = img.size
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            img.save(target_path, "JPEG", quality=90, optimize=True)
        raw_path.unlink(missing_ok=True)

    return {
        "status": "success",
        "image_path": str(target_path),
        "resolution": f"{width}x{height}",
        "width": width,
        "height": height,
        "file_size_kb": round(target_path.stat().st_size / 1024, 1),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def tool_interact_ui(
    action: str,
    x: Optional[int] = None,
    y: Optional[int] = None,
    text: Optional[str] = None,
    key_combo: Optional[str] = None,
    scroll_amount: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Execute hardware mouse and keyboard interactions directly on the Windows desktop.

    Actions:
      - 'click': Left-click at (x, y)
      - 'double_click': Double left-click at (x, y)
      - 'right_click': Right-click at (x, y)
      - 'move': Move mouse cursor to (x, y)
      - 'type': Type text string with keystrokes
      - 'hotkey': Send key combination (e.g. 'ctrl+c', 'alt+tab', 'enter', 'win+d')
      - 'scroll': Scroll mouse wheel vertically
    """
    act = action.strip().lower()

    if act in ("click", "double_click", "right_click", "move"):
        if x is None or y is None:
            return {"status": "error", "message": "x and y coordinates are required for mouse actions."}

        # Set cursor
        ctypes.windll.user32.SetCursorPos(int(x), int(y))
        time.sleep(0.05)

        if act == "click":
            ctypes.windll.user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            time.sleep(0.02)
            ctypes.windll.user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        elif act == "double_click":
            for _ in range(2):
                ctypes.windll.user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                time.sleep(0.02)
                ctypes.windll.user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                time.sleep(0.05)
        elif act == "right_click":
            ctypes.windll.user32.mouse_event(MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
            time.sleep(0.02)
            ctypes.windll.user32.mouse_event(MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)

        return {
            "status": "success",
            "action": act,
            "target": {"x": x, "y": y},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    elif act == "type":
        if not text:
            return {"status": "error", "message": "text argument required for 'type' action."}

        # Send via PowerShell SendKeys for Unicode and multi-line support
        escaped = text.replace("{", "{{").replace("}", "}}")
        ps_cmd = f"""
        Add-Type -AssemblyName System.Windows.Forms;
        [System.Windows.Forms.SendKeys]::SendWait('{escaped}');
        """
        subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], check=False)
        return {
            "status": "success",
            "action": "type",
            "typed_chars": len(text),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    elif act == "hotkey":
        if not key_combo:
            return {"status": "error", "message": "key_combo argument required for 'hotkey' action (e.g. 'enter', 'ctrl+c')."}

        keys = [k.strip().lower() for k in key_combo.split("+")]
        # Map to SendKeys format
        send_keys_map = {
            "ctrl": "^",
            "alt": "%",
            "shift": "+",
            "enter": "{ENTER}",
            "esc": "{ESC}",
            "tab": "{TAB}",
            "backspace": "{BACKSPACE}",
            "delete": "{DELETE}",
            "win": "^{ESC}",  # Windows menu fallback
            "f5": "{F5}",
        }

        combo_str = ""
        for k in keys:
            if k in send_keys_map:
                combo_str += send_keys_map[k]
            else:
                combo_str += k.upper() if len(k) == 1 else f"{{{k.upper()}}}"

        ps_cmd = f"""
        Add-Type -AssemblyName System.Windows.Forms;
        [System.Windows.Forms.SendKeys]::SendWait('{combo_str}');
        """
        subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], check=False)
        return {
            "status": "success",
            "action": "hotkey",
            "combo": key_combo,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    elif act == "scroll":
        amt = scroll_amount or -120  # default scroll down
        ctypes.windll.user32.mouse_event(MOUSEEVENTF_WHEEL, 0, 0, int(amt), 0)
        return {
            "status": "success",
            "action": "scroll",
            "amount": amt,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    return {"status": "error", "message": f"Unknown action '{action}'."}


def tool_see_screen_and_analyze(prompt: str = "Identify active windows, main open applications, and prominent text.") -> Dict[str, Any]:
    """
    Capture the screen, inspect active applications, and perform multimodal visual analysis.
    """
    cap = tool_capture_desktop_display()
    img_path = cap.get("image_path")

    # Inspect top running processes
    app_summary = tool_list_running_applications()
    top_apps = [a["name"] for a in app_summary.get("applications", [])[:6]]

    analysis_text = f"Screen captured at {cap.get('resolution')}. Active key apps on system: {', '.join(top_apps)}."

    # Try local vision model
    try:
        from aether.tools.vision import analyze_image
        vis_res = analyze_image(img_path, prompt=prompt)
        if vis_res and "No visual details" not in vis_res:
            analysis_text += f"\n\nVisual Inspection:\n{vis_res}"
    except Exception as e:
        logger.debug(f"Vision analysis fallback: {e}")

    return {
        "status": "success",
        "image_path": img_path,
        "resolution": cap.get("resolution"),
        "active_applications": top_apps,
        "visual_summary": analysis_text,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
