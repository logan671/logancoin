-- ProjectK polycopyman
-- Migration: v0 (initial schema)
-- Source of truth at creation time: schema.sql
-- Applied order: v0 -> v1 -> v2 ...

BEGIN;

PRAGMA foreign_keys = ON;

-- Source wallets (wallets to copy from)
CREATE TABLE IF NOT EXISTS source_wallets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    address TEXT NOT NULL UNIQUE,
    alias TEXT,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'paused', 'archived')),
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);

-- Follower wallets (wallets that execute mirrored trades)
CREATE TABLE IF NOT EXISTS follower_wallets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    address TEXT NOT NULL UNIQUE,
    label TEXT,
    budget_usdc REAL NOT NULL CHECK (budget_usdc >= 0),
    initial_matic REAL NOT NULL DEFAULT 3 CHECK (initial_matic >= 0),
    min_matic_alert REAL NOT NULL DEFAULT 0.5 CHECK (min_matic_alert >= 0),
    key_ref TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'paused', 'archived')),
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);

-- 1:1 source -> follower pair
CREATE TABLE IF NOT EXISTS wallet_pairs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_wallet_id INTEGER NOT NULL,
    follower_wallet_id INTEGER NOT NULL UNIQUE,
    mode TEXT NOT NULL DEFAULT 'live' CHECK (mode IN ('shadow', 'live')),
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
    sizing_policy TEXT NOT NULL DEFAULT 'proportional' CHECK (sizing_policy IN ('fixed', 'proportional')),
    min_order_usdc REAL NOT NULL DEFAULT 1 CHECK (min_order_usdc > 0),
    max_order_usdc REAL CHECK (max_order_usdc IS NULL OR max_order_usdc > 0),
    max_slippage_bps INTEGER NOT NULL DEFAULT 300 CHECK (max_slippage_bps BETWEEN 1 AND 10000),
    max_consecutive_failures INTEGER NOT NULL DEFAULT 3 CHECK (max_consecutive_failures >= 1),
    rpc_error_threshold INTEGER NOT NULL DEFAULT 5 CHECK (rpc_error_threshold >= 1),
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    UNIQUE (source_wallet_id),
    FOREIGN KEY (source_wallet_id) REFERENCES source_wallets (id) ON DELETE CASCADE,
    FOREIGN KEY (follower_wallet_id) REFERENCES follower_wallets (id) ON DELETE CASCADE
);

-- Raw/normalized source signals
CREATE TABLE IF NOT EXISTS trade_signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_wallet_id INTEGER NOT NULL,
    chain_id INTEGER NOT NULL DEFAULT 137,
    tx_hash TEXT NOT NULL,
    log_index INTEGER NOT NULL DEFAULT -1,
    block_number INTEGER,
    market_slug TEXT,
    token_id TEXT,
    outcome TEXT,
    side TEXT NOT NULL CHECK (side IN ('buy', 'sell')),
    source_notional_usdc REAL NOT NULL CHECK (source_notional_usdc >= 0),
    source_price REAL,
    idempotency_key TEXT NOT NULL UNIQUE,
    observed_at INTEGER NOT NULL,
    created_at INTEGER NOT NULL,
    FOREIGN KEY (source_wallet_id) REFERENCES source_wallets (id) ON DELETE CASCADE
);

-- Mirrored order intents generated from signals
CREATE TABLE IF NOT EXISTS mirror_orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pair_id INTEGER NOT NULL,
    trade_signal_id INTEGER NOT NULL,
    requested_notional_usdc REAL NOT NULL CHECK (requested_notional_usdc >= 0),
    min_order_size_usdc REAL,
    adjusted_notional_usdc REAL NOT NULL CHECK (adjusted_notional_usdc >= 0),
    expected_slippage_bps INTEGER,
    status TEXT NOT NULL CHECK (status IN ('queued', 'blocked', 'sent', 'filled', 'failed', 'canceled')),
    blocked_reason TEXT,
    executor_ref TEXT,
    idempotency_key TEXT NOT NULL UNIQUE,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    FOREIGN KEY (pair_id) REFERENCES wallet_pairs (id) ON DELETE CASCADE,
    FOREIGN KEY (trade_signal_id) REFERENCES trade_signals (id) ON DELETE CASCADE
);

-- Actual execution result records
CREATE TABLE IF NOT EXISTS executions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mirror_order_id INTEGER NOT NULL UNIQUE,
    pair_id INTEGER NOT NULL,
    follower_wallet_id INTEGER NOT NULL,
    chain_tx_hash TEXT,
    executed_side TEXT CHECK (executed_side IN ('buy', 'sell')),
    executed_outcome TEXT,
    executed_price REAL,
    executed_notional_usdc REAL,
    fee_usdc REAL,
    pnl_realized_usdc REAL,
    status TEXT NOT NULL CHECK (status IN ('filled', 'partial', 'failed', 'reverted')),
    fail_reason TEXT,
    executed_at INTEGER,
    created_at INTEGER NOT NULL,
    FOREIGN KEY (mirror_order_id) REFERENCES mirror_orders (id) ON DELETE CASCADE,
    FOREIGN KEY (pair_id) REFERENCES wallet_pairs (id) ON DELETE CASCADE,
    FOREIGN KEY (follower_wallet_id) REFERENCES follower_wallets (id) ON DELETE CASCADE
);

-- Risk guard events (stops, blocks, threshold hits)
CREATE TABLE IF NOT EXISTS risk_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pair_id INTEGER,
    follower_wallet_id INTEGER,
    event_type TEXT NOT NULL,
    severity TEXT NOT NULL CHECK (severity IN ('info', 'warn', 'critical')),
    detail TEXT,
    meta_json TEXT,
    created_at INTEGER NOT NULL,
    FOREIGN KEY (pair_id) REFERENCES wallet_pairs (id) ON DELETE SET NULL,
    FOREIGN KEY (follower_wallet_id) REFERENCES follower_wallets (id) ON DELETE SET NULL
);

-- Balance snapshots for operations and UI
CREATE TABLE IF NOT EXISTS balances (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    follower_wallet_id INTEGER NOT NULL,
    asset_symbol TEXT NOT NULL,
    asset_address TEXT,
    amount REAL NOT NULL,
    amount_usdc REAL,
    block_number INTEGER,
    snapshot_at INTEGER NOT NULL,
    created_at INTEGER NOT NULL,
    FOREIGN KEY (follower_wallet_id) REFERENCES follower_wallets (id) ON DELETE CASCADE
);

-- Outbound notifications
CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pair_id INTEGER,
    follower_wallet_id INTEGER,
    channel TEXT NOT NULL CHECK (channel IN ('telegram', 'webhook', 'email')),
    alert_type TEXT NOT NULL,
    message TEXT NOT NULL,
    dedupe_key TEXT,
    sent_status TEXT NOT NULL DEFAULT 'pending' CHECK (sent_status IN ('pending', 'sent', 'failed')),
    sent_at INTEGER,
    created_at INTEGER NOT NULL,
    FOREIGN KEY (pair_id) REFERENCES wallet_pairs (id) ON DELETE SET NULL,
    FOREIGN KEY (follower_wallet_id) REFERENCES follower_wallets (id) ON DELETE SET NULL
);

-- Runtime service registry (which component points to which DB path)
CREATE TABLE IF NOT EXISTS service_runtime (
    component TEXT PRIMARY KEY,
    pid INTEGER NOT NULL,
    db_path TEXT NOT NULL,
    updated_at INTEGER NOT NULL,
    extra_json TEXT
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_source_wallets_status ON source_wallets (status);
CREATE INDEX IF NOT EXISTS idx_follower_wallets_status ON follower_wallets (status);
CREATE INDEX IF NOT EXISTS idx_wallet_pairs_active ON wallet_pairs (active);

CREATE INDEX IF NOT EXISTS idx_trade_signals_source_observed ON trade_signals (source_wallet_id, observed_at DESC);
CREATE INDEX IF NOT EXISTS idx_trade_signals_tx ON trade_signals (tx_hash, log_index);
CREATE INDEX IF NOT EXISTS idx_trade_signals_market ON trade_signals (market_slug);

CREATE INDEX IF NOT EXISTS idx_mirror_orders_pair_created ON mirror_orders (pair_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_mirror_orders_status ON mirror_orders (status);

CREATE INDEX IF NOT EXISTS idx_executions_pair_executed ON executions (pair_id, executed_at DESC);
CREATE INDEX IF NOT EXISTS idx_executions_follower_executed ON executions (follower_wallet_id, executed_at DESC);
CREATE INDEX IF NOT EXISTS idx_executions_status ON executions (status);

CREATE INDEX IF NOT EXISTS idx_risk_events_pair_created ON risk_events (pair_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_risk_events_severity_created ON risk_events (severity, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_balances_wallet_snapshot ON balances (follower_wallet_id, snapshot_at DESC);
CREATE INDEX IF NOT EXISTS idx_balances_asset ON balances (asset_symbol, snapshot_at DESC);

CREATE INDEX IF NOT EXISTS idx_alerts_pair_created ON alerts (pair_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_status_created ON alerts (sent_status, created_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS idx_alerts_dedupe_key ON alerts (dedupe_key) WHERE dedupe_key IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_service_runtime_updated ON service_runtime (updated_at DESC);

COMMIT;
