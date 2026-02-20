import sqlite3

from .config import DB_PATH


def _ensure_compat_schema(conn: sqlite3.Connection) -> None:
    # Backward-compatible column for proportional sizing baseline.
    row = conn.execute(
        "SELECT 1 FROM pragma_table_info('source_wallets') WHERE name='source_portfolio_usdc'"
    ).fetchone()
    if row is None:
        conn.execute("ALTER TABLE source_wallets ADD COLUMN source_portfolio_usdc REAL")


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    _ensure_compat_schema(conn)
    return conn
