#!/usr/bin/env bash
# Deploy backend from your laptop: SSH to control node and run control-node-deploy.sh.
set -euo pipefail

HOST="${CONTROL_NODE_HOST:-}"
USER="${CONTROL_NODE_USER:-ubuntu}"
SSH_OPTS=(-o BatchMode=yes -o StrictHostKeyChecking=accept-new)

if [[ -z "$HOST" ]]; then
  echo "Set CONTROL_NODE_HOST (tailnet IP or hostname)." >&2
  echo "Example: CONTROL_NODE_HOST=100.76.205.59 $0" >&2
  exit 1
fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REMOTE_DIR="${CONTROL_NODE_DIR:-homecloud}"

echo "→ Deploying to ${USER}@${HOST}:~/${REMOTE_DIR}"
ssh "${SSH_OPTS[@]}" "${USER}@${HOST}" "cd ~/${REMOTE_DIR} && ./scripts/control-node-deploy.sh"

echo "→ Remote smoke check"
ssh "${SSH_OPTS[@]}" "${USER}@${HOST}" \
  "curl -fsS http://localhost:8080/api/health && echo && curl -fsS http://localhost:8080/api/config | head -c 400 && echo"
