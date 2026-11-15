import ctypes
import psutil

class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

pt = POINT()
ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
print(f"Current Cursor Position: ({pt.x}, {pt.y})")

width = ctypes.windll.user32.GetSystemMetrics(0)
height = ctypes.windll.user32.GetSystemMetrics(1)
print(f"Screen Dimensions: {width} x {height}")

apps = []
for p in psutil.process_iter(["pid", "name", "memory_info"]):
    try:
        name = p.info["name"]
        mem = p.info["memory_info"].rss / (1024 * 1024)
        if mem > 50.0:  # processes using >50MB RAM
            apps.append({"name": name, "pid": p.info["pid"], "mem_mb": mem})
    except Exception:
        pass

print(f"Active Major Apps/Services ({len(apps)} found):")
for a in sorted(apps, key=lambda x: x["mem_mb"], reverse=True)[:10]:
    print(f" - {a['name']} (PID: {a['pid']}, RAM: {a['mem_mb']:.1f} MB)")
