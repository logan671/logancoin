#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   scripts/deploy-gate.sh company
#   scripts/deploy-gate.sh personal
#
# Behavior:
#   - If target is missing, stop and ask the operator to clarify.
#   - If target is provided, validate with preflight and continue.

TARGET="${1:-}"

if [[ -z "${TARGET}" ]]; then
  echo "[deploy-gate] TARGET_MISSING"
  echo "[deploy-gate] 서버 타깃을 지정해 주세요: company 또는 personal"
  echo "[deploy-gate] 예시: scripts/deploy-gate.sh company"
  exit 1
fi

bash scripts/preflight-target.sh "${TARGET}"
echo "[deploy-gate] READY target=${TARGET}"
