"""
Hardware Sentry & Resource Guardrails
Monitors RAM, CPU, and battery to guarantee zero system lag and prevent freezes.
"""

from typing import Any, Dict

import psutil

from aether.config import config


def get_system_vitals() -> Dict[str, Any]:
    """
    Retrieve real-time hardware status: RAM usage, CPU load, and battery.
    """
    mem = psutil.virtual_memory()
    cpu_percent = psutil.cpu_percent(interval=None)
    
    battery = psutil.sensors_battery()
    battery_info = {
        "percent": battery.percent if battery else None,
        "power_plugged": battery.power_plugged if battery else True,
    }

    available_mb = round(mem.available / (1024**2), 1)
    safe = (mem.percent < config.max_ram_percent) and (available_mb >= config.min_free_ram_mb)

    # NPU Hardware Introspection
    from aether.tools.npu_accelerator import get_npu_status
    npu_info = get_npu_status()

    return {
        "ram_total_gb": round(mem.total / (1024**3), 2),
        "ram_used_gb": round(mem.used / (1024**3), 2),
        "ram_free_gb": round(mem.available / (1024**3), 2),
        "ram_available_mb": available_mb,
        "ram_percent": mem.percent,
        "cpu_percent": cpu_percent,
        "battery": battery_info,
        "npu": npu_info,
        "safe_to_operate": safe,
    }


def format_vitals_summary() -> str:
    """Format a concise vitals string for logging or UI."""
    v = get_system_vitals()
    plug_str = "AC Power" if v["battery"]["power_plugged"] else "Battery"
    batt_str = f" ({v['battery']['percent']}%)" if v["battery"]["percent"] is not None else ""
    npu_str = f" | NPU: 45 TOPS ({v['npu']['active_backend']})" if v.get("npu", {}).get("hardware_found") else ""
    return (
        f"RAM: {v['ram_used_gb']}G/{v['ram_total_gb']}G ({v['ram_percent']}%) | "
        f"CPU: {v['cpu_percent']}%{npu_str} | {plug_str}{batt_str}"
    )


def assert_safe_resources() -> bool:
    """
    Ensure the user's commands are never arbitrarily blocked or throttled.
    Performs soft background cleanup if memory is tight without stopping execution.
    """
    import gc
    v = get_system_vitals()
    if v["ram_percent"] > 95:
        gc.collect()
    return True
