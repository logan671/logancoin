#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DB_PATH="${1:-$SCRIPT_DIR/projectk.db}"
SCHEMA_PATH="$SCRIPT_DIR/schema.sql"
SEED_PATH="$SCRIPT_DIR/seed.sql"

if [[ ! -f "$SCHEMA_PATH" ]]; then
  echo "[ERROR] schema file not found: $SCHEMA_PATH" >&2
  exit 1
fi

if [[ ! -f "$SEED_PATH" ]]; then
  echo "[ERROR] seed file not found: $SEED_PATH" >&2
  exit 1
fi

mkdir -p "$(dirname "$DB_PATH")"

if [[ -f "$DB_PATH" ]]; then
  rm -f "$DB_PATH"
fi

sqlite3 "$DB_PATH" < "$SCHEMA_PATH"
sqlite3 "$DB_PATH" < "$SEED_PATH"

echo "[OK] seeded database: $DB_PATH"
echo "[INFO] table counts:"
sqlite3 "$DB_PATH" "SELECT 'source_wallets', COUNT(*) FROM source_wallets;"
sqlite3 "$DB_PATH" "SELECT 'follower_wallets', COUNT(*) FROM follower_wallets;"
sqlite3 "$DB_PATH" "SELECT 'wallet_pairs', COUNT(*) FROM wallet_pairs;"
