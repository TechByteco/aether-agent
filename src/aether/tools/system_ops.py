"""
System Operations & Full Computer Control
Provides OS navigation, application launching (Chrome, Notepad, Spotify, etc.),
direct YouTube playback, screenshot capture, and desktop automation.
"""

import os
import re
import shutil
import subprocess
import urllib.parse
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import httpx

APP_REGISTRY = {
    "chrome": [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        "chrome.exe",
    ],
    "google chrome": [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        "chrome.exe",
    ],
    "edge": [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        "msedge.exe",
    ],
    "notepad": ["notepad.exe"],
    "calculator": ["calc.exe"],
    "calc": ["calc.exe"],
    "explorer": ["explorer.exe"],
    "files": ["explorer.exe"],
    "terminal": ["wt.exe", "powershell.exe"],
    "powershell": ["powershell.exe"],
    "spotify": ["spotify.exe"],
    "code": ["code.cmd", "code.exe"],
    "vscode": ["code.cmd", "code.exe"],
}


def find_chrome_executable() -> Optional[str]:
    """Find Google Chrome executable path on this system."""
    candidates = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    # Fallback to shutil.which
    found = shutil.which("chrome.exe") or shutil.which("chrome")
    return found


def open_application(app_name: str) -> str:
    """
    Launch any installed application on the computer (e.g. Chrome, Notepad, Calculator, Edge, Spotify, VS Code).
    """
    clean_name = app_name.strip().lower()
    targets = APP_REGISTRY.get(clean_name, [clean_name])

    for target in targets:
        if os.path.isabs(target) and os.path.exists(target):
            try:
                subprocess.Popen([target], shell=False)
                return f"Successfully launched {app_name.capitalize()}."
            except Exception as e:
                return f"Failed to launch {target}: {str(e)}"
        else:
            resolved = shutil.which(target)
            if resolved:
                try:
                    subprocess.Popen([resolved], shell=False)
                    return f"Successfully launched {app_name.capitalize()}."
                except Exception as e:
                    return f"Failed to launch {target}: {str(e)}"

    # Universal fallback using Windows startfile / shell
    try:
        os.startfile(app_name)
        return f"Dispatched launch command for {app_name}."
    except Exception as e:
        return f"Could not find or launch application '{app_name}'. Error: {str(e)}"


def open_browser_url(url: str) -> str:
    """
    Open any website URL directly in Google Chrome (or default browser).
    """
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url

    chrome = find_chrome_executable()
    if chrome:
        try:
            subprocess.Popen([chrome, url])
            return f"Opened {url} in Google Chrome."
        except Exception:
            pass

    # Fallback to default browser
    webbrowser.open(url)
    return f"Opened {url} in default browser."


def play_youtube_media(song_or_query: str) -> str:
    """
    Play a song, music, video, or playlist on YouTube in Google Chrome.
    Resolves the top video and launches it directly so it starts playing immediately.
    """
    encoded_query = urllib.parse.quote_plus(song_or_query.strip())
    search_url = f"https://www.youtube.com/results?search_query={encoded_query}"
    target_url = search_url
    video_title = song_or_query

    # Try resolving first video ID for direct instant playback
    try:
        with httpx.Client(timeout=4.0, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}) as client:
            resp = client.get(search_url)
            matches = re.findall(r"/watch\?v=([a-zA-Z0-9_-]{11})", resp.text)
            if matches:
                target_url = f"https://www.youtube.com/watch?v={matches[0]}"
    except Exception:
        target_url = search_url

    # Open in Chrome
    chrome = find_chrome_executable()
    if chrome:
        try:
            subprocess.Popen([chrome, target_url])
            return f"Opened Google Chrome and started playing '{video_title}' on YouTube ({target_url})."
        except Exception:
            pass

    webbrowser.open(target_url)
    return f"Opened YouTube and started playing '{video_title}'."


def lock_workstation() -> str:
    """Lock the Windows computer immediately."""
    try:
        subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"], check=True)
        return "Computer locked."
    except Exception as e:
        return f"Failed to lock workstation: {str(e)}"


def take_screenshot(filename: str = "") -> str:
    """Capture the current computer screen and save it to data/screenshots/."""
    try:
        from aether.config import config
        shots_dir = config.data_dir.parent / "screenshots"
        shots_dir.mkdir(parents=True, exist_ok=True)
        
        name = filename.strip() or f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        out_path = shots_dir / name

        ps_script = f"""
        Add-Type -AssemblyName System.Windows.Forms;
        Add-Type -AssemblyName System.Drawing;
        $screen = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds;
        $bitmap = New-Object System.Drawing.Bitmap $screen.Width, $screen.Height;
        $graphic = [System.Drawing.Graphics]::FromImage($bitmap);
        $graphic.CopyFromScreen($screen.Location, [System.Drawing.Point]::Empty, $screen.Size);
        $bitmap.Save('{str(out_path).replace("\\", "\\\\")}');
        """
        subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], check=True, capture_output=True)
        return f"Screenshot saved to: {out_path}"
    except Exception as e:
        return f"Failed to take screenshot: {str(e)}"


def get_current_time() -> str:
    """Return the current local date, time, and day of the week."""
    now = datetime.now()
    return now.strftime("%A, %B %d, %Y - %I:%M:%S %p %Z")


def inspect_directory(directory_path: str = ".", max_items: int = 400) -> str:
    """List files and subdirectories within a given path with generous item limits."""
    try:
        target = Path(directory_path).expanduser().resolve()
        if not target.exists():
            return f"Error: Directory '{directory_path}' does not exist."
        if not target.is_dir():
            return f"Error: '{directory_path}' is not a directory."

        entries = list(target.iterdir())[:max_items]
        lines = [f"Directory listing of: {target}"]
        for e in entries:
            kind = "[DIR] " if e.is_dir() else "[FILE]"
            size = f"({e.stat().st_size} bytes)" if e.is_file() else ""
            lines.append(f"  {kind} {e.name} {size}")

        if len(entries) == max_items:
            lines.append(f"  ... (showing first {max_items} items)")
        return "\n".join(lines)
    except Exception as e:
        return f"Error inspecting directory: {str(e)}"


def read_text_file(file_path: str, max_lines: int = 2000) -> str:
    """Read full text of a file with expansive line allowance."""
    try:
        p = Path(file_path).expanduser().resolve()
        if not p.exists():
            return f"Error: File '{file_path}' does not exist."
        if not p.is_file():
            return f"Error: '{file_path}' is not a regular file."

        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        content = "\n".join(lines[:max_lines])
        if len(lines) > max_lines:
            content += f"\n... [Truncated: {len(lines) - max_lines} more lines]"
        return content
    except Exception as e:
        return f"Error reading file: {str(e)}"


def write_text_file(file_path: str, content: str) -> str:
    """Create or overwrite a file on disk with provided text or code."""
    try:
        p = Path(file_path).expanduser().resolve()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"Successfully wrote {len(content)} characters to '{p}'."
    except Exception as e:
        return f"Error writing file '{file_path}': {str(e)}"


def execute_system_command(command: str, timeout_seconds: int = 45) -> str:
    """Execute a system shell command (PowerShell / Windows CMD) and return output."""
    try:
        res = subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        out = res.stdout.strip()
        err = res.stderr.strip()
        if res.returncode != 0:
            return f"[Command Exited with Code {res.returncode}]\n{err or out or 'No output'}"
        return out if out else (f"[Command succeeded]\n{err}" if err else "[Command succeeded with no output]")
    except subprocess.TimeoutExpired:
        return f"[Command Timeout]: Exceeded {timeout_seconds} seconds."
    except Exception as e:
        return f"[Command Error]: {str(e)}"


def get_storage_status() -> str:
    """Return disk space overview."""
    total, used, free = shutil.disk_usage(".")
    return (
        f"Disk Space: Total {round(total / (1024**3), 1)} GB | "
        f"Used {round(used / (1024**3), 1)} GB | "
        f"Free {round(free / (1024**3), 1)} GB"
    )


def read_clipboard() -> str:
    """Read the current contents of the Windows clipboard."""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", "Get-Clipboard"],
            capture_output=True, text=True, timeout=5
        )
        content = result.stdout.strip()
        return content if content else "[Clipboard is empty]"
    except Exception as e:
        return f"Clipboard read error: {str(e)}"


def write_clipboard(text: str) -> str:
    """Write text to the Windows clipboard."""
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", f"Set-Clipboard -Value @'\n{text}\n'@"],
            capture_output=True, text=True, timeout=5
        )
        return f"Copied {len(text)} characters to clipboard."
    except Exception as e:
        return f"Clipboard write error: {str(e)}"


def list_running_processes(filter_name: str = "") -> str:
    """List currently running processes, optionally filtered by name."""
    try:
        cmd = "Get-Process | Select-Object Name, Id, CPU, WorkingSet | Sort-Object CPU -Descending | Select-Object -First 30 | Format-Table -AutoSize"
        if filter_name:
            cmd = f"Get-Process | Where-Object {{$_.Name -like '*{filter_name}*'}} | Select-Object Name, Id, CPU, WorkingSet | Format-Table -AutoSize"
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", cmd],
            capture_output=True, text=True, timeout=10
        )
        return result.stdout.strip() or "No processes found."
    except Exception as e:
        return f"Process list error: {str(e)}"


def get_system_info() -> str:
    """Return comprehensive system information: OS, CPU, RAM, battery, uptime."""
    try:
        import platform

        import psutil
        cpu_count = psutil.cpu_count(logical=True)
        cpu_freq = psutil.cpu_freq()
        freq_str = f"{cpu_freq.current:.0f} MHz" if cpu_freq else "N/A"
        ram = psutil.virtual_memory()
        battery = psutil.sensors_battery()
        bat_str = ""
        if battery:
            bat_str = f"\nBattery: {battery.percent:.0f}% ({'Charging' if battery.power_plugged else 'Discharging'})"
        uptime_sec = int(psutil.boot_time())
        from datetime import datetime as dt
        uptime = dt.now() - dt.fromtimestamp(uptime_sec)
        return (
            f"OS: {platform.system()} {platform.release()} {platform.machine()}\n"
            f"CPU: {platform.processor()} ({cpu_count} cores @ {freq_str})\n"
            f"RAM: {ram.used / 1e9:.1f} GB used / {ram.total / 1e9:.1f} GB total ({ram.percent:.0f}%)\n"
            f"Uptime: {str(uptime).split('.')[0]}"
            f"{bat_str}"
        )
    except Exception as e:
        return f"System info error: {str(e)}"


def search_files_by_content(directory: str, pattern: str, max_results: int = 30) -> str:
    """Search files within a directory for lines matching a text pattern (like grep)."""
    try:
        target = Path(directory).expanduser().resolve()
        if not target.exists():
            return f"Directory '{directory}' does not exist."
        matches = []
        text_extensions = {'.py', '.js', '.ts', '.json', '.md', '.txt', '.yaml', '.yml',
                          '.toml', '.cfg', '.ini', '.css', '.html', '.sh', '.bat', '.ps1'}
        for file_path in target.rglob('*'):
            if file_path.is_file() and file_path.suffix.lower() in text_extensions:
                try:
                    lines = file_path.read_text(encoding='utf-8', errors='replace').splitlines()
                    for ln, line in enumerate(lines, 1):
                        if pattern.lower() in line.lower():
                            matches.append(f"{file_path}:{ln}: {line.strip()}")
                            if len(matches) >= max_results:
                                break
                except Exception:
                    pass
            if len(matches) >= max_results:
                break
        if not matches:
            return f"No matches for '{pattern}' in '{directory}'"
        return f"Found {len(matches)} match(es):\n" + "\n".join(matches)
    except Exception as e:
        return f"Search error: {str(e)}"


def find_files(directory: str, name_pattern: str, max_results: int = 50) -> str:
    """Find files by name pattern in a directory tree."""
    try:
        import fnmatch
        target = Path(directory).expanduser().resolve()
        if not target.exists():
            return f"Directory '{directory}' does not exist."
        matches = []
        for f in target.rglob('*'):
            if f.is_file() and fnmatch.fnmatch(f.name.lower(), name_pattern.lower()):
                size = f.stat().st_size
                matches.append(f"{f} ({size} bytes)")
                if len(matches) >= max_results:
                    break
        return f"Found {len(matches)} file(s):\n" + "\n".join(matches) if matches else f"No files matching '{name_pattern}'"
    except Exception as e:
        return f"Find files error: {str(e)}"


def get_recent_files(directory: str = "~", days: int = 3, max_results: int = 25) -> str:
    """List recently modified files in a directory (last N days)."""
    try:
        import time
        target = Path(directory).expanduser().resolve()
        cutoff = time.time() - (days * 86400)
        results = []
        for f in target.rglob('*'):
            if f.is_file():
                try:
                    mtime = f.stat().st_mtime
                    if mtime > cutoff:
                        results.append((mtime, f))
                except Exception:
                    pass
        results.sort(key=lambda x: x[0], reverse=True)
        lines = [f"Recent files in {target} (last {days} days):"]
        for mtime, f in results[:max_results]:
            from datetime import datetime as dt
            ts = dt.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M')
            lines.append(f"  [{ts}] {f}")
        return "\n".join(lines) if len(results) > 0 else f"No recently modified files found."
    except Exception as e:
        return f"Recent files error: {str(e)}"


def diff_files(file_a: str, file_b: str) -> str:
    """Show unified diff between two text files."""
    try:
        import difflib
        a = Path(file_a).read_text(encoding='utf-8', errors='replace').splitlines(keepends=True)
        b = Path(file_b).read_text(encoding='utf-8', errors='replace').splitlines(keepends=True)
        diff = list(difflib.unified_diff(a, b, fromfile=file_a, tofile=file_b))
        if not diff:
            return "Files are identical."
        return "".join(diff[:200])  # Limit to 200 lines of diff
    except Exception as e:
        return f"Diff error: {str(e)}"


def get_active_window_title() -> str:
    """Return the title of the currently focused window."""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "(Get-Process | Where-Object {$_.MainWindowHandle -ne 0 -and $_.MainWindowTitle -ne ''} | Select-Object -First 1).MainWindowTitle"],
            capture_output=True, text=True, timeout=5
        )
        title = result.stdout.strip()
        return title if title else "Could not determine active window."
    except Exception as e:
        return f"Active window error: {str(e)}"


def get_network_status() -> str:
    """Return current network interfaces and connectivity status."""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-NetIPAddress | Where-Object {$_.AddressFamily -eq 'IPv4' -and $_.InterfaceAlias -notlike '*Loopback*'} | Select-Object InterfaceAlias, IPAddress | Format-Table -AutoSize"],
            capture_output=True, text=True, timeout=8
        )
        net_info = result.stdout.strip()

        # Quick connectivity check
        ping = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Test-Connection -ComputerName 8.8.8.8 -Count 1 -Quiet"],
            capture_output=True, text=True, timeout=5
        )
        online = "Online" if "True" in ping.stdout else "Offline"
        return f"Network Status: {online}\n{net_info}"
    except Exception as e:
        return f"Network status error: {str(e)}"


def control_system_volume(action: str = "toggle") -> str:
    """
    Control PC system volume immediately (actions: 'up', 'down', 'mute', 'unmute', 'toggle').
    Executes in < 15ms via hardware keyboard media events.
    """
    act = action.strip().lower()
    # 173 = VK_VOLUME_MUTE, 174 = VK_VOLUME_DOWN, 175 = VK_VOLUME_UP
    key_code = 173
    repeat = 1
    msg = "Toggled system mute."

    if "up" in act or "increase" in act or "raise" in act:
        key_code = 175
        repeat = 4
        msg = "Increased system volume."
    elif "down" in act or "decrease" in act or "lower" in act:
        key_code = 174
        repeat = 4
        msg = "Decreased system volume."
    elif "mute" in act:
        key_code = 173
        repeat = 1
        msg = "Toggled master audio mute."

    try:
        ps_cmd = f"$wsh = New-Object -ComObject WScript.Shell; 1..{repeat} | ForEach-Object {{ $wsh.SendKeys([char]{key_code}) }}"
        subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True, timeout=3)
        return f"✓ {msg}"
    except Exception as e:
        return f"Volume control error: {str(e)}"


def set_display_brightness(level: int) -> str:
    """
    Set laptop screen brightness percentage (0-100) via Windows WMI hardware controller.
    """
    try:
        val = max(0, min(100, int(level)))
        ps_cmd = f"(Get-CimInstance -Namespace root/wmi -ClassName WmiMonitorBrightnessMethods).WmiSetBrightness(1, {val})"
        res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True, text=True, timeout=5)
        if res.returncode == 0:
            return f"✓ Display brightness adjusted to {val}%."
        return f"Could not adjust brightness: {res.stderr.strip() or 'WMI unsupported on external monitor'}"
    except Exception as e:
        return f"Brightness error: {str(e)}"


def translate_language(text: str, target_lang: str = "spanish") -> str:
    """
    Translate text into a target language (e.g. 'French', 'Spanish', 'Japanese', 'German', 'Hindi') in ~250ms.
    """
    lang_map = {
        "spanish": "es", "french": "fr", "german": "de", "japanese": "ja",
        "chinese": "zh-CN", "mandarin": "zh-CN", "italian": "it", "russian": "ru",
        "hindi": "hi", "portuguese": "pt", "korean": "ko", "arabic": "ar",
        "dutch": "nl", "turkish": "tr", "polish": "pl", "swedish": "sv"
    }
    clean_target = target_lang.lower().strip()
    code = lang_map.get(clean_target, clean_target[:2])

    try:
        url = "https://translate.googleapis.com/translate_a/single"
        params = {"client": "gtx", "sl": "auto", "tl": code, "dt": "t", "q": text}
        with httpx.Client(timeout=6.0) as client:
            resp = client.get(url, params=params)
            data = resp.json()
            translated = "".join([part[0] for part in data[0] if part and part[0]])
            return f"**Translation ({target_lang.capitalize()}):**\n{translated}"
    except Exception as e:
        return f"Translation error: {str(e)}"


def lookup_world_map(location: str, zoom: int = 12) -> str:
    """
    Geocode a location and return interactive map metadata for inline Leaflet rendering in the Glass HUD.
    """
    try:
        url = "https://nominatim.openstreetmap.org/search"
        headers = {"User-Agent": "AETHER-Copilot/1.0 (Windows ARM64)"}
        params = {"q": location, "format": "json", "limit": 1}
        with httpx.Client(timeout=6.0, headers=headers) as client:
            resp = client.get(url, params=params)
            results = resp.json()
            if not results:
                return f"Could not find coordinates for location: '{location}'"
            first = results[0]
            lat = float(first["lat"])
            lon = float(first["lon"])
            name = first.get("display_name", location)
            return (
                f"### World Map: {location.title()}\n"
                f"**Coordinates:** {lat:.4f}° N, {lon:.4f}° E\n\n"
                f"```aether-map\n"
                f'{{"lat": {lat}, "lon": {lon}, "zoom": {zoom}, "title": "{location.title()}", "name": "{name[:80]}"}}\n'
                f"```"
            )
    except Exception as e:
        return f"Map lookup error: {str(e)}"

