#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   scripts/preflight-target.sh company
#   scripts/preflight-target.sh personal
#
# Purpose:
#   Enforce explicit deploy target before any deploy/ops action.

TARGET="${1:-}"

if [[ -z "${TARGET}" ]]; then
  echo "[preflight] ERROR: target is required (company|personal)." >&2
  exit 1
fi

case "${TARGET}" in
  company|personal)
    ;;
  *)
    echo "[preflight] ERROR: invalid target '${TARGET}'. Use company|personal." >&2
    exit 1
    ;;
esac

if [[ ! -f "DEPLOY_TARGETS.yaml" ]]; then
  echo "[preflight] ERROR: DEPLOY_TARGETS.yaml not found." >&2
  exit 1
fi

if ! rg -n "^[[:space:]]+${TARGET}:" DEPLOY_TARGETS.yaml >/dev/null 2>&1; then
  echo "[preflight] ERROR: target '${TARGET}' is not defined in DEPLOY_TARGETS.yaml." >&2
  exit 1
fi

echo "[preflight] OK: target=${TARGET}"
