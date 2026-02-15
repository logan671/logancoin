from __future__ import annotations

import json
import os
import smtplib
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage
from pathlib import Path

from .config import settings
from .observation_store import init_db


@dataclass(slots=True)
class ReportConfig:
    email_from: str
    email_to: str
    smtp_user: str
    smtp_password: str
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587


STATE_PATH = Path("data/report_state.json")


def _load_state() -> dict:
    if STATE_PATH.exists():
        with STATE_PATH.open("r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with STATE_PATH.open("w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def _should_send(now: datetime, state: dict) -> bool:
    started_at = state.get("started_at")
    last_sent = state.get("last_sent")

    if started_at is None:
        state["started_at"] = now.isoformat()
        return True

    started_dt = datetime.fromisoformat(started_at)
    if started_dt.tzinfo is None:
        started_dt = started_dt.replace(tzinfo=UTC)

    if last_sent:
        last_dt = datetime.fromisoformat(last_sent)
        if last_dt.tzinfo is None:
            last_dt = last_dt.replace(tzinfo=UTC)
    else:
        last_dt = None

    if now - started_dt <= timedelta(hours=24):
        if last_dt is None:
            return True
        return (now - last_dt) >= timedelta(hours=1)

    # After 24 hours: send once per day (UTC day change)
    if last_dt is None:
        return True
    return now.date() != last_dt.date()


def _fetch_summary(db_path: str) -> dict:
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        total = conn.execute(
            """
            SELECT COUNT(*),
                   COALESCE(SUM(pnl), 0),
                   COALESCE(SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END), 0)
            FROM observations
            WHERE would_trade = 1 AND filled = 1 AND actual_result IS NOT NULL
            """
        ).fetchone()

        last24 = conn.execute(
            """
            SELECT COUNT(*),
                   COALESCE(SUM(pnl), 0),
                   COALESCE(SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END), 0)
            FROM observations
            WHERE would_trade = 1 AND filled = 1 AND actual_result IS NOT NULL
              AND ts >= ?
            """,
            ((datetime.now(UTC) - timedelta(hours=24)).isoformat(),),
        ).fetchone()

        pending = conn.execute(
            """
            SELECT COUNT(*)
            FROM observations
            WHERE would_trade = 1 AND filled = 1 AND actual_result IS NULL
            """
        ).fetchone()

    total_trades, total_pnl, total_wins = total
    last24_trades, last24_pnl, last24_wins = last24
    pending_count = pending[0]

    def win_rate(wins: int, trades: int) -> float:
        return round((wins / trades) * 100, 2) if trades else 0.0

    return {
        "total_trades": total_trades,
        "total_pnl": round(total_pnl, 6),
        "total_win_rate": win_rate(total_wins, total_trades),
        "last24_trades": last24_trades,
        "last24_pnl": round(last24_pnl, 6),
        "last24_win_rate": win_rate(last24_wins, last24_trades),
        "pending": pending_count,
    }


def _build_email(summary: dict) -> EmailMessage:
    msg = EmailMessage()
    msg["Subject"] = "ProjectG Report"
    msg.set_content(
        "\n".join(
            [
                "ProjectG (paper) summary",
                f"Total trades: {summary['total_trades']}",
                f"Total PnL: {summary['total_pnl']}",
                f"Total win rate: {summary['total_win_rate']}%",
                "",
                "Last 24h",
                f"Trades: {summary['last24_trades']}",
                f"PnL: {summary['last24_pnl']}",
                f"Win rate: {summary['last24_win_rate']}%",
                "",
                f"Pending (filled, unresolved): {summary['pending']}",
            ]
        )
    )
    return msg


def _send_email(cfg: ReportConfig, message: EmailMessage) -> None:
    message["From"] = cfg.email_from
    message["To"] = cfg.email_to

    with smtplib.SMTP(cfg.smtp_host, cfg.smtp_port) as smtp:
        smtp.starttls()
        smtp.login(cfg.smtp_user, cfg.smtp_password)
        smtp.send_message(message)


def main() -> None:
    email_from = os.getenv("REPORT_EMAIL_FROM", "")
    email_to = os.getenv("REPORT_EMAIL_TO", "")
    smtp_user = os.getenv("REPORT_SMTP_USER", email_from)
    smtp_password = os.getenv("REPORT_SMTP_PASSWORD", "")

    if not email_from or not email_to or not smtp_password:
        raise RuntimeError("Missing REPORT_EMAIL_FROM/TO/REPORT_SMTP_PASSWORD env")

    cfg = ReportConfig(
        email_from=email_from,
        email_to=email_to,
        smtp_user=smtp_user,
        smtp_password=smtp_password,
    )

    now = datetime.now(UTC)
    state = _load_state()
    if not _should_send(now, state):
        return

    summary = _fetch_summary(settings.DB_PATH)
    message = _build_email(summary)
    _send_email(cfg, message)

    state["last_sent"] = now.isoformat()
    _save_state(state)


if __name__ == "__main__":
    main()
