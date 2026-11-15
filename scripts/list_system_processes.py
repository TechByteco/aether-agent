"""
System Process Inspector for AETHER
"""
import sys
import psutil
from datetime import datetime

# Enforce UTF-8 output on Windows
sys.stdout.reconfigure(encoding='utf-8')

def inspect_processes():
    vitals = psutil.virtual_memory()
    cpu_pct = psutil.cpu_percent(interval=0.3)
    battery = psutil.sensors_battery()
    
    print("=" * 80)
    print("AETHER SYSTEM & PROCESS TELEMETRY")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')}")
    print(f"RAM Usage: {vitals.used / (1024**3):.2f} GB / {vitals.total / (1024**3):.2f} GB ({vitals.percent}%) | Free: {vitals.available / (1024**3):.2f} GB")
    print(f"CPU Load:  {cpu_pct}% (Qualcomm Snapdragon X Oryon 8-Core ARM64)")
    if battery:
        plugged_str = "Plugged in" if battery.power_plugged else "On Battery"
        print(f"Battery:   {battery.percent}% ({plugged_str})")
    print("=" * 80)

    procs = []
    for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info', 'status']):
        try:
            mem_mb = (p.info['memory_info'].rss / (1024 * 1024)) if p.info['memory_info'] else 0.0
            procs.append({
                'pid': p.info['pid'],
                'name': p.info['name'],
                'cpu': p.info['cpu_percent'] or 0.0,
                'mem_mb': mem_mb,
                'status': p.info['status']
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    # Top by Memory
    top_mem = sorted(procs, key=lambda x: x['mem_mb'], reverse=True)[:18]

    print(f"{'PID':<8} | {'Process Name':<34} | {'Memory (MB)':<12} | {'Status':<10}")
    print("-" * 80)
    for p in top_mem:
        print(f"{p['pid']:<8} | {p['name']:<34} | {p['mem_mb']:>9.1f} MB | {p['status']}")
    print("=" * 80)

if __name__ == "__main__":
    inspect_processes()
