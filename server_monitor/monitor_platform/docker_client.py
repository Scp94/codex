from __future__ import annotations

import http.client
import json
import socket
import urllib.parse
from dataclasses import dataclass
from typing import Any


class DockerAPIError(RuntimeError):
    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.message = message


class DockerUnavailableError(RuntimeError):
    pass


class UnixSocketHTTPConnection(http.client.HTTPConnection):
    def __init__(self, socket_path: str, timeout: float = 5.0):
        super().__init__("localhost", timeout=timeout)
        self.socket_path = socket_path

    def connect(self) -> None:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        sock.connect(self.socket_path)
        self.sock = sock


@dataclass
class DockerClient:
    socket_path: str = "/var/run/docker.sock"
    timeout: float = 5.0

    def _request(
        self,
        method: str,
        path: str,
        *,
        query: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
    ) -> Any:
        if query:
            encoded = urllib.parse.urlencode({key: value for key, value in query.items() if value is not None})
            path = f"{path}?{encoded}"

        payload = json.dumps(body).encode("utf-8") if body is not None else None
        headers = {"Host": "docker", "Content-Type": "application/json"}
        connection = UnixSocketHTTPConnection(self.socket_path, timeout=self.timeout)
        try:
            connection.request(method, path, body=payload, headers=headers)
            response = connection.getresponse()
            raw = response.read()
        except OSError as exc:
            raise DockerUnavailableError(f"Cannot connect to Docker socket {self.socket_path}: {exc}") from exc
        finally:
            connection.close()

        text = raw.decode("utf-8", errors="replace")
        if response.status >= 400:
            message = text
            try:
                message = json.loads(text).get("message", text)
            except json.JSONDecodeError:
                pass
            raise DockerAPIError(response.status, message)

        if not text:
            return None
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text

    def ping(self) -> bool:
        return self._request("GET", "/_ping") == "OK"

    def version(self) -> dict[str, Any]:
        return self._request("GET", "/version")

    def list_containers(self) -> list[dict[str, Any]]:
        containers = self._request("GET", "/containers/json", query={"all": 1})
        return [normalize_container(item) for item in containers]

    def inspect_container(self, container_id: str) -> dict[str, Any]:
        return self._request("GET", f"/containers/{urllib.parse.quote(container_id, safe='')}/json")

    def container_stats(self, container_id: str) -> dict[str, Any]:
        stats = self._request(
            "GET",
            f"/containers/{urllib.parse.quote(container_id, safe='')}/stats",
            query={"stream": "false", "one-shot": "true"},
        )
        return normalize_stats(stats)

    def run_action(self, container_id: str, action: str, options: dict[str, Any] | None = None) -> dict[str, Any]:
        options = options or {}
        safe_id = urllib.parse.quote(container_id, safe="")
        if action == "start":
            self._request("POST", f"/containers/{safe_id}/start")
        elif action == "stop":
            self._request("POST", f"/containers/{safe_id}/stop", query={"t": options.get("timeout", 10)})
        elif action == "restart":
            self._request("POST", f"/containers/{safe_id}/restart", query={"t": options.get("timeout", 10)})
        elif action == "pause":
            self._request("POST", f"/containers/{safe_id}/pause")
        elif action == "unpause":
            self._request("POST", f"/containers/{safe_id}/unpause")
        elif action == "kill":
            self._request("POST", f"/containers/{safe_id}/kill", query={"signal": options.get("signal")})
        elif action == "remove":
            self._request(
                "DELETE",
                f"/containers/{safe_id}",
                query={"force": str(bool(options.get("force", False))).lower(), "v": "false"},
            )
        else:
            raise DockerAPIError(400, f"Unsupported Docker action: {action}")
        return {"container_id": container_id, "action": action, "ok": True}


def normalize_container(item: dict[str, Any]) -> dict[str, Any]:
    names = [name.lstrip("/") for name in item.get("Names", [])]
    labels = item.get("Labels") or {}
    ports = []
    for port in item.get("Ports") or []:
        private_port = port.get("PrivatePort")
        public_port = port.get("PublicPort")
        port_type = port.get("Type", "tcp")
        if public_port:
            ports.append(f"{public_port}:{private_port}/{port_type}")
        elif private_port:
            ports.append(f"{private_port}/{port_type}")
    return {
        "id": item.get("Id", ""),
        "short_id": item.get("Id", "")[:12],
        "name": names[0] if names else item.get("Id", "")[:12],
        "names": names,
        "image": item.get("Image", ""),
        "image_id": item.get("ImageID", ""),
        "command": item.get("Command", ""),
        "created": item.get("Created", 0),
        "state": item.get("State", "unknown"),
        "status": item.get("Status", ""),
        "ports": ports,
        "compose_project": labels.get("com.docker.compose.project"),
        "compose_service": labels.get("com.docker.compose.service"),
        "labels": labels,
    }


def normalize_stats(stats: dict[str, Any]) -> dict[str, Any]:
    memory_stats = stats.get("memory_stats") or {}
    cpu_stats = stats.get("cpu_stats") or {}
    precpu_stats = stats.get("precpu_stats") or {}
    networks = stats.get("networks") or {}
    blkio = stats.get("blkio_stats", {}).get("io_service_bytes_recursive") or []

    cpu_total = cpu_stats.get("cpu_usage", {}).get("total_usage", 0)
    precpu_total = precpu_stats.get("cpu_usage", {}).get("total_usage", 0)
    system_total = cpu_stats.get("system_cpu_usage", 0)
    presystem_total = precpu_stats.get("system_cpu_usage", 0)
    online_cpus = cpu_stats.get("online_cpus") or len(cpu_stats.get("cpu_usage", {}).get("percpu_usage") or []) or 1
    cpu_delta = cpu_total - precpu_total
    system_delta = system_total - presystem_total
    cpu_percent = 0.0
    if cpu_delta > 0 and system_delta > 0:
        cpu_percent = round((cpu_delta / system_delta) * online_cpus * 100, 2)

    memory_usage = memory_stats.get("usage", 0) - memory_stats.get("stats", {}).get("cache", 0)
    memory_limit = memory_stats.get("limit", 0)
    memory_percent = round((memory_usage / memory_limit * 100) if memory_limit else 0.0, 2)

    network_rx = sum(item.get("rx_bytes", 0) for item in networks.values())
    network_tx = sum(item.get("tx_bytes", 0) for item in networks.values())
    block_read = sum(item.get("value", 0) for item in blkio if item.get("op", "").lower() == "read")
    block_write = sum(item.get("value", 0) for item in blkio if item.get("op", "").lower() == "write")

    return {
        "read_at": stats.get("read"),
        "cpu_percent": cpu_percent,
        "memory": {
            "usage": max(0, memory_usage),
            "limit": memory_limit,
            "percent": memory_percent,
        },
        "network": {"rx_bytes": network_rx, "tx_bytes": network_tx},
        "block_io": {"read_bytes": block_read, "write_bytes": block_write},
    }

