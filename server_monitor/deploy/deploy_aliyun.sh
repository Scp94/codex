#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ALIYUN_USER="${ALIYUN_USER:-root}"
APP_DIR="${APP_DIR:-/opt/server-monitor}"
MONITOR_PORT="${MONITOR_PORT:-8080}"
SSH_TARGET="${SSH_TARGET:-}"

if [[ -z "${SSH_TARGET}" && -z "${ALIYUN_HOST:-}" ]]; then
  echo "SSH_TARGET or ALIYUN_HOST is required, for example: export SSH_TARGET=aliyun" >&2
  exit 1
fi

if [[ -z "${MONITOR_API_TOKEN:-}" ]]; then
  echo "MONITOR_API_TOKEN is required, for example: export MONITOR_API_TOKEN=\$(openssl rand -hex 24)" >&2
  exit 1
fi

if [[ -n "${SSH_TARGET}" ]]; then
  REMOTE="${SSH_TARGET}"
else
  REMOTE="${ALIYUN_USER}@${ALIYUN_HOST}"
fi
ARCHIVE="/tmp/server-monitor-${USER:-codex}-deploy.tgz"

echo "Packing project..."
tar \
  --exclude ".env" \
  --exclude ".venv" \
  --exclude ".pycache" \
  --exclude "__pycache__" \
  --exclude "*.pyc" \
  -C "${PROJECT_ROOT}" \
  -czf "${ARCHIVE}" \
  .

echo "Uploading to ${REMOTE}:${APP_DIR}..."
ssh "${REMOTE}" "mkdir -p '${APP_DIR}'"
scp "${ARCHIVE}" "${REMOTE}:/tmp/server-monitor-deploy.tgz"

echo "Installing and starting service..."
ssh "${REMOTE}" "set -euo pipefail
  if ! command -v docker >/dev/null 2>&1; then
    curl -fsSL https://get.docker.com | sh
    systemctl enable --now docker
  fi
  rm -rf '${APP_DIR:?}'/*
  tar -xzf /tmp/server-monitor-deploy.tgz -C '${APP_DIR}'
  cd '${APP_DIR}'
  cat > .env <<ENVEOF
MONITOR_API_TOKEN=${MONITOR_API_TOKEN}
MONITOR_PORT=${MONITOR_PORT}
MONITOR_READ_ONLY=${MONITOR_READ_ONLY:-false}
ENVEOF
  docker compose up -d --build
  docker compose ps
"

rm -f "${ARCHIVE}"

echo "Done. Open http://<your-ecs-public-ip>:${MONITOR_PORT}"
