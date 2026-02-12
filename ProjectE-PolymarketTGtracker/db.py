import os
import sqlite3
import time
from typing import Optional

from config import DB_PATH


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db() -> None:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS wallets (
                address TEXT PRIMARY KEY,
                alias TEXT,
                note TEXT,
                created_at INTEGER,
                updated_at INTEGER
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS state (
                key TEXT PRIMARY KEY,
                value TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sent_events (
                tx_hash TEXT,
                log_index INTEGER,
                address TEXT,
                sent_at INTEGER,
                PRIMARY KEY (tx_hash, log_index, address)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS trade_counts (
                address TEXT,
                market_key TEXT,
                date TEXT,
                count INTEGER,
                updated_at INTEGER,
                PRIMARY KEY (address, market_key, date)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS directional_streaks (
                address TEXT,
                market_key TEXT,
                outcome TEXT,
                side TEXT,
                streak_count INTEGER,
                last_milestone_alert INTEGER,
                updated_at INTEGER,
                PRIMARY KEY (address, market_key, outcome)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tracked_markets (
                chat_id TEXT,
                market_slug TEXT,
                market_title TEXT,
                created_at INTEGER,
                PRIMARY KEY (chat_id, market_slug)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tracked_positions (
                chat_id TEXT,
                address TEXT,
                market_slug TEXT,
                market_title TEXT,
                outcome TEXT,
                side TEXT,
                status TEXT,
                started_at INTEGER,
                exited_at INTEGER,
                exit_tx_hash TEXT,
                PRIMARY KEY (chat_id, address, market_slug, started_at)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS track_buttons (
                token TEXT PRIMARY KEY,
                address TEXT,
                market_slug TEXT,
                market_title TEXT,
                outcome TEXT,
                side TEXT,
                created_at INTEGER
            )
            """
        )


def upsert_wallet(address: str, alias: Optional[str], note: Optional[str]) -> None:
    now = int(time.time())
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO wallets(address, alias, note, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(address) DO UPDATE SET
                alias=COALESCE(excluded.alias, wallets.alias),
                note=COALESCE(excluded.note, wallets.note),
                updated_at=excluded.updated_at
            """,
            (address, alias, note, now, now),
        )


def update_alias(address: str, alias: Optional[str]) -> None:
    now = int(time.time())
    with get_conn() as conn:
        conn.execute(
            "UPDATE wallets SET alias=?, updated_at=? WHERE address=?",
            (alias, now, address),
        )


def update_note(address: str, note: Optional[str]) -> None:
    now = int(time.time())
    with get_conn() as conn:
        conn.execute(
            "UPDATE wallets SET note=?, updated_at=? WHERE address=?",
            (note, now, address),
        )


def remove_wallet(address: str) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM wallets WHERE address=?", (address,))


def list_wallets() -> list[tuple[str, Optional[str], Optional[str]]]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT address, alias, note FROM wallets ORDER BY created_at ASC"
        ).fetchall()


def get_wallet(address: str) -> Optional[tuple[str, Optional[str], Optional[str]]]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT address, alias, note FROM wallets WHERE address=?",
            (address,),
        ).fetchone()
        return row


def get_state(key: str) -> Optional[str]:
    with get_conn() as conn:
        row = conn.execute("SELECT value FROM state WHERE key=?", (key,)).fetchone()
        return row[0] if row else None


def set_state(key: str, value: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO state(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )


def is_sent(tx_hash: str, log_index: int, address: str) -> bool:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM sent_events WHERE tx_hash=? AND log_index=? AND address=?",
            (tx_hash, log_index, address),
        ).fetchone()
        return row is not None


def mark_sent(tx_hash: str, log_index: int, address: str) -> None:
    now = int(time.time())
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO sent_events(tx_hash, log_index, address, sent_at) VALUES(?, ?, ?, ?)",
            (tx_hash, log_index, address, now),
        )


def is_sent_any(tx_hash: str, address: str) -> bool:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM sent_events WHERE tx_hash=? AND address=?",
            (tx_hash, address),
        ).fetchone()
        return row is not None


def mark_sent_any(tx_hash: str, address: str) -> None:
    now = int(time.time())
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO sent_events(tx_hash, log_index, address, sent_at) VALUES(?, ?, ?, ?)",
            (tx_hash, -1, address, now),
        )


def prune_old_sent_events(ttl_days: int) -> int:
    if ttl_days <= 0:
        return 0
    cutoff = int(time.time()) - (ttl_days * 86400)
    with get_conn() as conn:
        cur = conn.execute(
            "DELETE FROM sent_events WHERE sent_at < ?",
            (cutoff,),
        )
        return int(cur.rowcount or 0)


def get_trade_count(address: str, market_key: str, date: str) -> int:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT count FROM trade_counts WHERE address=? AND market_key=? AND date=?",
            (address, market_key, date),
        ).fetchone()
        return int(row[0]) if row else 0


def increment_trade_count(address: str, market_key: str, date: str) -> int:
    now = int(time.time())
    with get_conn() as conn:
        row = conn.execute(
            "SELECT count FROM trade_counts WHERE address=? AND market_key=? AND date=?",
            (address, market_key, date),
        ).fetchone()
        count = int(row[0]) if row else 0
        new_count = count + 1
        conn.execute(
            """
            INSERT INTO trade_counts(address, market_key, date, count, updated_at)
            VALUES(?, ?, ?, ?, ?)
            ON CONFLICT(address, market_key, date)
            DO UPDATE SET count=excluded.count, updated_at=excluded.updated_at
            """,
            (address, market_key, date, new_count, now),
        )
        return new_count


def update_directional_streak(
    address: str,
    market_key: str,
    outcome: str,
    side: str,
) -> tuple[int, bool]:
    now = int(time.time())
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT side, streak_count, last_milestone_alert
            FROM directional_streaks
            WHERE address=? AND market_key=? AND outcome=?
            """,
            (address, market_key, outcome),
        ).fetchone()

        if row and row[0] == side:
            streak_count = int(row[1]) + 1
            last_milestone_alert = int(row[2] or 0)
        else:
            streak_count = 1
            last_milestone_alert = 0

        milestones = {5, 10, 20}
        is_milestone = streak_count in milestones and streak_count > last_milestone_alert
        next_milestone_alert = streak_count if is_milestone else last_milestone_alert

        conn.execute(
            """
            INSERT INTO directional_streaks(
                address, market_key, outcome, side, streak_count, last_milestone_alert, updated_at
            )
            VALUES(?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(address, market_key, outcome)
            DO UPDATE SET
                side=excluded.side,
                streak_count=excluded.streak_count,
                last_milestone_alert=excluded.last_milestone_alert,
                updated_at=excluded.updated_at
            """,
            (
                address,
                market_key,
                outcome,
                side,
                streak_count,
                next_milestone_alert,
                now,
            ),
        )

        return streak_count, is_milestone


def add_tracked_market(chat_id: str, market_slug: str, market_title: str) -> None:
    now = int(time.time())
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO tracked_markets(chat_id, market_slug, market_title, created_at)
            VALUES(?, ?, ?, ?)
            ON CONFLICT(chat_id, market_slug)
            DO UPDATE SET market_title=excluded.market_title
            """,
            (chat_id, market_slug, market_title, now),
        )


def list_tracked_markets(chat_id: str) -> list[tuple[str, str]]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT market_title, market_slug FROM tracked_markets WHERE chat_id=? ORDER BY created_at DESC",
            (chat_id,),
        ).fetchall()


def add_tracked_position(
    chat_id: str,
    address: str,
    market_slug: str,
    market_title: str,
    outcome: str,
    side: str,
) -> None:
    now = int(time.time())
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO tracked_positions(
                chat_id, address, market_slug, market_title, outcome, side, status, started_at, exited_at, exit_tx_hash
            )
            VALUES(?, ?, ?, ?, ?, ?, 'active', ?, NULL, NULL)
            """,
            (chat_id, address, market_slug, market_title, outcome, side, now),
        )


def list_tracked_positions(chat_id: str) -> list[tuple[str, str, str, str]]:
    with get_conn() as conn:
        return conn.execute(
            """
            SELECT market_title, market_slug, outcome, side
            FROM tracked_positions
            WHERE chat_id=? AND status='active'
            ORDER BY started_at DESC
            """,
            (chat_id,),
        ).fetchall()


def get_active_tracked_position(address: str, market_slug: str) -> Optional[tuple[str, str, str, str, int]]:
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT chat_id, outcome, side, market_title, started_at
            FROM tracked_positions
            WHERE address=? AND market_slug=? AND status='active'
            ORDER BY started_at DESC
            LIMIT 1
            """,
            (address, market_slug),
        ).fetchone()
        return row


def mark_tracked_position_exited(chat_id: str, address: str, market_slug: str, started_at: int, tx_hash: str) -> None:
    now = int(time.time())
    with get_conn() as conn:
        conn.execute(
            """
            UPDATE tracked_positions
            SET status='exited', exited_at=?, exit_tx_hash=?
            WHERE chat_id=? AND address=? AND market_slug=? AND started_at=?
            """,
            (now, tx_hash, chat_id, address, market_slug, started_at),
        )


def add_track_button(token: str, address: str, market_slug: str, market_title: str, outcome: str, side: str) -> None:
    now = int(time.time())
    with get_conn() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO track_buttons(token, address, market_slug, market_title, outcome, side, created_at)
            VALUES(?, ?, ?, ?, ?, ?, ?)
            """,
            (token, address, market_slug, market_title, outcome, side, now),
        )


def get_track_button(token: str) -> Optional[tuple[str, str, str, str, str, str]]:
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT address, market_slug, market_title, outcome, side, token
            FROM track_buttons
            WHERE token=?
            """,
            (token,),
        ).fetchone()
        return row


def delete_track_button(token: str) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM track_buttons WHERE token=?", (token,))
