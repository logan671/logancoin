PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS signals (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  event_time_utc TEXT NOT NULL,
  pool_id TEXT NOT NULL,
  market_stx_per_ststx REAL NOT NULL,
  intrinsic_stx_per_ststx REAL NOT NULL,
  edge_pct REAL NOT NULL,
  abs_edge_pct REAL NOT NULL,
  slippage_pct REAL NOT NULL,
  net_edge_pct REAL NOT NULL,
  action TEXT NOT NULL,
  should_enter INTEGER NOT NULL,
  reason TEXT NOT NULL,
  order_usd REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS orders (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  signal_id INTEGER,
  event_time_utc TEXT NOT NULL,
  order_id TEXT,
  side TEXT NOT NULL,
  pool_id TEXT NOT NULL,
  order_size_usd REAL NOT NULL,
  status TEXT NOT NULL,
  reason TEXT,
  txid TEXT,
  FOREIGN KEY(signal_id) REFERENCES signals(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS fills (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  order_id INTEGER NOT NULL,
  event_time_utc TEXT NOT NULL,
  filled_stx REAL,
  filled_ststx REAL,
  avg_fill_price_stx_per_ststx REAL,
  fee_stx REAL NOT NULL DEFAULT 0,
  slippage_pct REAL,
  trade_pnl_stx REAL,
  running_pnl_stx REAL,
  FOREIGN KEY(order_id) REFERENCES orders(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS positions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  opened_at_utc TEXT NOT NULL,
  closed_at_utc TEXT,
  side TEXT NOT NULL,
  pool_id TEXT NOT NULL,
  size_usd REAL NOT NULL,
  entry_price_stx_per_ststx REAL NOT NULL,
  exit_price_stx_per_ststx REAL,
  status TEXT NOT NULL,
  realized_pnl_stx REAL
);

CREATE TABLE IF NOT EXISTS pnl_daily (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  day_utc TEXT NOT NULL UNIQUE,
  start_equity_stx REAL NOT NULL,
  end_equity_stx REAL,
  running_pnl_stx REAL NOT NULL DEFAULT 0,
  trade_count INTEGER NOT NULL DEFAULT 0,
  win_count INTEGER NOT NULL DEFAULT 0,
  loss_count INTEGER NOT NULL DEFAULT 0,
  updated_at_utc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS alerts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  event_time_utc TEXT NOT NULL,
  event_type TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  status TEXT NOT NULL,
  error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_signals_time ON signals(event_time_utc);
CREATE INDEX IF NOT EXISTS idx_orders_time ON orders(event_time_utc);
CREATE INDEX IF NOT EXISTS idx_fills_time ON fills(event_time_utc);
CREATE INDEX IF NOT EXISTS idx_alerts_time ON alerts(event_time_utc);
CREATE INDEX IF NOT EXISTS idx_pnl_day ON pnl_daily(day_utc);

