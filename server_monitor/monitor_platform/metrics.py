from __future__ import annotations

import os
import platform
import shutil
import socket
import time
from pathlib import Path
from typing import Any

from .config import Settings


def _read_text(root: str, relative: str) -> str:
    return Path(root, relative).read_text(encoding="utf-8")


def _read_cpu_times(proc_root: str) -> tuple[int, int]:
    line = _read_text(proc_root, "stat").splitlines()[0]
    values = [int(value) for value in line.split()[1:]]
    idle = values[3] + (values[4] if len(values) > 4 else 0)
    return sum(values), idle


def cpu_usage_percent(proc_root: str, interval_seconds: float = 0.12) -> float:
    try:
        first_total, first_idle = _read_cpu_times(proc_root)
    except OSError:
        return 0.0
    time.sleep(max(0.0, interval_seconds))
    try:
        second_total, second_idle = _read_cpu_times(proc_root)
    except OSError:
        return 0.0
    total_delta = second_total - first_total
    idle_delta = second_idle - first_idle
    if total_delta <= 0:
        return 0.0
    return round(max(0.0, min(100.0, (1 - idle_delta / total_delta) * 100)), 1)


def parse_meminfo(text: str) -> dict[str, int]:
    data: dict[str, int] = {}
    for line in text.splitlines():
        if ":" not in line:
            continue
        key, raw_value = line.split(":", 1)
        parts = raw_value.strip().split()
        if not parts:
            continue
        data[key] = int(parts[0]) * 1024
    return data


def memory_snapshot(proc_root: str) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        meminfo = parse_meminfo(_read_text(proc_root, "meminfo"))
    except OSError:
        total = fallback_total_memory()
        return (
            {"total": total, "available": 0, "used": 0, "percent": 0.0},
            {"total": 0, "free": 0, "used": 0, "percent": 0.0},
        )
    total = meminfo.get("MemTotal", 0)
    available = meminfo.get("MemAvailable", meminfo.get("MemFree", 0))
    used = max(0, total - available)
    percent = round((used / total * 100) if total else 0.0, 1)

    swap_total = meminfo.get("SwapTotal", 0)
    swap_free = meminfo.get("SwapFree", 0)
    swap_used = max(0, swap_total - swap_free)
    swap_percent = round((swap_used / swap_total * 100) if swap_total else 0.0, 1)

    return (
        {"total": total, "available": available, "used": used, "percent": percent},
        {"total": swap_total, "free": swap_free, "used": swap_used, "percent": swap_percent},
    )


def fallback_total_memory() -> int:
    try:
        return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
    except (AttributeError, OSError, ValueError):
        return 0


def load_average(proc_root: str) -> dict[str, float]:
    try:
        raw = _read_text(proc_root, "loadavg").split()
        return {"one": float(raw[0]), "five": float(raw[1]), "fifteen": float(raw[2])}
    except (OSError, ValueError, IndexError):
        one, five, fifteen = os.getloadavg()
        return {"one": round(one, 2), "five": round(five, 2), "fifteen": round(fifteen, 2)}


def uptime_seconds(proc_root: str) -> float:
    try:
        return round(float(_read_text(proc_root, "uptime").split()[0]), 2)
    except (OSError, ValueError, IndexError):
        return 0.0


def process_count(proc_root: str) -> int:
    try:
        return sum(1 for item in Path(proc_root).iterdir() if item.name.isdigit())
    except OSError:
        return 0


def disk_snapshot(paths: tuple[str, ...]) -> list[dict[str, Any]]:
    disks: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw_path in paths:
        path = str(Path(raw_path))
        if path in seen or not Path(path).exists():
            continue
        seen.add(path)
        usage = shutil.disk_usage(path)
        percent = round((usage.used / usage.total * 100) if usage.total else 0.0, 1)
        label = "/" if path == "/host/root" else path
        disks.append(
            {
                "path": path,
                "label": label,
                "total": usage.total,
                "used": usage.used,
                "free": usage.free,
                "percent": percent,
            }
        )
    return disks


def parse_net_dev(text: str) -> list[dict[str, Any]]:
    interfaces: list[dict[str, Any]] = []
    for line in text.splitlines()[2:]:
        if ":" not in line:
            continue
        name, payload = line.split(":", 1)
        values = payload.split()
        if len(values) < 16:
            continue
        interfaces.append(
            {
                "interface": name.strip(),
                "rx_bytes": int(values[0]),
                "rx_packets": int(values[1]),
                "rx_errors": int(values[2]),
                "tx_bytes": int(values[8]),
                "tx_packets": int(values[9]),
                "tx_errors": int(values[10]),
            }
        )
    return interfaces


def network_snapshot(proc_root: str) -> list[dict[str, Any]]:
    try:
        return parse_net_dev(_read_text(proc_root, "net/dev"))
    except OSError:
        return []


def collect_system_snapshot(settings: Settings) -> dict[str, Any]:
    memory, swap = memory_snapshot(settings.proc_root)
    return {
        "timestamp": time.time(),
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "uptime_seconds": uptime_seconds(settings.proc_root),
        "process_count": process_count(settings.proc_root),
        "cpu": {
            "usage_percent": cpu_usage_percent(settings.proc_root, settings.sample_interval_seconds),
            "cores": os.cpu_count() or 1,
            "load_average": load_average(settings.proc_root),
        },
        "memory": memory,
        "swap": swap,
        "disk": disk_snapshot(settings.disk_paths),
        "network": network_snapshot(settings.proc_root),
    }
