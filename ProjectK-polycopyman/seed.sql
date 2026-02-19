BEGIN;

PRAGMA foreign_keys = ON;

-- Seed timestamp
WITH now(ts) AS (SELECT CAST(strftime('%s','now') AS INTEGER))
INSERT INTO source_wallets (address, alias, status, created_at, updated_at)
SELECT '0x1111111111111111111111111111111111111111', 'source_alpha', 'active', ts, ts FROM now
UNION ALL
SELECT '0x2222222222222222222222222222222222222222', 'source_bravo', 'active', ts, ts FROM now
UNION ALL
SELECT '0x3333333333333333333333333333333333333333', 'source_charlie', 'active', ts, ts FROM now;

WITH now(ts) AS (SELECT CAST(strftime('%s','now') AS INTEGER))
INSERT INTO follower_wallets (
    address, label, budget_usdc, initial_matic, min_matic_alert, key_ref, status, created_at, updated_at
)
SELECT '0xa111111111111111111111111111111111111111', 'follower_alpha', 180, 3, 0.5, 'vault://follower_alpha', 'active', ts, ts FROM now
UNION ALL
SELECT '0xa222222222222222222222222222222222222222', 'follower_bravo', 420, 3, 0.5, 'vault://follower_bravo', 'active', ts, ts FROM now
UNION ALL
SELECT '0xa333333333333333333333333333333333333333', 'follower_charlie', 900, 3, 0.5, 'vault://follower_charlie', 'active', ts, ts FROM now;

WITH now(ts) AS (SELECT CAST(strftime('%s','now') AS INTEGER))
INSERT INTO wallet_pairs (
    source_wallet_id,
    follower_wallet_id,
    mode,
    active,
    sizing_policy,
    min_order_usdc,
    max_order_usdc,
    max_slippage_bps,
    max_consecutive_failures,
    rpc_error_threshold,
    created_at,
    updated_at
)
SELECT s.id, f.id, 'live', 1, 'proportional', 1, NULL, 300, 3, 5, ts, ts
FROM source_wallets s
JOIN follower_wallets f ON (
    (s.alias = 'source_alpha' AND f.label = 'follower_alpha')
    OR (s.alias = 'source_bravo' AND f.label = 'follower_bravo')
    OR (s.alias = 'source_charlie' AND f.label = 'follower_charlie')
)
JOIN now;

COMMIT;
