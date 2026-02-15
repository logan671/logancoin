#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="/home/ubuntu/app"
BRANCH="main"

run_as_ubuntu() {
  runuser -u ubuntu -- "$@"
}

run_as_ubuntu git -C "$REPO_DIR" fetch origin "$BRANCH"
LOCAL_COMMIT="$(run_as_ubuntu git -C "$REPO_DIR" rev-parse HEAD)"
REMOTE_COMMIT="$(run_as_ubuntu git -C "$REPO_DIR" rev-parse "origin/${BRANCH}")"

if [ "$LOCAL_COMMIT" != "$REMOTE_COMMIT" ]; then
  run_as_ubuntu git -C "$REPO_DIR" pull --ff-only origin "$BRANCH"
  systemctl restart projectg-observer
fi
