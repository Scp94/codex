from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


def _default_existing_path(preferred: str, fallback: str) -> str:
    return preferred if Path(preferred).exists() else fallback


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    app_name: str = "Server Monitor"
    proc_root: str = os.getenv("MONITOR_PROC_ROOT", _default_existing_path("/host/proc", "/proc"))
    sys_root: str = os.getenv("MONITOR_SYS_ROOT", _default_existing_path("/host/sys", "/sys"))
    docker_socket: str = os.getenv("DOCKER_SOCKET", "/var/run/docker.sock")
    disk_paths: tuple[str, ...] = tuple(
        item.strip()
        for item in os.getenv("MONITOR_DISK_PATHS", _default_existing_path("/host/root", "/")).split(",")
        if item.strip()
    )
    api_token: Optional[str] = os.getenv("MONITOR_API_TOKEN") or None
    read_only: bool = _env_bool("MONITOR_READ_ONLY", False)
    sample_interval_seconds: float = float(os.getenv("MONITOR_SAMPLE_INTERVAL", "0.12"))


settings = Settings()
