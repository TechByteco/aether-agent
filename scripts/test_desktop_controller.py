import ctypes
import win32gui
import win32process
import psutil
from PIL import ImageGrab

print("Enumerating active windows on system...")

windows = []
def enum_handler(hwnd, extra):
    if win32gui.IsWindowVisible(hwnd):
        title = win32gui.GetWindowText(hwnd).strip()
        if title:
            rect = win32gui.GetWindowRect(hwnd)
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            try:
                pname = psutil.Process(pid).name()
            except Exception:
                pname = "unknown"
            if rect[2] - rect[0] > 10 and rect[3] - rect[1] > 10:
                windows.append({"hwnd": hwnd, "title": title, "process": pname, "rect": rect})

win32gui.EnumWindows(enum_handler, None)
print(f"Total active visible windows found: {len(windows)}")
for w in windows[:10]:
    print(f" - [{w['process']}] '{w['title']}' at {w['rect']}")
