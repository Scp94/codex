from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .config import settings
from .docker_client import DockerAPIError, DockerClient, DockerUnavailableError
from .metrics import collect_system_snapshot


STATIC_DIR = Path(__file__).parent / "static"


class DockerActionPayload(BaseModel):
    timeout: Optional[int] = 10
    signal: Optional[str] = None
    force: bool = False


def require_auth(authorization: Optional[str] = Header(default=None)) -> None:
    if not settings.api_token:
        return
    expected = f"Bearer {settings.api_token}"
    if authorization != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing API token")


def docker_client() -> DockerClient:
    return DockerClient(settings.docker_socket)


app = FastAPI(title="Server Monitor", version="0.1.0")
api = APIRouter(prefix="/api", dependencies=[Depends(require_auth)])


@app.exception_handler(DockerAPIError)
async def handle_docker_api_error(_: Request, exc: DockerAPIError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


@app.exception_handler(DockerUnavailableError)
async def handle_docker_unavailable(_: Request, exc: DockerUnavailableError) -> JSONResponse:
    return JSONResponse(status_code=503, content={"detail": str(exc)})


@app.get("/health")
async def health() -> dict[str, Any]:
    docker = docker_client()
    docker_ok = False
    docker_version: Optional[dict[str, Any]] = None
    try:
        docker_ok = docker.ping()
        docker_version = docker.version()
    except (DockerUnavailableError, DockerAPIError):
        docker_ok = False
    return {
        "ok": True,
        "docker": docker_ok,
        "docker_version": docker_version,
        "read_only": settings.read_only,
    }


@api.get("/metrics")
async def metrics() -> dict[str, Any]:
    return collect_system_snapshot(settings)


@api.get("/docker/containers")
async def containers() -> list[dict[str, Any]]:
    return docker_client().list_containers()


@api.get("/docker/containers/{container_id}")
async def inspect_container(container_id: str) -> dict[str, Any]:
    return docker_client().inspect_container(container_id)


@api.get("/docker/containers/{container_id}/stats")
async def container_stats(container_id: str) -> dict[str, Any]:
    return docker_client().container_stats(container_id)


@api.post("/docker/containers/{container_id}/actions/{action}")
async def container_action(
    container_id: str,
    action: str,
    payload: Optional[DockerActionPayload] = None,
) -> dict[str, Any]:
    if settings.read_only:
        raise HTTPException(status_code=403, detail="Docker actions are disabled because MONITOR_READ_ONLY is enabled")
    options = payload.model_dump() if payload and hasattr(payload, "model_dump") else payload.dict() if payload else {}
    return docker_client().run_action(container_id, action, options)


@api.get("/overview")
async def overview() -> dict[str, Any]:
    snapshot = collect_system_snapshot(settings)
    containers_payload: dict[str, Any] = {"available": True, "items": [], "counts": {}}
    try:
        container_items = docker_client().list_containers()
        counts: dict[str, int] = {}
        for item in container_items:
            state = item.get("state", "unknown")
            counts[state] = counts.get(state, 0) + 1
        containers_payload = {"available": True, "items": container_items, "counts": counts}
    except (DockerUnavailableError, DockerAPIError) as exc:
        containers_payload = {"available": False, "items": [], "counts": {}, "error": str(exc)}
    return {"metrics": snapshot, "containers": containers_payload, "read_only": settings.read_only}


app.include_router(api)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")
