#!/usr/bin/env bash
# First-time control node setup: clone repo, preserve state, deploy stack.
# Run on the control node VM (ubuntu user) or via: ssh ubuntu@<tailnet-ip> 'bash -s' < scripts/bootstrap-control-node.sh
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/gavinfancher/homecloud.git}"
INSTALL_DIR="${INSTALL_DIR:-$HOME/homecloud}"
BRANCH="${DEPLOY_BRANCH:-main}"

if [[ -d "$INSTALL_DIR/.git" ]]; then
  echo "Already bootstrapped at $INSTALL_DIR"
  exit 0
fi

BACKUP=""
if [[ -d "$INSTALL_DIR" ]]; then
  BACKUP="${INSTALL_DIR}.bak.$(date +%s)"
  echo "→ Backing up existing $INSTALL_DIR to $BACKUP"
  mv "$INSTALL_DIR" "$BACKUP"
fi

echo "→ Cloning $REPO_URL into $INSTALL_DIR"
git clone --branch "$BRANCH" "$REPO_URL" "$INSTALL_DIR"
cd "$INSTALL_DIR"

if [[ -n "$BACKUP" ]]; then
  for item in .env .homecloud ssh; do
    if [[ -e "$BACKUP/$item" ]]; then
      echo "→ Restoring $item from backup"
      rm -rf "$item"
      cp -a "$BACKUP/$item" "$item"
    fi
  done
fi

if [[ ! -f .env ]]; then
  echo "Copy .env.example → .env and fill secrets, then re-run deploy." >&2
  cp .env.example .env
  exit 1
fi

if [[ -d ssh ]]; then
  chmod 700 ssh
  chmod 600 ssh/*-key 2>/dev/null || true
fi

chmod +x scripts/*.sh
./scripts/control-node-deploy.sh
